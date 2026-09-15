"""Inspect independently sourced regulatory publications.

No third-party UN card source is fetched. Survey output is not permission to
redistribute a publication or derived text; consult the rights register.
"""
from __future__ import annotations

import argparse
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

UNECE = "https://unece.org/sites/default/files/2023-08"
VOL1 = f"{UNECE}/ST-SG-AC10-1r23e_Vol1_WEB.pdf"
VOL2 = f"{UNECE}/ST-SG-AC10-1r23e_Vol2_WEB.pdf"
CEPA = "https://www.cepa.be/wp-content/uploads/IMDG_Code-amdt_42_24.pdf"

# What is on cepa.be is MSC 108/20/Add.2, annex 8: the full consolidated text of
# Amendment 42-24, 954 pages. The code pages below follow from the table of
# contents. The PDF counts on through the front matter, so the real page number
# is some twelve higher; find_page_offset() measures that instead of guessing it.
CODE_PAGES = {
    "7.1.3 Stowage categories": 476,
    "7.1.5 Stowage codes": 482,
    "7.1.6 Handling codes": 483,
    "7.2.4 Segregation table": 485,
    "7.2.5 Segregation groups": 486,
    "7.2.6 Special segregation provisions and exemptions": 486,
    "7.2.7 Segregation of goods of class 1": 489,
    "7.2.8 Segregation codes": 490,
    "Appendix 2 (Dangerous Goods List)": 564,
}

# The sections we want to be able to check. 7.2.4, 7.2.6.3 and 7.2.7.1.4 carry
# the segregation tables; 3.1.4.4 the segregation groups; 7.1.5 the stowage codes
# and 7.1.6 the handling codes, which we do have per substance but without their
# description.
SECTIONS_OF_INTEREST = ["3.1.4.4", "3.2.1", "3.3.1", "7.1.3", "7.1.5", "7.1.6",
                        "7.2.3.1", "7.2.4", "7.2.5", "7.2.6.3", "7.2.7.1.4", "7.2.8"]

# The entries Amendment 42-24 adds. If they are in Rev.23, the free edition is
# enough for everything except the IMDG-specific columns.
NEW_UN_NUMBERS = ["0514", "3551", "3552", "3553", "3554",
                  "3555", "3556", "3557", "3558", "3559", "3560"]

# Special provisions below 900 come from the Model Regulations; that text is
# currently missing on our side. The 9xx series is IMDG-specific and is not in it.
NEW_SPECIAL_PROVISIONS = ["375", "400", "401", "402", "403",
                          "404", "405", "406", "407", "408", "409"]

UA = {"User-Agent": "EMCargo source probe (github.com/jeffreymooiweer/emcargo)"}


def head(url: str, timeout: int = 25) -> tuple[int, int]:
    """(status code, number of bytes). An error is an outcome, not an exception."""
    request = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, len(response.read())
    except urllib.error.HTTPError as error:
        return error.code, 0
    except (urllib.error.URLError, TimeoutError, OSError):
        return 0, 0


def exists(url: str) -> bool:
    status, size = head(url)
    return status == 200 and size > 2000


def download(url: str, target: Path, timeout: int = 180) -> Path:
    request = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        target.write_bytes(response.read())
    return target


def read_pdf_text(url: str, target: Path, page: int = 0) -> str:
    import fitz

    download(url, target)
    with fitz.open(target) as document:
        return document[page].get_text()


def probe_model_regulations(sample_pages: list[int]) -> int:
    """Whether the Dangerous Goods List of Rev.23 can be read by machine."""
    import fitz

    print("== UN-modelvoorschriften Rev.23, deel II (Dangerous Goods List) ==")
    path = download(VOL2, Path("/tmp/vol2.pdf"))
    print(f"  {path.stat().st_size} bytes")

    with fitz.open(path) as document:
        print(f"  {document.page_count} pagina's")

        for index in range(min(80, document.page_count)):
            if re.search(r"DANGEROUS GOODS LIST", document[index].get_text(), re.I):
                print(f"  'DANGEROUS GOODS LIST' first on page {index + 1}")
                break

        found: dict[str, int] = {}
        for index in range(document.page_count):
            text = document[index].get_text()
            for un in NEW_UN_NUMBERS:
                if un not in found and re.search(rf"\b{un}\b", text):
                    found[un] = index + 1
        print(f"  new UN numbers found: {found}")
        missing = [un for un in NEW_UN_NUMBERS if un not in found]
        print(f"  missing: {missing or 'nothing'}")

        for number in sample_pages:
            index = number - 1
            if not 0 <= index < document.page_count:
                continue
            page = document[index]
            print(f"\n===== PAGINA {number}: platte tekst =====")
            print(page.get_text())
            print(f"===== PAGINA {number}: woorden met x-positie (eerste 150) =====")
            for word in page.get_text("words")[:150]:
                print(f"{word[0]:8.1f} {word[1]:8.1f}  {word[4]}")

    print("\n== Deel I (bijzondere bepalingen) ==")
    path = download(VOL1, Path("/tmp/vol1.pdf"))
    print(f"  {path.stat().st_size} bytes")
    with fitz.open(path) as document:
        print(f"  {document.page_count} pagina's")
        pending = list(NEW_SPECIAL_PROVISIONS)
        for index in range(document.page_count):
            text = document[index].get_text()
            for provision in list(pending):
                match = re.search(rf"^\s*{provision}\s+[A-Z(\"].{{0,700}}", text, re.M | re.S)
                if match:
                    print(f"\n--- SP{provision}, pagina {index + 1} ---")
                    print(match.group(0).strip())
                    pending.remove(provision)
        print(f"\n  not found again: {pending or 'nothing'}")
    return 0


def find_page_offset(document) -> int:
    """Difference between the page number in the footer and the index in the PDF.

    The table of contents refers to code pages; PyMuPDF counts from zero through
    the front matter. Measuring beats guessing: this reads the number from the
    footer of a handful of pages in the middle and takes the most common
    difference.
    """
    from collections import Counter

    votes: Counter[int] = Counter()
    for index in range(200, min(document.page_count, 800), 17):
        lines = [line.strip() for line in document[index].get_text().splitlines() if line.strip()]
        # The page number sits on the first or last line, on its own.
        for line in (lines[:2] + lines[-2:]) if lines else []:
            if line.isdigit() and 1 <= int(line) <= document.page_count:
                votes[index + 1 - int(line)] += 1
    return votes.most_common(1)[0][0] if votes else 0


def probe_cepa() -> int:
    """Establish *what* the amendment document on cepa.be is, and where what is.

    Not: copying the text. But: publisher, size, the page offset and a sample of
    every section we need, so the parsers can be written against it. Only factual
    data ends up in the repo in the end; the regulatory text itself does not.
    """
    import fitz

    print("== cepa.be — IMDG_Code-amdt_42_24.pdf ==")
    try:
        path = download(CEPA, Path("/tmp/cepa.pdf"), timeout=600)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as error:
        print(f"  not reachable: {error}")
        return 1
    print(f"  {path.stat().st_size} bytes")

    with fitz.open(path) as document:
        print(f"  {document.page_count} pagina's")
        print(f"  metadata: {document.metadata}")

        print("\n--- eerste pagina ---")
        print(document[0].get_text()[:2000])

        toc = document.get_toc()
        print(f"\n--- ingebedde inhoudsopgave: {len(toc)} regels ---")
        for level, title, page in toc[:120]:
            print(f"{'  ' * (level - 1)}{title}  -> p{page}")

        offset = find_page_offset(document)
        print(f"\n--- paginaverschuiving: PDF-pagina = codepagina + {offset} ---")

        print("\n--- the sections we need ---")
        for label, code_page in CODE_PAGES.items():
            index = code_page + offset - 1
            marker = "?" if not 0 <= index < document.page_count else ""
            print(f"  {label:<52} codepagina {code_page} -> PDF {index + 1}{marker}")

        print("\n--- where do the sections appear in the text? ---")
        located: dict[str, list[int]] = {}
        for index in range(document.page_count):
            text = document[index].get_text()
            for section in SECTIONS_OF_INTEREST:
                if re.search(rf"(?<![\d.]){re.escape(section)}(?![\d])", text):
                    located.setdefault(section, []).append(index + 1)
        for section in SECTIONS_OF_INTEREST:
            pages = located.get(section, [])
            summary = f"{len(pages)}x, eerst PDF p{pages[0]}" if pages else "niet gevonden"
            print(f"  {section:<12} {summary}")

        # Continuous code text or an overview of changes? An amendment writes in
        # instructions; a consolidated text does not.
        joined = " ".join(document[i].get_text() for i in range(min(40, document.page_count)))
        directives = sum(len(re.findall(rf"\b{verb}\b", joined, re.I))
                         for verb in ("replace", "insert", "delete", "amend"))
        print(f"\n  amendment directives in the first 40 pages: {directives}")
        print("  -> probably an amendment text" if directives > 60
              else "  -> probably a running, consolidated code text")

        # The stowage and segregation codes are the biggest gain and the easiest
        # to parse: numbered lists. Print them in full so the parser can be
        # written against the real layout.
        for label in ("7.1.3 Stowage categories", "7.1.5 Stowage codes",
                      "7.1.6 Handling codes", "7.2.8 Segregation codes"):
            start = CODE_PAGES[label] + offset - 1
            print(f"\n===== {label} — PDF p{start + 1} t/m p{start + 4} =====")
            for index in range(start, min(start + 4, document.page_count)):
                print(f"--- PDF p{index + 1} ---")
                print(document[index].get_text())

        # The segregation table is a grid: words with position, otherwise the
        # column layout cannot be recovered.
        start = CODE_PAGES["7.2.4 Segregation table"] + offset - 1
        print(f"\n===== 7.2.4 Segregation table — PDF p{start + 1}, woorden met positie =====")
        if 0 <= start < document.page_count:
            for word in document[start].get_text("words"):
                print(f"{word[0]:8.1f} {word[1]:8.1f}  {word[4]}")

        # Appendix 2 is the Dangerous Goods List: the top prize, and the hardest.
        start = CODE_PAGES["Appendix 2 (Dangerous Goods List)"] + offset - 1
        print(f"\n===== Appendix 2 — PDF p{start + 1} and p{start + 3}, words with position =====")
        for index in (start, start + 2):
            if 0 <= index < document.page_count:
                print(f"--- PDF p{index + 1} ---")
                for word in document[index].get_text("words")[:250]:
                    print(f"{word[0]:8.1f} {word[1]:8.1f}  {word[4]}")
    return 0


# Column headings of the Dangerous Goods List. A page carrying several of them
# is a DGL page; searching on the separate words gives too many false hits.
DGL_HEADINGS = ["UN No.", "Proper shipping name", "Class or division", "Subsidiary",
                "Packing group", "Special provisions", "Limited and excepted",
                "Packagings and IBCs", "Portable tanks", "EmS", "Stowage and handling",
                "Segregation", "Properties and observations"]

# A list line starts with a UN number. In this PDF every table cell comes out as
# a text line of its own, so the number often stands alone on its line; requiring
# the name behind it produces a systematic miss.
DGL_ROW = re.compile(r"^[ \t]*(\d{4})(?:[ \t]|$)", re.M)


def probe_dangerous_goods_list() -> int:
    """Is the full Dangerous Goods List in the document, and where?

    For part 3 the table of contents refers on to appendix 2. Where that appendix
    begins in the PDF cannot be derived from the code page number — an earlier
    attempt landed on chapter 3.1 — so this searches on structure rather than on
    a number: column headings and lines beginning with a UN number.
    """
    import fitz

    print("== Dangerous Goods List in the 42-24 document ==")
    try:
        path = download(CEPA, Path("/tmp/cepa.pdf"), timeout=600)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as error:
        print(f"  not reachable: {error}")
        return 1

    with fitz.open(path) as document:
        print(f"  {document.page_count} pagina's")

        # Where does the document name an appendix?
        for index in range(document.page_count):
            for match in re.finditer(r"^\s*Appendix\s+(\d)\b.{0,60}", document[index].get_text(), re.M):
                print(f"  'Appendix {match.group(1)}' op PDF p{index + 1}: "
                      f"{match.group(0).strip()[:70]}")

        # Measure first, judge second: too strict a pattern reports "nothing
        # found" where the list is simply laid out differently.
        heading_hits: dict[str, list[int]] = {}
        table_pages: list[int] = []
        un_numbers: set[str] = set()
        rows_per_page: dict[int, int] = {}
        for index in range(document.page_count):
            text = document[index].get_text(sort=True)
            for heading in DGL_HEADINGS:
                if heading in text:
                    heading_hits.setdefault(heading, []).append(index + 1)
            rows = [m.group(1) for m in DGL_ROW.finditer(text)
                    if 1 <= int(m.group(1)) <= 3999]
            if len(rows) >= 8:
                table_pages.append(index + 1)
                rows_per_page[index + 1] = len(rows)
                un_numbers.update(rows)

        print("\n  column headers of the list:")
        for heading in DGL_HEADINGS:
            pages = heading_hits.get(heading, [])
            print(f"    {heading:<30} {len(pages)}x"
                  + (f", first p{pages[0]}" if pages else ""))

        if not table_pages:
            print("\n  No page at all with eight or more UN numbers.")
            print("  The full Dangerous Goods List is NOT in this document.")
            print("\n  -- what is around 'Appendix 2' then? --")
            for index in range(562, min(570, document.page_count)):
                print(f"--- PDF p{index + 1} ---")
                print(document[index].get_text()[:1200])
            return 1

        # Summarise contiguous ranges; that reads as a location.
        ranges: list[tuple[int, int]] = []
        for page in table_pages:
            if ranges and page == ranges[-1][1] + 1:
                ranges[-1] = (ranges[-1][0], page)
            else:
                ranges.append((page, page))
        print(f"\n  {len(table_pages)} pagina's met lijststructuur, "
              f"{len(un_numbers)} verschillende UN-nummers")
        print("  bereiken: " + ", ".join(f"p{a}-p{b}" if a != b else f"p{a}"
                                         for a, b in ranges[:25]))

        # Does this cover the whole list? Our own database counts 2,336 with a card.
        for un in ("0004", "1203", "1361", "3480", "3551", "3560"):
            print(f"  UN {un}: {'present' if un in un_numbers else 'NOT found'}")

        biggest = max(rows_per_page, key=rows_per_page.get)
        print(f"\n===== dichtstbezette pagina p{biggest} "
              f"({rows_per_page[biggest]} rijen), platte tekst =====")
        print(document[biggest - 1].get_text()[:4000])
        print(f"\n===== p{biggest}, woorden met positie (eerste 300) =====")
        for word in document[biggest - 1].get_text("words")[:300]:
            print(f"{word[0]:8.1f} {word[1]:8.1f}  {word[4]}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", choices=["model-regs", "cepa", "dgl", "all"])
    parser.add_argument("--sample-pages", default="60,61,120",
                        help="DGL pages to print as a sample of the output")
    args = parser.parse_args(argv)

    pages = [int(p) for p in args.sample_pages.split(",") if p.strip().isdigit()]
    status = 0
    if args.source in {"model-regs", "all"}:
        status |= probe_model_regulations(pages)
    if args.source in {"cepa", "all"}:
        status |= probe_cepa()
    if args.source in {"dgl", "all"}:
        status |= probe_dangerous_goods_list()
    return status


if __name__ == "__main__":
    sys.exit(main())
