"""Parse the independently sourced descriptions in IMDG 7.2.8.

This module contains project-owned parsing logic, no third-party card text.
The input is imdg_codes.json, whose own rights remain separately registered.
"""
from __future__ import annotations
import re

ACTIONS = [
    ("separated longitudinally by an intervening complete compartment or hold from",
     "separated_longitudinally"),
    ("separated by a complete compartment or hold from", "separated_by_compartment"),
    ("separated from", "separated_from"),
    ("away from", "away_from"),
]
AS_FOR_CLASS = re.compile(r"[Ss]egregation as for (?:class\s+)?([\d.]+[A-Z]?)\b")
CLASS_TOKEN = re.compile(r"\b(?:class|classes|division|divisions)\s+([\d.]+[A-Z]?(?:\s*,?\s*(?:and\s+)?[\d.]+[A-Z]?)*)")
GROUP_TOKEN = re.compile(r"\bSGG(\d{1,2}a?)\b")


def parse_provision(code: str, sentence: str) -> dict[str, object]:
    """Turn one IMDG code description into a rule the compliance check can apply.

    Sentences that name a class or a segregation group become actionable.
    Anything else — foodstuffs, a named substance, a cross-reference to a table
    in the Code — is kept as text and shown to the user without being acted on.
    """
    rule: dict[str, object] = {"code": code, "text": sentence}

    # These descriptions contain conditional or multiple instructions. A
    # single-action parser cannot safely collapse them into one class target.
    if code in {"SG1", "SG34", "SG39", "SG40", "SG67", "SG68", "SG69", "SG70", "SG77"}:
        return {**rule, "informational": True, "manual_review": True}

    for phrase, action in ACTIONS:
        if f"\u201c{phrase}\u201d" in sentence or f'"{phrase}"' in sentence:
            rule["action"] = action
            break

    as_for = AS_FOR_CLASS.search(sentence)
    if as_for and "action" not in rule:
        rule["action"] = "segregate_as_class"
        rule["as_class"] = as_for.group(1)
        return rule

    # Only look for a target after the action phrase, so "class 1" in
    # "in relation to goods of class 1" is not mistaken for the target.
    tail = sentence
    for phrase, _action in ACTIONS:
        marker = f"\u201c{phrase}\u201d"
        if marker in sentence:
            tail = sentence.split(marker, 1)[1]
            break

    # "class 1 except for division 1.4S" names one target and one exception.
    # Reading the exception as a second target would warn about a load the Code
    # explicitly allows.
    excepted: list[str] = []
    if re.search(r"\bexcept\b", tail, re.IGNORECASE):
        tail, _, exception_tail = re.split(r"\bexcept\b", tail, maxsplit=1, flags=re.IGNORECASE)[0], "except", \
            re.split(r"\bexcept\b", tail, maxsplit=1, flags=re.IGNORECASE)[1]
        for match in CLASS_TOKEN.finditer(exception_tail):
            for token in re.split(r"[,\s]+(?:and\s+)?", match.group(1)):
                token = token.strip(" .,")
                if token and token not in excepted:
                    excepted.append(token)

    classes: list[str] = []
    for match in CLASS_TOKEN.finditer(tail):
        for token in re.split(r"[,\s]+(?:and\s+)?", match.group(1)):
            token = token.strip(" .,")
            if token and token not in classes:
                classes.append(token)
    groups = [f"SGG{n}" for n in GROUP_TOKEN.findall(tail)]

    targets: dict[str, list[str]] = {}
    if classes:
        targets["classes"] = classes
    if groups:
        targets["groups"] = list(dict.fromkeys(groups))
    if targets and rule.get("action"):
        rule["targets"] = targets
        if excepted:
            rule["excepted_classes"] = excepted
    else:
        rule["informational"] = True
    return rule
