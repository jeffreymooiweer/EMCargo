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
    "delivery.document_scope": "Select consecutive transport parts with the same modality and goods, and enter the transport contract reference.",
    "delivery.import": "This delivery archive cannot be imported. Use a version 1.0 archive with matching local source shipments.",
    "delivery.legacy_readonly": "Legacy trips are read-only. Convert a trip to a delivery concept to continue planning.",
    'delivery.not_found': 'Delivery or assignment not found.',
    'delivery.permission': 'You do not have permission for this action.',
    'delivery.conflict': 'This delivery changed. Reload before saving.',
    'delivery.quantity': 'Check the loaded, received and refused quantities.',
    'delivery.overallocated': 'These goods are already reserved or delivered.',
    'delivery.source': 'Select an accessible, saved shipment and its goods.',
    'delivery.source_changed': 'The shipment changed. Refresh the draft and review it again.',
    'delivery.source_locked': 'These goods belong to a planned delivery. Reopen its transport parts before editing.',
    'delivery.department': 'A delivery can only contain shipments from one department.',
    'delivery.itinerary': 'Check the connection and order of the transport parts.',
    'delivery.unpack': 'Split or unpack the source cargo before planning a partial unit.',
    'delivery.dg_split': 'A partial DG consignment requires a separate verified declaration.',
    'delivery.frozen': 'Reopen this transport part before changing released or planned goods.',
    'delivery.state': 'Complete the required planning or execution step first.',
    'delivery.blocked': 'A mandatory transport check blocks release.',
    'delivery.review': 'A qualified assessment of this version is required.',
    'delivery.document': 'Check the document, its shipment and its transport part.',
    'delivery.time': 'Use a valid date, time and time zone.',
    'delivery.too_large': 'The record or attachment exceeds the storage limit.',
    'delivery.invite': 'Check the email address and configured mail server. Access has not been sent.',
    'delivery.mail': 'The document bundle could not be sent. Check the mail configuration and try again.',
    "cargo.limit": "The cargo hierarchy exceeds the configured limit.",
    "cargo.parent_missing": "The selected destination no longer exists.",
    "cargo.parent_invalid": "A transport unit cannot be placed in a package.",
    "cargo.identity_duplicate": "A physical unit can only occur once in a shipment.",
    "cargo.cycle": "A unit cannot contain itself or its parent.",
    "cargo.goods_duplicate": "Goods identifiers must be unique.",
    "cargo.goods_missing": "The selected goods no longer exist.",
    "cargo.quantity_missing": "Enter a quantity before distributing these goods.",
    "cargo.whole_items": "Whole items cannot be divided into fractions.",
    "cargo.overallocated": "The allocated quantity exceeds the available goods.",
    "cargo.legacy_invalid": "The original container data must be preserved.",
    "cargo.weight_unknown": "Weight unknown.",
    "cargo.payload_exceeded": "The payload exceeds this unit's capacity.",
    "cargo.gross_exceeded": "The gross weight exceeds this unit's capacity.",
    "cargo.weight_difference": "Measured and calculated gross weight differ.",
    "cargo.template_missing": "This packaging model no longer exists.",
    "cargo.conflict": "This cargo was changed elsewhere. Reopen it before saving.",
    "cargo.equipment_in_use": "This equipment has a permanent cargo identity. Archive it instead of deleting it.",
    "cargo.identity_conflict": "This unit identifier already belongs to another physical unit.",
    "cargo.unit_in_use": "This reusable unit is assigned to another active shipment.",
    "cargo.documents_incomplete": "Complete the cargo weights before creating this document.",
    "cargo.document_unsupported": "The document {document} cannot represent this cargo structure.",
    "cargo.snapshot_mismatch": "Shipment cargo and document cargo must match.",

    "equipment.inspection_name": "Give this inspection a name.",
    "equipment.inspection_dates": "The next inspection cannot precede the performed date.",
    "equipment.inspection_date_required": "Enter the performed date for this result.",
    "equipment.inspection_ids": "Every inspection must have a unique identifier.",
    "equipment.document_container": "This document describes one container. Include one container and assign every goods line to it; use a separate shipment for other containers.",
    "equipment.gross_exceeded": "The gross weight exceeds the container gross weight limit.",
    "equipment.payload_exceeded": "The goods weight exceeds the container payload limit.",
    "equipment.container_weight_missing": "Enter the tare and the weight of every goods line in the container.",
    "equipment.container_missing": "The selected container is missing or excluded. Select again or carry the goods separately.",
    "equipment.container_invalid": "Select one container as a carrying unit, without a parent container.",
    "equipment.single_asset": "An identified asset can occur only once per shipment, with quantity 1.",
    "equipment.snapshot_invalid": "The saved equipment data is invalid. Select the equipment again.",
    "equipment.not_found": "This equipment item no longer exists.",
    "equipment.row_invalid": "Row {row}: {reason}",
    "equipment.changed": "This equipment item changed while you were editing. Reload it before saving.",
    "equipment.invalid": "Check the equipment data: {reason}",
    "equipment.move_required": "Use Confirm transfer to record a change of location.",
    "equipment.identifier_used": "Equipment with identifier {identifier} already exists.",
    "equipment.identifier_conflict": "This equipment identifier is already in use. Reload the library.",
    "equipment.name_required": "Enter an equipment name.",
    "equipment.location_required": "Enter the confirmed destination.",
    "equipment.configuration_names": "Give each transport configuration a distinct name.",
    "equipment.gross_limit": "Maximum gross weight must exceed the empty container weight.",
    "equipment.inner_dimensions": "Internal dimensions cannot exceed external dimensions.",
    "equipment.file_size": "Choose a non-empty PDF or photo of at most 10 MB.",
    "equipment.file_limit": "An equipment item can hold at most 12 files.",
    "equipment.file_invalid": "Choose an unlocked PDF with 1 to 200 pages or a static JPEG, PNG or WebP photo.",
    "equipment.file_missing": "This equipment file no longer exists.",
    "imdg.source_verification_required": "Complete the IMDG substance assessment and record the source and verification before release.",
    "templates.unknown": "This document template is not registered.",
    "templates.size": "Choose a non-empty PDF of at most 30 MB.",
    "templates.incompatible": "This PDF does not match the supported edition, pages and field mapping. The current template has been preserved.",
    "templates.source_required": "Record the source and your basis for using this template locally.",
    "templates.missing": "Import the supported template under Administration, Document templates.",
    "intake.unsupported": "Choose a PDF, JPEG or PNG document.",
    "intake.file_large": "Choose a non-empty document of at most 20 MB.",
    "intake.busy": "Other documents are being read. Try again shortly.",
    "intake.timeout": "Reading took too long. Use a smaller document or clearer scan and retry.",
    "intake.invalid": "This document could not be read. Export a new PDF or choose a clear image.",
    "intake.image_large": "This image or page is too large to process. Reduce its resolution and retry.",
    "intake.encrypted": "This PDF is password protected. Upload an unlocked copy.",
    "intake.pages": "Choose a document with 1 to 10 pages. No pages have been imported.",
    "intake.text_large": "The document contains too much text. Split it into smaller documents; no rows have been imported.",
    "intake.no_text": "No readable text was found. Choose a clearer photo or a PDF with selectable text.",
    "intake.ocr_missing": "Local text recognition is not installed. Ask the administrator to install Tesseract and its language data.",
    "intake.ocr_failed": "Text recognition failed. Try a sharper, upright image.",
    "intake.model_failed": "The local model could not prepare a proposal. The source and your current shipment have been preserved.",
    "work.owner_invalid": "Choose an active colleague who can access this shipment.",
    "work.not_ready": "Finish the documents and required DG release before completing this office task.",
    "work.changed": "This task has changed. Refresh the list before trying again.",
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
