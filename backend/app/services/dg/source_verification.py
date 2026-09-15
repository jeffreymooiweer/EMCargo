"""Make missing IMDG source facts explicit and require a recorded assessment."""
from __future__ import annotations

import re
from app.core.languages import pick
from app.services.dg import dangerous_goods_list as dgl


def marine_pollutant_status(un: str, packing_group: str = "") -> str:
    rows = dgl.entries_for(un)
    if packing_group:
        rows = [r for r in rows if str(r.get("packing_group") or "").strip() == packing_group]
    if rows and all(re.search(r"\bP\b", dgl.value(r, "subsidiary_hazards")) for r in rows):
        return "yes"
    return "unknown"


def findings(entries: list[dict], language: str = "en") -> list[dict]:
    from app.services.dg.enrichment import segregation_provisions
    rules = segregation_provisions()
    found = []
    for entry in entries:
        for index, product in enumerate(entry.get("products") or []):
            un = str(product.get("un_number") or "")
            pg = str(product.get("packing_group") or "").strip()
            rows = dgl.entries_for(un)
            if pg:
                rows = [r for r in rows if str(r.get("packing_group") or "").strip() == pg]
            reasons = []
            if not rows:
                reasons.append("DGL")
            source = str(product.get("imdg_source_reference") or "").strip()
            verified = bool(source) and product.get("imdg_source_reviewed") == "Y"
            declared = str(product.get("marine_pollutant") or "").strip().upper()
            known = marine_pollutant_status(un, pg)
            positive = declared in {"P", "Y", "YES", "JA", "TRUE", "1"}
            negative = declared in {"N", "NO", "NEE", "FALSE", "0"}
            if known == "yes" and not positive:
                reasons.append("IMDG 2.10: P")
            elif known == "unknown" and (not verified or not (positive or negative)):
                reasons.append("IMDG 2.10")
            if product.get("carriage_mode") == "bulk" and not verified:
                reasons.append("IMDG 4.3: bulk")
            codes = {code for row in rows for code in dgl.segregation_codes(row)}
            if not verified:
                reasons += sorted(code for code in codes
                                  if code not in rules or rules[code].get("manual_review"))
            if not reasons:
                continue
            found.append({"rule": ", ".join(reasons), "severity": "error",
                          "code": "imdg.source_verification_required",
                          "products": f"UN {un} ({entry.get('line_id', '?')}/{index + 1})",
                          "message": pick({
                              "nl": "IMDG-brongegevens ontbreken of spreken elkaar tegen. Leg de stofbeoordeling, bron met editie/datum en controle vast. Een ontbrekende DGL-regel vereist eerst een geverifieerde bronupdate.",
                              "en": "IMDG source facts are missing or conflict. Record the substance assessment, source with edition/date and verification. A missing DGL row requires a verified source update first.",
                              "de": "IMDG-Quelldaten fehlen oder widersprechen sich. Stoffbeurteilung, Quelle mit Ausgabe/Datum und Prüfung dokumentieren. Eine fehlende DGL-Zeile erfordert zunächst eine verifizierte Quellenaktualisierung.",
                              "fr": "Des données sources IMDG manquent ou se contredisent. Documentez l’évaluation de la matière, la source avec édition/date et la vérification. Une ligne DGL manquante exige d’abord une mise à jour vérifiée de la source.",
                          }, language)})
    return found


def require_verified_payload(payload: dict) -> None:
    """Check the retained review inputs, including nested bundle documents."""
    from app.core.messages import error
    profiles = {str(p).upper() for p in payload.get("profiles", [])}
    if payload.get("document_key"):
        from app.services.documents.registry import get_document
        document = get_document(payload["document_key"]) or {}
        profiles.add(str(document.get("dg_profile", "")).upper())
    if "IMDG" in profiles or payload.get("modality") in {"sea", "maritime"}:
        if findings(payload.get("dangerous_goods") or []):
            raise error(409, "imdg.source_verification_required")
    bundle = payload.get("bundle")
    if isinstance(bundle, dict):
        require_verified_payload(bundle)
    for document in payload.get("documents") or []:
        if isinstance(document, dict):
            require_verified_payload(document)
