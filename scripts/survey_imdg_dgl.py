"""A survey of the Dangerous Goods List in the 42-24 document.

This is the first of two steps and deliberately records nothing. The list covers
some 170 pages with eighteen columns, and a parser that silently reads one column
wrong is more dangerous than no parser at all: then there are 2,300 substances
with the wrong segregation code in the app without anybody noticing. So measure
first:

1. Where exactly does the list begin and end?
2. Where are the column boundaries? Those are derived from the x positions of the
   heading and checked against the x positions of the data itself.
3. Which UN numbers does the list yield, and how does that compare with the 2,336
   numbers we currently know from the 41-22 UN cards? Every difference is a
   clue: a missed page, a row laid out differently, or a real change in 42-24.

The earlier probe reported that UN 1361, 3551 and 3560 were missing while there
were gaps in the page range at p734 and p757. Those three are precisely 42-24
changes, so that points to a reading error rather than to missing data; this
survey has to settle it.

Runs via GitHub Actions, because the development environment has no outbound
network. What ends up in the repo in the end is derived data, never the
regulatory text.

Usage::

    python scripts/survey_imdg_dgl.py
    python scripts/survey_imdg_dgl.py --sample-pages 600,650 --pdf /tmp/imdg.pdf
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from collections import Counter
from pathlib import Path

SOURCE_URL = "https://www.cepa.be/wp-content/uploads/IMDG_Code-amdt_42_24.pdf"
UA = {"User-Agent": "EMCargo data survey (github.com/jeffreymooiweer/emcargo)"}
ADR_DATA = Path(__file__).resolve().parents[1] / "backend" / "seed" / "dg" / "un_numbers.json"

# A page of the list carries these headings. They are not all on every page — the
# list runs across two facing pages — so two hits is enough to mark a page as a
# list page.
HEADINGS = ["UN No.", "Proper shipping name", "Class or division", "Subsidiary",
            "Packing group", "Special provisions", "Limited and excepted",
            "Packagings and IBCs", "Portable tanks", "EmS", "Stowage and handling",
            "Segregation", "Properties and observations"]

# A row begins with a UN number on a text line of its own. Without re.MULTILINE,
# ^ matches only the beginning of the whole page text; that has put this survey
# on a false negative twice already.
ROW_START = re.compile(r"^[ \t]*(\d{4})(?:[ \t]|$)", re.M)


def download(url: str, target: Path, timeout: int = 600) -> Path:
    request = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        target.write_bytes(response.read())
    return target


def known_un_numbers() -> set[str]:
    """The independent UN numbers in ADR Table A."""
    try:
        return {str(row["un"]) for row in json.loads(ADR_DATA.read_text(encoding="utf-8"))}
    except (OSError, ValueError, KeyError):  # pragma: no cover - seed ontbreekt
        return set()


def list_pages(document) -> list[int]:
    """Pages belonging to the list itself, recognised by their headings.

    Searching on headings rather than on rows: the segregation group lists of
    3.1.4.4 also start with UN numbers and do not belong here.
    """
    pages = []
    for index in range(document.page_count):
        text = document[index].get_text()
        if sum(1 for heading in HEADINGS if heading in text) >= 2:
            pages.append(index + 1)
    return pages


def contiguous(pages: list[int]) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    for page in pages:
        if ranges and page == ranges[-1][1] + 1:
            ranges[-1] = (ranges[-1][0], page)
        else:
            ranges.append((page, page))
    return ranges


def column_positions(document, pages: list[int], limit: int = 40) -> list[tuple[float, int]]:
    """The x positions text starts at, counted over a number of list pages.

    In a fixed table layout those positions cluster around the column
    boundaries. What sits between the clusters is continuous text within a column.
    """
    counts: Counter[float] = Counter()
    for page in pages[:limit]:
        for word in document[page - 1].get_text("words"):
            counts[round(word[0], 1)] += 1
    return sorted(counts.items())


def cluster(positions: list[tuple[float, int]], gap: float = 4.0,
            floor: int = 20) -> list[tuple[float, float, int]]:
    """Naburige x-posities samennemen tot kolomkandidaten."""
    clusters: list[list[tuple[float, int]]] = []
    for x, count in positions:
        if count < floor:
            continue
        if clusters and x - clusters[-1][-1][0] <= gap:
            clusters[-1].append((x, count))
        else:
            clusters.append([(x, count)])
    return [(c[0][0], c[-1][0], sum(n for _, n in c)) for c in clusters]


def survey(path: Path, sample_pages: list[int]) -> int:
    import fitz

    print(f"source: {path} ({path.stat().st_size} bytes)")
    with fitz.open(path) as document:
        print(f"{document.page_count} pages\n")

        pages = list_pages(document)
        if not pages:
            print("No list pages recognised by their header.")
            return 1
        ranges = contiguous(pages)
        print(f"== list pages: {len(pages)} ==")
        print("  " + ", ".join(f"p{a}-p{b}" if a != b else f"p{a}" for a, b in ranges))

        # Gaps inside the range are suspect: a list runs on.
        gaps = [p for p in range(pages[0], pages[-1] + 1) if p not in set(pages)]
        print(f"  gaps inside the range: {gaps or 'none'}")
        for page in gaps[:6]:
            first = document[page - 1].get_text().strip().splitlines()[:3]
            print(f"    p{page}: {' | '.join(line.strip() for line in first)}")

        print("\n== column positions over the first 40 list pages ==")
        clusters = cluster(column_positions(document, pages))
        for start, end, count in clusters:
            print(f"  x {start:7.1f} - {end:7.1f}   {count:6d} words")

        for number in sample_pages:
            if not 0 < number <= document.page_count:
                continue
            print(f"\n===== p{number}: header with position =====")
            words = document[number - 1].get_text("words")
            top = [w for w in words if w[1] < 120]
            for word in sorted(top, key=lambda w: (round(w[1], 1), w[0]))[:80]:
                print(f"{word[0]:8.1f} {word[1]:8.1f}  {word[4]}")

        # Coverage: what the list yields against what we already have.
        found: dict[str, int] = {}
        rows_per_page: dict[int, int] = {}
        for page in pages:
            numbers = [m.group(1) for m in ROW_START.finditer(document[page - 1].get_text())]
            rows_per_page[page] = len(numbers)
            for un in numbers:
                found.setdefault(un, page)

        known = known_un_numbers()
        print(f"\n== coverage ==")
        print(f"  UN numbers in the list   : {len(found)}")
        print(f"  UN numbers from the cards (41-22): {len(known)}")
        print(f"  rows in total            : {sum(rows_per_page.values())}")
        if known:
            missing = sorted(known - set(found))
            extra = sorted(set(found) - known)
            print(f"  on a card, not in the list: {len(missing)}")
            print(f"    {missing[:40]}{' …' if len(missing) > 40 else ''}")
            print(f"  in the list, no card      : {len(extra)}")
            print(f"    {extra[:40]}{' …' if len(extra) > 40 else ''}")

        # The three the earlier probe missed, checked separately: are they
        # anywhere in the document, and if so how are they laid out there?
        print("\n== the numbers that were missing before ==")
        for un in ("1361", "3551", "3552", "3556", "3560", "0514", "3553"):
            page = found.get(un)
            if page:
                print(f"  UN {un}: row on p{page}")
                continue
            hits = [i + 1 for i in range(document.page_count)
                    if re.search(rf"\b{un}\b", document[i].get_text())]
            inside = [p for p in hits if p in set(pages)]
            print(f"  UN {un}: no row. Appears on {hits[:8]}"
                  f"{' …' if len(hits) > 8 else ''}; of those, list pages: {inside[:8]}")
            for p in inside[:1]:
                context = document[p - 1].get_text()
                spot = context.find(un)
                print(f"      context p{p}: ...{context[max(0, spot - 120):spot + 160]!r}...")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", type=Path, help="Reuse an already downloaded file")
    parser.add_argument("--sample-pages", default="600,601",
                        help="List pages whose header is printed")
    args = parser.parse_args(argv)

    path = args.pdf or download(SOURCE_URL, Path("/tmp/imdg_42_24.pdf"))
    pages = [int(p) for p in args.sample_pages.split(",") if p.strip().isdigit()]
    return survey(path, pages)


if __name__ == "__main__":
    sys.exit(main())
