# Cargo contract v1

Cargo is part of EMCargo's core shipment data. A future placement plugin consumes
this contract; no 3D planner, placement engine or label printer is included.
Every endpoint requires the same authenticated account as the rest of the app.
There is no direct database integration or public scan bypass.

## Endpoints

| Endpoint | Behaviour |
| --- | --- |
| `GET /api/cargo/v1/contract` | JSON schema, capability names and explicit measurement units. |
| `POST /api/cargo/v1/assess` | Validate and assess `{cargo, lines}` without storing a shipment or physical identity. |
| `GET /api/shipments/{id}/cargo/v1` | Read retained cargo with the authoritative stored revision. Existing history, private-draft and department access rules apply. |
| `GET /api/cargo/templates` | Built-in and active organisation packaging models; any signed-in account can choose them. |
| `POST /api/cargo/templates` | Create an organisation packaging model; library-manager permission required. |
| `PUT /api/cargo/templates/{id}` | Update a model with its current `version`; stale writes return 409. |
| `DELETE /api/cargo/templates/{id}?version=N` | Archive a model; existing shipment snapshots stay intact. |
| `GET /api/cargo/units?q=…&equipment_id=…` | Up to 200 reusable physical-unit masters, with no shipment contents, customer or historic load information. |

Shipment changes use the existing shipment save routes and their normal DG
review policy. `ShipmentIn` carries `cargo` and `expected_cargo_revision`.
A save response includes `cargo_revision`; use it as the next precondition.
The server also increments that revision when underlying goods quantities,
measurements or transport characteristics change. A stateless assessment and a
local export retain the editor's revision; use the retained read endpoint's
revision when writing against a saved shipment.

A changed stored cargo graph requires the matching precondition. SQL conditional
updates prevent two sessions from both overwriting the same revision. Repeating
an identical save reuses the shipment's UUID and physical identities. A late
draft save cannot turn a published shipment back into a private draft.

## Manifest

```json
{
  "schema_version": 1,
  "shipment_id": "297ed01d-f2d0-478f-b567-a6d7192c9f11",
  "revision": 3,
  "units": [
    {
      "id": "29847789-14b1-408a-bd03-d50a264a8ce1",
      "code": "BOX-2984778914B1",
      "kind": "package",
      "category": "box",
      "name": "Small parts",
      "parent_id": null,
      "template_id": "builtin-box",
      "group_id": null,
      "source": "unknown",
      "equipment_id": null,
      "external_reference": null,
      "dimensions_mm": {"length": 400, "width": 300, "height": 200},
      "inner_dimensions_mm": null,
      "loaded_dimensions_mm": null,
      "tare_kg": 0.4,
      "measured_gross_kg": null,
      "max_payload_kg": null,
      "max_gross_kg": null,
      "max_stack_load_kg": null,
      "stackable": null,
      "keep_upright": null,
      "can_rotate": null,
      "reusable": false
    }
  ],
  "allocations": [
    {
      "id": "e6b68311-8f79-49e2-b1aa-b6d377a7ee3e",
      "goods_id": 7,
      "unit_id": "29847789-14b1-408a-bd03-d50a264a8ce1",
      "quantity": 100
    }
  ]
}
```

`goods_id` refers to the stable `cargo_goods_id` on a goods line, with the old
`line_id` as a compatibility fallback only. It is scoped by `shipment_id`, not a
catalogue article ID. A unit can contain multiple goods allocations and other
units simultaneously. Its single `parent_id` is its physical parent. The graph
is acyclic; a transport unit cannot be placed inside a package.

`kind` is `package` or `ctu`. `source` is `own`, `external` or `unknown`.
Own equipment retains a separate `equipment_id`; a container number or
registration remains in `external_reference`, not the internal UUID. `code` is
an internal readable identifier, not an SSCC or an officially issued number.
A group has one physical UUID per member. Copying a shipment creates new UUIDs
and removes bindings to actual reusable equipment.

`legacy_goods_id` is reserved for an imported legacy container line. It preserves
the original tare snapshot without counting that line again as goods. It must
refer to an actual container-role goods line with the same tare. Existing
shipments without a cargo graph retain their original export and calculations;
the additive database migration does not rewrite their contents.

## Assessment and uncertainty

An assessment returns the validated `cargo`, calculated `units`, unallocated
`loose` quantities, coded `issues` and `totals`:

| Total | Meaning |
| --- | --- |
| `goods_kg` | Goods mass, excluding packaging and transport-unit tare. |
| `packaging_kg` | Every package tare once, including nested packaging. |
| `cargo_gross_kg` | Goods plus packaging. |
| `transport_tare_kg` | All cargo transport-unit tare, kept separate. |
| `transport_gross_kg` | Goods, packaging and transport tare. |
| `occupied_volume_m3` | The outer relevant load units and direct/unpacked cargo, without adding their nested contents again. |
| `complete` | Whether cargo mass is known; this is not a fit, safety or DG approval. |

Missing measurements are `null`. Pallet dimensions describe the empty pallet;
its loaded height is never inferred. Rigid closed packs may use known outer
measurements. Bulk goods and long goods can be assigned directly to a CTU or
remain unallocated without creating a package or a vehicle record.

`measured_gross_kg` stays separate from calculated gross. It neither replaces
unknown constituent facts nor gets added to them. Capacity issues identify the
unit; changes require a new DG review under the existing review rules. The
hierarchy itself grants no packaging compatibility, stacking or fit approval.

Quantities use decimal arithmetic and six-place output rounding. Whole-piece
units cannot be fractionally allocated. Configurable limits are
`CARGO_MAX_UNITS` (default 2000), `CARGO_MAX_ALLOCATIONS` (50000) and
`CARGO_MAX_DEPTH` (20). Measurements reject negative, nonfinite and abusively
large input. The existing shipment and DG review byte limits still apply.

## Documents

The structured shipment export includes the complete cargo graph and its
assessment, preserving each original goods line. The document bundle also carries
the same top-level graph; the server rejects disagreement between shipment,
snapshot and document cargo. Semantic DG fingerprints include cargo content,
not revision bookkeeping. Existing no-cargo fingerprints remain compatible.

CMR, AVC, packing lists and delivery notes project outer packages into paper
rows. Their descriptions preserve nested contents and unit codes; gross mass is
counted once per outer package. Loose and directly assigned goods retain their
proportional quantities and mass. On CMR/AVC, original ADR declarations appear
once as descriptive rows without inventing or splitting regulated quantities.

The current specialised CIM, IATA DGD, IMO DGD, ADN transport, AWB, bill-of-lading,
IFTDGN and VGM mappings cannot yet represent newly nested packaging without loss.
They return the document-specific `cargo.document_unsupported` result for those
structures, on validation and export. This does not block unpacked cargo,
structured export or unrelated equipment/marking documents. Existing
single-container restrictions are also enforced: a multi-container graph cannot
be silently written as one container. These limits are explicit, not an implied
promise that every document format has been extended.

## Persistence and privacy

Packaging models and physical-unit masters are separate from shipment contents.
Only opt-in shipment retention creates cargo-use records. Pure assessment and
local export do not save shipments. Reusable master records contain no parent,
contents, loaded measurements or customer data and follow the shared equipment
library's access policy. Prior shipments keep independent frozen snapshots.

Reusable units cannot be published in two active retained shipments at once;
private drafts may propose them. Closing the earlier shipment permits reuse.
Deleting history removes associated use records and unreferenced single-use
identities. Reusable masters remain so physical labels do not unexpectedly gain
a new identity. Equipment linked to a permanent cargo identity must be archived,
rather than deleted and accidentally replaced by SQLite's reused integer ID.

Reusable library identities remain selectable when shipment retention is off.
A new physical identity is registered centrally on its first retained save; a
purely local shipment instead preserves its identity through the saved draft
file or export/import round trip, without centrally retaining its contents.
