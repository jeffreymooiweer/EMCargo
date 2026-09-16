# Equipment library

Since v2.13.0, Library → Equipment holds vehicles, machines, containers and other
reusable transport items. It starts empty. Existing records are preserved as Other;
classify them when their actual purpose is known.

## Maintaining an asset

Managers and administrators can add/edit records, archive/restore, import/export,
attach files and confirm transfers. Signed-in users can read the active library and
select equipment in a shipment. The existing write permissions are unchanged.

Use an asset number to distinguish machines with the same name. Asset numbers and
container numbers are unique, trimmed and case-normalised. Registration and serial
numbers are searchable. Record **transport** dimensions in centimetres and weight in
kilograms, including attached accessories. Vehicle/machine records can hold named
alternative transport configurations; each carries its own dimensions and weight.

Containers carry outer and inner dimensions, empty tare, payload/gross limits, type
and next inspection date. These are operator-supplied facts, not manufacturer
certifications, inspection results or a spatial load plan.

Availability, condition and planning reference/date are maintained explicitly.
The current location changes only through **Confirm transfer** after creation.
The event records the old/new location, user, timestamp, reference and notes.
Creating, saving, exporting or downloading a shipment records no transfer. A stale
edit or movement returns a conflict instead of overwriting a more recent handover.
Reload the item and review the current facts before saving again.

Each item accepts up to 12 photos/PDFs, each up to 10 MiB. Static JPEG, PNG and WebP
photos are normalised, resized and stored as JPEG; unencrypted PDFs are limited to
200 pages. Files are authenticated and stored in SQLite with the equipment. Existing
database backups therefore include them. Spreadsheet exports carry metadata, not
file bytes or movement history; use the database backup for a complete copy.

## Selecting equipment in a shipment

Use **Choose equipment** or select an equipment search result. A selection copies
its identity, dimensions, weight, accessories, instructions and configurations into
the shipment. Select a configuration or adjust that shipment's measurements as
needed. Saved shipments keep this copy even after the library item is changed,
archived or removed. This guarantee applies to explicit selections made with this
version; older free-text-only shipments do not contain historical master data.

A physical asset with an asset/container/registration/serial number can appear only
once, with quantity one. Create separate records for separately identified machines.
Renaming a goods line manually detaches its equipment selection and copied physical
fields. Choose equipment again to make a new explicit selection.

## Containers and contents

Choose **Empty container as cargo** to transport the container itself, or **Container
carrying goods** to allocate other goods lines to it. On each goods line, choose its
container. Multiple carrying containers can be represented; nested carrying
containers are unsupported. A container removed, excluded or changed back to cargo
leaves an explicit allocation error until its goods are reassigned or carried loose.

The container row contributes tare and outer transport volume. Contents contribute
their own mass, but no additional occupied transport volume; their package volume is
retained separately. The summary shows tare, cargo and total. Incomplete weights and
exceeded payload/gross limits are checked again before exporting documents. These
checks do not determine whether the goods physically fit or are safely secured.

Goods descriptions in exports include their assigned container reference. Shipment
JSON retains the complete selection and allocation. Existing VGM, IMO DGD, B/L
instructions and IFTDGN flows describe one container; use a separate shipment per
carrying container for these documents. CMR and general shipment lists can include
multiple containers. Per-container document bundles remain a future extension.

VGM cargo-mass suggestions exclude tare; the empty weight is suggested separately.
Verified mass remains an explicit document entry. Correcting the shipment's total
weight scales goods weights, leaving the carrying containers' tare unchanged.

## Import, export and storage

The first eight spreadsheet columns remain unchanged. Additional columns hold type,
identifiers, technical/management fields, configuration JSON and language labels.
Legacy templates remain accepted. Imports match an asset/container number first;
ambiguous names or a name matching an identified asset require its identifier.
Import cannot move an existing item to another location; confirm a transfer instead.

Schema migration 10 adds typed equipment fields, unique identifiers, a version
counter, movement events and file tables. It is repeatable and keeps old records.
No seed contains operational equipment. Existing API delete remains compatible;
the interface archives by default to preserve records and history.
