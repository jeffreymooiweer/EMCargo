"""Which edition of which regulations sits in this installation.

EMCargo computes with five rule sets, each with its own revision rhythm: ADR
every two years, the IMDG Code every two years with a transitional year, the
IATA DGR *every* year. Until now that provenance was spread over the seeds, the
compliance configuration and the documentation, and there was no way to see from
the outside what a running installation actually uses.

That is not merely bookkeeping. The IATA DGR 67th edition applies up to and
including 31 December 2026; on 1 January 2027 this app computes with an expired
edition and there is nothing that says so. The manifest therefore carries a
validity period per rule set, and `expired_rule_sets()` turns that into a
statement.

The checksum is there for the opposite case: a seed that changed quietly. Two
installations reporting the same manifest id compute with the same data.
"""
from __future__ import annotations

import hashlib
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.version import get_version

SEED = Path(__file__).resolve().parents[2] / "seed" / "dg"
CONFIG = Path(__file__).resolve().parents[1] / "config"

# Per rule set: what applies, where it comes from and which files carry it.
# Only what can be substantiated against a source — where something has not been
# kept up, it says so, because "unknown" is a more usable answer than an edition
# number nobody has checked.
RULE_SETS: list[dict[str, Any]] = [
    {
        "key": "adr",
        "profiles": ["ADR", "RID", "ADN"],
        "name": "ADR — carriage by road",
        "edition": "2025",
        "source": ("UNECE ADR 2025 for the provisions; table A read out of the "
                   "official Dutch ADR 2025 edition and checked against the "
                   "alphabetical index of that edition; English and German "
                   "proper shipping names via rkstgr/adr-substances"),
        "source_url": "https://unece.org/transport/dangerous-goods/adr-2025-files",
        "valid_from": "2025-01-01",
        # ADR is revised every two years; ADR 2027 replaces this edition, with a
        # transitional period to 30 June of that year.
        "valid_until": "2027-06-30",
        # Measured against the Dutch ADR 2025 while the Dutch names were being
        # read out, and therefore stated here rather than left to be discovered.
        "errata": [
            "Table A has no English column — the edition read is the Dutch one "
            "— so the English names still come from the 2023 export. Where 2025 "
            "moved a field the row cannot be matched and the UN number's name "
            "is used, which for 55 UN numbers with per-row names can be the "
            "wrong variant. The German names no longer come from that export: "
            "since v1.79.0 they are read from the ADR 2025 of the Bundesamt "
            "für Strassen, 2,346 UN numbers, of which 2,210 read exactly as "
            "the export had them.",
            "A carriage prohibition is not in the Dutch table in words: the row "
            "is simply left empty, which is also how an entry not subject to "
            "ADR is written. The fourteen prohibited UN numbers therefore come "
            "from the 2023 export, which names them.",
        ],
        "covers": [
            "classification per UN number (class, packing group, labels, LQ/EQ)",
            "the carriage provisions of columns (16) to (19)",
            "Dutch, French and German proper shipping names from Table A, column (2)",
            "1.1.3.6 points calculation",
            "7.5.2 mixed loading and 7.5.4/CV28",
        ],
        "files": ["adr_table_a.json", "un_numbers.json", "adr_names_nl.json",
                  "adr_names_fr.json", "adr_names_de.json",
                  "adr_2025_additions.json", "packagings.json",
                  "adn_table_a.json", "adn_table_c.json"],
    },
    {
        "key": "imdg",
        "profiles": ["IMDG"],
        "name": "IMDG Code — carriage by sea",
        "edition": "Amendment 42-24 (2024 Edition)",
        "source": "IMO resolution MSC.556(108), adopted 23 May 2024",
        "source_url": "https://www.cepa.be/wp-content/uploads/IMDG_Code-amdt_42_24.pdf",
        "valid_from": "2026-01-01",
        # 44-26 follows the usual two-yearly cycle.
        "valid_until": "2028-12-31",
        "errata": [],
        "covers": [
            "Dangerous Goods List (chapter 3.2), including columns 16a and 16b",
            "stowage, handling and segregation codes (7.1.5, 7.1.6, 7.2.8)",
            "the 42-24 difference layer over the 41-22 UN cards",
        ],
        "files": ["imdg_dgl.json", "imdg_codes.json", "imdg_42_24.json"],
    },
    {
        "key": "imdg_class_tables",
        "profiles": ["IMDG"],
        "name": "IMDG Code — segregation tables of chapters 7.2 and 3.1.4.4",
        "edition": "Amendment 40-20, verified unchanged in 42-24",
        "source": (
            "IMDG Code chapters 7.2 and 3.1.4.4. Sections 7.2.4, 7.2.6.3, "
            "7.2.7.1.4 and 3.1.4.4 were checked against 42-24 and are "
            "unchanged; the only change in 7.2 is a rewording of 7.2.6.1."
        ),
        "valid_from": "2026-01-01",
        "valid_until": "2028-12-31",
        "errata": [],
        "covers": [
            "7.2.4 class segregation table",
            "7.2.6.3 exemption tables",
            "7.2.7.1.4 class 1 compatibility matrix",
            "3.1.4.4 segregation groups",
        ],
        "files": ["segregation_groups.json"],
    },
    {
        "key": "ems",
        "profiles": ["IMDG"],
        "name": "EmS Guide — emergency procedures on board",
        "edition": "MSC.1/Circ.1588/Rev.3",
        "source": "IMO MSC.1/Circ.1588/Rev.3, EmS Guide — index per UN number",
        "valid_from": "2022-05-01",
        # A circular has no end date; it applies until a Rev.4 appears.
        "valid_until": None,
        "errata": [
            "The UN numbers 42-24 adds are not yet in this index; their "
            "schedules come from imdg_42_24.json."
        ],
        "covers": ["fire and spillage schedules per UN number"],
        "files": ["ems.json"],
    },
    {
        "key": "iata",
        "profiles": ["IATA"],
        "name": "IATA DGR — air freight",
        "edition": "67th edition (2026)",
        "source": "IATA Dangerous Goods Regulations, 67th edition",
        "valid_from": "2026-01-01",
        # The DGR is replaced annually; edition 68 applies from 1-1-2027.
        "valid_until": "2026-12-31",
        "errata": [
            "Addenda and operator/state variations are not tracked; consult "
            "those separately.",
        ],
        "covers": [
            "9.3.2 Table 9.3.A segregation",
            "5.0.2.11 Q value for 'all packed in one'",
            "lithium and sodium-ion batteries (Guidance 2026)",
        ],
        "files": [],
    },
    {
        "key": "imdg_un_cards",
        "profiles": ["IMDG"],
        # Expired, and we know it: columns 16a and 16b have come from the 42-24
        # Dangerous Goods List since v1.23.0. What the cards still supply —
        # marine pollutant and bulk — did not change with the edition. Warning
        # about this on every check would make the warning itself worthless.
        "superseded_by": "imdg",
        "name": "IMDG UN cards — supplementary substance data",
        "edition": "41-22 (2023)",
        # The card PDFs themselves left the repository in v1.129.0 (the
        # application now generates its own cards); the data extracted from
        # them is retired; this record only preserves the historical provenance.
        "source": "Cantell IMDG UN cards, 2023 edition (source PDFs no longer bundled)",
        "valid_from": "2024-01-01",
        "valid_until": "2025-12-31",
        "errata": [
            "Superseded for columns 16a and 16b: those have come from the "
            "42-24 Dangerous Goods List since v1.23.0.",
            "The class is unusable for UN 2984-2992, 3548 and 3550: those "
            "hold sequence numbers instead of classes.",
        ],
        "covers": [],
        "files": [],
        "retired": True,
    },
]


def _checksum(path: Path) -> dict[str, Any] | None:
    """Content hash of a data file.

    The hash is over the content and not over the timestamp: the latter differs
    per build without the data changing, and would make two identical
    installations look different.
    """
    try:
        data = path.read_bytes()
    except OSError:  # pragma: no cover - file is missing
        return None
    return {
        "file": path.name,
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def _parse(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


def rule_set_status(rule_set: dict[str, Any], today: date) -> str:
    """"current", "not_yet_in_force" or "expired"."""
    starts = _parse(rule_set.get("valid_from"))
    ends = _parse(rule_set.get("valid_until"))
    if starts and today < starts:
        return "not_yet_in_force"
    if ends and today > ends:
        return "expired"
    return "current"


def build_manifest(today: date | None = None) -> dict[str, Any]:
    """The full manifest, with checksums and validity."""
    today = today or date.today()
    rule_sets = []
    digest = hashlib.sha256()

    for entry in RULE_SETS:
        datasets = [c for name in entry["files"] if (c := _checksum(SEED / name))]
        for dataset in datasets:
            digest.update(dataset["sha256"].encode())
        rule_sets.append({
            **{k: v for k, v in entry.items() if k != "files"},
            "status": rule_set_status(entry, today),
            "datasets": datasets,
        })

    # One id over all data files together: two installations reporting the same
    # id compute with the same data.
    return {
        "manifest_version": 1,
        "application_version": get_version(),
        "generated_for": today.isoformat(),
        "manifest_id": digest.hexdigest()[:16],
        "rule_sets": rule_sets,
        "disclaimer": (
            "A compilation of facts, offered as an aid to filling in documents. "
            "The published editions of ADR, RID, ADN, the IMDG Code and the IATA "
            "DGR remain authoritative; see TERMS.nl.md."
        ),
    }


def stale_rule_sets(profiles: list[str] | None = None,
                    today: date | None = None) -> list[dict[str, Any]]:
    """Rule sets that have expired without anything taking their place.

    This is not the same as `expired_rule_sets()`. The 41-22 UN cards have
    expired *and* been deliberately replaced: columns 16a and 16b come from the
    42-24 list and what the cards still supply did not change with the edition.
    Warning about that on every check would make the warning itself worthless —
    whoever dismisses a message every time will dismiss the one that matters too.

    What remains is the case this is meant for: an edition that has run out and
    that nobody has done anything about. Today that yields nothing; on 1 January
    2027 it yields the IATA DGR.
    """
    today = today or date.today()
    wanted = {str(p).strip().upper() for p in (profiles or [])}
    out = []
    for entry in RULE_SETS:
        if rule_set_status(entry, today) != "expired" or entry.get("superseded_by"):
            continue
        covered = {p.upper() for p in entry.get("profiles", [])}
        if wanted and not (covered & wanted):
            continue
        out.append({
            "key": entry["key"],
            "name": entry["name"],
            "edition": entry["edition"],
            "expired_on": entry["valid_until"],
            "profiles": entry.get("profiles", []),
        })
    return out


def expired_rule_sets(today: date | None = None) -> list[str]:
    """The rule sets that are no longer valid on this date.

    With this the app can say that it is computing with an expired edition,
    instead of quietly going on doing so.
    """
    today = today or date.today()
    return [r["key"] for r in RULE_SETS if rule_set_status(r, today) == "expired"]


@lru_cache
def _cached_summary() -> dict[str, str]:
    return {r["key"]: r["edition"] for r in RULE_SETS}


def summary(today: date | None = None) -> dict[str, Any]:
    """Compact form, small enough to hang off /api/health."""
    manifest = build_manifest(today)
    return {
        "manifest_id": manifest["manifest_id"],
        "editions": _cached_summary(),
        "expired": expired_rule_sets(today),
    }
