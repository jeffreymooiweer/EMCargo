"""Errors the user reads, in a form the interface can translate.

Until v1.48.0 every message the API sent back was a Dutch sentence written
straight into the ``raise``. A German user who uploaded an empty file was told so
in Dutch; so was a French one who asked for a UN number the ADR table does not
hold. The interface speaks four languages and its errors spoke one, which is the
kind of gap nobody reports because it only shows up once something has already
gone wrong.

The backend does not translate. It cannot: the message may be raised deep in a
service that has no idea who is asking, and the language belongs to the screen,
not to the server. What it sends instead is a **code**, the parameters that go
in the sentence, and an English text as a fallback:

    {"code": "import.empty_file", "message": "Empty file", "params": {}}

The interface looks the code up in its own language files and falls back to
``message`` when it does not know it — so an error is always readable, even one
added by a newer backend than the frontend in front of it.

Codes are dotted and stable. Renaming one is a breaking change for the
translations, and ``test_error_messages.py`` holds every code here to a key in
all four language files.
"""
from __future__ import annotations

from typing import Any

from fastapi import HTTPException


class ApiError(HTTPException):
    """An HTTP error the interface can translate.

    ``detail`` is a dict rather than a string. FastAPI's own validation errors
    are already a list of dicts, so the interface had to cope with a non-string
    detail regardless; this makes the two paths consistent instead of adding a
    third shape.
    """

    def __init__(self, status_code: int, code: str, message: str, **params: Any) -> None:
        super().__init__(
            status_code=status_code,
            detail={"code": code, "message": message, "params": params},
        )
        self.code = code


#: The English fallback text per code, with the parameters it interpolates.
#: Kept here rather than at the raise sites so that the set of codes is
#: countable — a translation guard cannot check what it cannot enumerate.
MESSAGES: dict[str, str] = {
    "auth.current_password_incorrect": "Your current password is incorrect.",
    "un_cards.no_release": "No UN card set has been published yet. Check for a new set later or import a ZIP file.",
    "un_cards.download_failed": "The card set could not be downloaded. Try again or import a ZIP file.",
    "trips.empty": "Add at least one shipment to the trip.",
    "documents.goods_incomplete": "Complete the goods description, quantity and weight before downloading the consignment note",
    "assistant.model_required": "Install the local language model in Settings before using the assistant. You can continue manually in the wizard.",
    'permissions.manager_required': 'Operational management access is required.',
    'permissions.specialist_required': 'Only a DG Specialist can release shipments.',
    'permissions.dgsa_required': 'You do not have access to DGSA reports.',
    'permissions.protected_account': 'Only an admin can manage this account.',
    'review.required': 'This shipment must first be released by a DG Specialist.',
    'review.changed': 'The shipment changed after release. Submit the new version for review.',
    'review.not_found': 'Review not found.',
    'review.incomplete': 'Complete the DG declaration and selected documents before submitting.',
    'review.inconsistent': 'Document data does not match the shipment. Open the wizard and submit again.',
    'review.too_large': 'This request is too large. The limit is 3 MB.',
    'review.comment_required': 'Explain what needs to be changed.',
    'review.already_decided': 'This review already has a decision. Refresh the page.',
    'review.owner_required': 'Only the submitter or admin can delete this review.',

    "avatar.invalid": "Choose a valid, static JPG, PNG or WebP image.",
    "avatar.too_large": "Choose an image up to 5 MB and 16 megapixels.",
    "avatar.not_found": "Profile photo not found.",
    "update.unavailable": "In-app updating is unavailable. Check Settings / Updates for the installation requirements.",
    "update.no_update": "There is no newer release to install. Check for updates again.",
    "update.check_disabled": "Update checks are switched off",
    "update.in_progress": "An update is already in progress",
    # Uploading and importing
    "import.filename_missing": "The file has no name",
    "import.empty_file": "The file is empty",
    "import.no_usable_lines": "No importable lines found",
    "import.no_rows_to_map": "No rows to map",
    "import.description_column_required": (
        "Without a description column there is nothing to recognise"
    ),
    "import.file_too_large": "The file is larger than {limit_mb} MB",
    "import.too_many_rows": "The import holds {rows} rows; at most {limit} are allowed",
    "import.too_many_columns": (
        "Row {row} holds {columns} columns; at most {limit} are allowed"
    ),
    "import.cell_too_long": "Cell {row}:{column} holds more than {limit} characters",
    "import.unpacked_too_large": "The unpacked spreadsheet is larger than {limit_mb} MB",
    "import.unreadable_file": "The file cannot be read as a spreadsheet",
    # Signing in
    "auth.two_factor_required": (
        "This installation requires two-factor verification for your account. "
        "Set it up under User settings, Security, before doing anything else"
    ),
    "auth.two_factor_invalid_code": "That verification code is not valid",
    "auth.two_factor_inactive": "Two-factor verification is not switched on",
    # Equipment import, reported per row rather than as an HTTP error
    "equipment.row_weight_missing": "Row {row}: the weight is missing or unusable",
    # Articles import, reported per row
    "articles.row_refused": "Row {row}: {reason}",
    # Dangerous goods
    "dg.un_number_not_found": "UN number not found in the ADR database",
    # Quantities, raised by the schema validators
    "dg.quantity_not_a_number": "quantity {value} holds no number",
    "dg.quantity_not_positive": "quantity {value} must be greater than zero",
}


def text(code: str, **params: Any) -> str:
    """The English fallback for a code, with its parameters filled in."""
    try:
        return MESSAGES[code].format(**params)
    except KeyError:
        # An unknown code must not turn a handled error into a 500. The code
        # itself is still a usable message: the interface translates on it.
        return code


def error(status_code: int, code: str, **params: Any) -> ApiError:
    """Build the HTTP error for a code, English fallback included."""
    return ApiError(status_code, code, text(code, **params), **params)


def detail(code: str, **params: Any) -> dict[str, Any]:
    """The same payload, for places that report rather than raise."""
    return {"code": code, "message": text(code, **params), "params": params}
