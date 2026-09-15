"""IMDG Code Amendment 42-24 as a differences layer over the 41-22 data.

Current substance data comes from the independently extracted 42-24 DGL.
This module retains the edition-change explanations and explicitly scoped
amendment facts. The historical Cantell seed and runtime overlay are retired.

Two things decide what is and is not in here:

- What the source states literally is in it. What it does not state is not
  invented; `not_covered` in the seed file lists what stays out of view.
- Chapter 7.2 has one change in 42-24: the rewording of 7.2.6.1. The segregation
  table of 7.2.4, the exemption tables of 7.2.6.3, the compatibility matrix of
  7.2.7.1.4 and the segregation groups of 3.1.4.4 stay unchanged. Those tables
  are therefore correct under 42-24 as well, and are no longer marked as lagging.

The published text of the Code remains authoritative; this is an aid to filling in.
"""
from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

from app.core.languages import SUPPORTED, pick

_SEED = Path(__file__).resolve().parents[3] / "seed" / "dg" / "imdg_42_24.json"

_lock = threading.Lock()
_cache: dict[str, Any] | None = None


def _load() -> dict[str, Any]:
    global _cache
    with _lock:
        if _cache is None:
            try:
                _cache = json.loads(_SEED.read_text(encoding="utf-8"))
            except (OSError, ValueError):  # pragma: no cover - seed ontbreekt
                _cache = {}
    return _cache


def _digits(un: str) -> str:
    return "".join(ch for ch in str(un or "") if ch.isdigit()).zfill(4)


def amendment() -> str:
    return str(_load().get("amendment") or "")


def source() -> str:
    return str(_load().get("source") or "")


def verified_unchanged_sections() -> list[str]:
    """Sections the source confirms 42-24 does not change."""
    data = _load().get("verified_unchanged") or {}
    return [item["section"] for item in data.get("sections", [])]


def new_un_numbers() -> list[dict[str, Any]]:
    """UN numbers 42-24 adds that do not yet exist in ADR 2025."""
    return list(_load().get("new_un_numbers") or [])


def ems_additions() -> dict[str, dict[str, str]]:
    return dict((_load().get("ems_additions") or {}).get("entries") or {})


def _entry_for(un: str, packing_group: str = "") -> dict[str, Any]:
    """The change for this UN number, per packing group where needed.

    UN 1835 and UN 3423 differ per packing group: the same substance, a different
    entry. Whoever does not pass the packing group gets only what applies to all
    groups — never the stricter variant silently.
    """
    change = (_load().get("amended_un_numbers") or {}).get(_digits(un))
    if not isinstance(change, dict):
        return {}
    by_group = change.get("by_packing_group")
    if not isinstance(by_group, dict):
        return change
    pg = str(packing_group or "").strip().upper()
    specific = by_group.get(pg)
    if isinstance(specific, dict):
        return {**{k: v for k, v in change.items() if k != "by_packing_group"}, **specific}
    return {k: v for k, v in change.items() if k != "by_packing_group"}


def changes_for(un: str, packing_group: str = "", language: str = "nl") -> list[str]:
    """What changes for this substance under 42-24, in plain words."""
    entry = _entry_for(un, packing_group)
    value = pick(
        {lang: entry.get(f"changes_{lang}") for lang in SUPPORTED}, language, []
    )
    return [str(line) for line in value if str(line).strip()]


def overlay_for(un: str, packing_group: str = "") -> dict[str, Any]:
    """The raw change fields for a substance, without the explanatory texts."""
    entry = _entry_for(un, packing_group)
    return {k: v for k, v in entry.items() if not k.startswith("changes_")}


def apply_card_overlay(un: str, card: dict[str, Any], packing_group: str = "") -> dict[str, Any]:
    """Update the data of the 41-22 UN card to 42-24.

    Adding and correcting only; nothing is removed that the source does not
    explicitly withdraw. A stowage code that was already in 41-22 stays.
    """
    overlay = overlay_for(un, packing_group)
    if not overlay or not isinstance(card, dict):
        return card
    updated = dict(card)

    added = [c for c in overlay.get("stowage_codes_add") or []
             if c not in (updated.get("stowage_codes") or [])]
    if added:
        updated["stowage_codes"] = list(updated.get("stowage_codes") or []) + added

    if overlay.get("marine_pollutant"):
        updated["marine_pollutant"] = overlay["marine_pollutant"]

    if overlay.get("stowage_category"):
        updated["stowage_category"] = overlay["stowage_category"]

    if added or overlay.get("marine_pollutant") or overlay.get("stowage_category"):
        updated["amended_by"] = "IMDG 42-24"
    return updated


def document_requirement(un: str, language: str = "nl") -> dict[str, Any] | None:
    """Additional document requirement per substance, such as 5.4.1.5.18 for UN 1361."""
    item = (_load().get("document_requirements") or {}).get(_digits(un))
    if not isinstance(item, dict):
        return None
    return {
        "section": item.get("section"),
        "text": pick(item, language),
        "fields": list(item.get("fields") or []),
    }


def general_document_requirements(language: str = "nl") -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for item in _load().get("general_document_requirements") or []:
        out.append({
            "section": item.get("section"),
            "text": pick(item, language),
            "special_provisions": list(item.get("special_provisions") or []),
        })
    return out


def amended_sections(language: str = "nl") -> list[dict[str, Any]]:
    data = (_load().get("verified_unchanged") or {}).get("amended_sections") or []
    return [
        {"section": i.get("section"), "text": pick(i, language)}
        for i in data
    ]


def not_covered(language: str = "nl") -> list[str]:
    data = _load().get("not_covered") or {}
    items = pick({lang: data.get(f"items_{lang}") for lang in SUPPORTED}, language, [])
    return [str(x) for x in items]
