"""The whole shipment as structured data, versioned, for something else to read.

Every other exporter in this package produces paper. This one produces the
shipment itself: what was filled in, what was carried, and — the part that
makes it worth more than a form dump — **what EMCargo worked out**. A
receiving system that gets only the typed fields has to re-derive the
regulatory answer, and re-derivation is where two systems start to disagree.

Why now, and why JSON rather than a standard. The EU eFTI Regulation applies in
full from 9 July 2027, from when authorities must accept freight information
electronically through certified platforms, and the eFTI data set is built on
the UN/CEFACT Multi-Modal Transport reference data model. EMCargo is not
going to become a certified platform — that is a certification regime for
platform providers, and this application is a documentation tool. What it can
be is trivially connectable to one. That starts with a shipment being able to
leave as structured data at all, which is what this is.

So the format is EMCargo's own and says so. Mapping it onto MMT-RDM is a
separate exercise against the published model, and inventing half a mapping
here would be worse than none: a field named as though it were the standard's,
carrying something subtly else, is exactly the failure that makes an integration
silently wrong. ``docs/shipment-export.md`` records what is known about the
correspondence and what still has to be read.

Three rules the format follows.

**Versioned, and the version means something.** ``format_version`` changes when
a reader would break. A field added is not a break; a field renamed, removed or
given a different meaning is. A reader that checks the major version and ignores
keys it does not know will keep working.

**Nothing is invented.** A field the user left empty is absent, not an empty
string, and a check that did not run is absent rather than reported as passing.
The compliance answer travels exactly as the panel received it, with the
editions it was computed against — which the answer already names — so a
shipment exported today can be told apart from the same shipment re-derived
under a later edition.

**It carries no user and no installation.** The export describes a consignment,
not who typed it. That keeps it the same file whoever produces it, and keeps
``docs/privacy.md``'s promise that a finished job leaves nothing behind.
"""
from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.services.dg.compliance import check_compliance
from app.version import get_version

#: The format's own version, not the application's. Bump the major when a
#: reader that understood the previous version would misread this one; bump the
#: minor when something is added that an old reader can safely ignore.
FORMAT = "emcargo.shipment"
FORMAT_VERSION = "3.0"


def _clean(value: Any) -> Any:
    """Drop what was never filled in, keep what was deliberately zero.

    An empty string is absence: the wizard writes one into every field it
    renders, so exporting them would fill the file with keys that mean
    "untouched" while looking like answers. A zero, a false and an empty list
    are not absence — somebody chose them — and they stay.
    """
    if isinstance(value, dict):
        cleaned = {key: _clean(item) for key, item in value.items()}
        return {key: item for key, item in cleaned.items() if item is not None}
    if isinstance(value, list):
        return [_clean(item) for item in value]
    if value is None:
        return None
    if isinstance(value, str) and not value.strip():
        return None
    return value


def build_shipment_export(
    values: dict[str, Any],
    lines: list[dict[str, Any]],
    dangerous_goods: list[dict[str, Any]] | None,
    language: str = "nl",
    profiles: list[str] | None = None,
    modality: str | None = None,
    documents: list[str] | None = None,
    cargo=None,
    routing=None,
) -> dict[str, Any]:
    """The shipment as a dictionary, ready to be written or returned.

    Kept apart from the file writing so the same structure can be served as an
    API response without going through a temporary file, which is what the
    roadmap's "documented as an API response" asks for.
    """
    entries = list(dangerous_goods or [])
    regimes = [str(profile).strip().upper() for profile in (profiles or []) if str(profile).strip()]

    export: dict[str, Any] = {
        "format": FORMAT,
        "format_version": FORMAT_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "generator": {
            "application": "EMCargo",
            "version": get_version(),
        },
        "language": language,
        "consignment": _clean(dict(values or {})),
        "goods": _clean(list(lines or [])),
    }
    if routing is not None:
        export["routing"] = routing.model_dump(mode="json")
    if cargo is not None:
        from app.services.cargo import assess
        assessment = assess(cargo, lines)
        export["cargo"] = assessment["cargo"]
        export["cargo_assessment"] = {key: value for key, value in assessment.items() if key != "cargo"}
    if modality:
        export["modality"] = modality
    if regimes:
        export["regulations"] = regimes
    if documents:
        export["documents"] = list(documents)
    if entries:
        export["dangerous_goods"] = _clean(entries)
        # The derived half. Without it a reader has the declaration and not the
        # assessment, and would have to compute its own — which is where two
        # systems begin to disagree about the same consignment. The answer
        # names the editions it was computed against, so a later reader can see
        # whether it is looking at today's rules or the ones that applied.
        if regimes:
            export["compliance"] = _clean(
                check_compliance(entries, regimes, language))
    return export


def render_shipment_export(
    values: dict[str, Any],
    lines: list[dict[str, Any]],
    dangerous_goods: list[dict[str, Any]] | None,
    language: str = "nl",
    profiles: list[str] | None = None,
    modality: str | None = None,
    documents: list[str] | None = None,
    cargo=None,
) -> Path:
    """The same structure as a file, for the export step and the bundle."""
    export = build_shipment_export(
        values, lines, dangerous_goods, language, profiles, modality, documents, cargo)
    fd, name = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    out_path = Path(name)
    try:
        out_path.chmod(0o600)
    except OSError:
        pass
    # Indented and with the non-ASCII left alone: this file is meant to be read
    # by a person as often as by a program — the first thing anyone does with a
    # new integration format is open it and look.
    out_path.write_text(
        json.dumps(export, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8")
    return out_path
