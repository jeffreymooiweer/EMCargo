"""What a source adapter owes the renderer, and nothing more.

Every value on a card must be traceable to a measured regulatory table — the
seed files under ``backend/seed/dg/``, each of which records the edition it
was read from and the script that read it. An adapter therefore never
computes, guesses or defaults a regulatory value: it copies fields out of its
table, labels them, and hands them over. A field the table does not carry is
*absent* from the card, and a modality whose table this repository does not
hold raises :class:`SourceUnavailable` so the generation fails aloud instead
of shipping an invented card.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SEED = REPO / "backend" / "seed" / "dg"

MODALITIES = ("ADR", "RID", "ADN", "IMDG", "ICAO")


class SourceUnavailable(Exception):
    """This repository holds no measured table for the modality.

    The message states what is missing and where it would come from, because
    the generation report prints it verbatim: honest absence is part of the
    product, a silently skipped modality is not.
    """


@dataclass
class CardPage:
    """One transport entry of one UN number under one modality.

    A UN number with several valid entries in the same table yields several
    pages inside the same ``UN####_<MODALITY>.pdf`` — never a silent pick of
    the first row.
    """

    modality: str
    un: str
    #: Proper shipping name per language, only the languages the seed carries.
    names: dict[str, str]
    klass: str
    packing_group: str
    classification_code: str
    #: Label codes exactly as the table prints them, e.g. ["2.3", "5.1", "8"].
    labels: list[str] = field(default_factory=list)
    #: Extra cells on the identity row, per modality: [(label, value)].
    identity_extra: list[tuple[str, str]] = field(default_factory=list)
    #: Extra cells beside the hazard labels, per modality: [(label, value)].
    label_extra: list[tuple[str, str]] = field(default_factory=list)
    #: The package marking line, e.g. "UN 1203 MOTOR SPIRIT or GASOLINE or PETROL".
    marking: str = ""
    #: Rows of the packaging band: [(label, text)].
    packaging_rows: list[tuple[str, str]] = field(default_factory=list)
    #: Cells of the tank / bulk / modality band: [(label, value)].
    tank_rows: list[tuple[str, str]] = field(default_factory=list)
    #: Rows under "Special transport provisions": [(label, text)].
    provision_rows: list[tuple[str, str]] = field(default_factory=list)
    #: (limited quantities text, excepted quantities text); either may be "".
    lq_eq: tuple[str, str] | None = None
    #: The regulation and edition this page was read from, e.g. "ADR 2025".
    regulation: str = ""
    #: Full provenance, rendered without truncation in the source section.
    source: str = ""


def dash(value: str | None) -> str:
    """The table's own empty cell, printed as an em dash rather than dropped."""
    value = (value or "").strip()
    return value if value else "—"
