# Deliveries and shipment preparation

A shipment records goods, packing, dangerous-goods declarations and exact
quantities between pickup and delivery addresses. Legal consignor and consignee
are recorded separately from the physical locations. New shipments have no
transport mode, document selection, document language or signature. A delivery records the actual journey:
one or more transport legs, their allocations, carrier, times and execution.
Office completion does not assert physical delivery.

## Planning and release

Each leg uses road, rail, inland waterway, sea or air. Several shipments can share
a leg; allocations follow an ordered itinerary. Goods quantities use six decimal
places and discrete item units require whole quantities. Concurrent reservations
are serialized and changes require the current delivery revision.

Complete document inputs while the leg is a draft, then plan it and run its
checks before release.
Ordinary road cargo still needs known mass and capacity checks. Missing modal
coverage requires a qualified recorded review; known prohibitions, missing
mandatory information and required source verification cannot be overridden.
DG approval retains the existing dangerous-goods specialist restriction.

An execution-only account sees assigned allocations on specific legs.
Two receivers of the same goods line have separate scopes, including stops,
events, signatures, proof files and exported dossiers. Department filtering
is additional to assignment checks. Managers can assign several shipments to an
operator or receiver, or invite a verified external email address. Invitations
and grants expire; physical completion shortens remaining access to at most seven
days. Existing accounts can combine the relevant task roles.

## Packing and physical inventory

Select complete outer packing units. The server includes every good and nested
unit in a selected outer unit, and retains the identity of each box or pallet.
A quantity alone cannot stand for an arbitrary fraction of a closed box. An
already consumed box cannot be selected again from the same source shipment.

A leg may select an existing reusable transport unit from the equipment/cargo
library as its shared load unit. The delivery projects each shipment into that
unit, counts its tare once and checks the combined contents against its payload
and gross limits. Its physical reservation applies across deliveries and source
shipments. A planned end date cannot free equipment that is still in use.

A complete physical receipt frees reusable equipment independently of office
completion. Accepting a shortage does not establish that an affected unit is
empty. An operator or planner can explicitly register empty units, with a named
person, actual time and explanation. This does not change received quantities.

## Execution, differences and further transport

Loading and receipts are append-only records with quantities, named people and
actual times. Damage is part of the received quantity; refusal is separate.
Optional signatures and evidence belong to the recorded event and access scope.
A retried request cannot accidentally add a second identical receipt.

A correction references the previous record. It cannot rewrite a closed journey,
undo a disposition or invalidate an already executed subsequent leg. A settled
shortage may reduce a subsequent draft leg to the quantity actually received at
the preceding completed leg. Previous leg inputs, quantities, reviews and issued
files remain unchanged. Forward loading cannot exceed that actual receipt.

Return and redelivery dispositions create linked, unplanned delivery records;
they never invent extra warehouse stock or inferred loading/receipt events. The
original difference stays open until the linked physical movement completes.
Derived goods and quantities are fixed, while transport planning remains editable.
A partial return from a closed ordinary-goods package requires an explicit actual
unpacking record before it can be planned as loose cargo. Original packing is
retained in the source snapshot and is not counted again after that record.
Replacement goods require their own source shipment.

DG declarations follow their verified source goods. At shipment preparation,
each split requires explicit quantities and packaging declarations linked to the
original classification. Confirmation binds the goods, locations, distribution
and declarations; changing them invalidates confirmation. A delivery can take a
complete confirmed distribution. Further partial DG allocations remain blocked
until the source declarations are resolved; quantities are never scaled silently.
Resolve those source facts and packing allocations before reserving the goods.

## Documents and retention

New shipments do not produce transport documents. Older preparation drafts
remain available. Final files are issued from released delivery legs. Consecutive legs
with identical modal cargo scope may share a document when an explicit contract
reference defines that scope. Otherwise each leg has its own document scope.
Each source pickup/delivery pair has separate document inputs and issued scope;
different receivers cannot be combined into one document.
Unsupported document formats need an approved external document where supported.

Issued bytes, input snapshots, regulatory editions, reviewer information and
hashes are retained together. Download and email use those same stored bytes.
New issue supersedes earlier versions for the same scope without deleting them;
changed inputs invalidate current release and document eligibility.

Retention is always enabled. Schema migration 13 preserves all old snapshots,
bundles and frozen document bytes; an obsolete opt-out setting cannot hide or
delete them. The temporary delivery API is retired. Explicit administrative
export and deletion remain available.

Shipment balances show reserved, available, received and returned quantities.
Operational reporting counts final receipts by actual receipt date; transfers
between legs do not multiply the delivery total. Historical DGSA reporting stays
separate. Deleting retained history includes delivery files, events and grants.

## Existing records and portability

Legacy trip assessments remain readable. Explicit conversion starts a delivery
concept with the old consignment references; it never invents physical quantities
or execution history. Delivery archives use `emcargo.delivery` version `2.0` (with legacy `1.0` imports supported).
Import checks local source fingerprints and creates a new concept. Imported
reviews, states, access grants and files never become authoritative approvals.
Onward quantity reductions reset to the source allocation because they require
new local receipt evidence; imported events cannot justify a stock adjustment.
Shipment and cargo export formats remain separate from the delivery archive.

## Multiple addresses

The shipment wizard follows goods, addresses/distribution, dangerous goods when
present, and review. Finalization requires exact distribution totals and complete
physical addresses, countries and responsible parties. Incomplete work remains a
private draft. A closed outer packing unit must stay with one address pair.

A new delivery copies the selected source addresses and available quantities.
Initial stops list pickups before deliveries. Reordering or inserting a transfer
rebuilds each allocation's path between its own pickup and final delivery. Every
leg has its own mode, carrier, checks and loading/receipt quantities. Intermediate
receipts are transfers; only the final receipt counts as delivery to the recipient.

Address overrides require a reason and retain the original, actor and timestamp.
Planning freezes these facts; unplan before changing them. Executed evidence stays
immutable. A document selection must have one source address pair. Separate
receivers cannot be combined accidentally into one CMR or other issued document.
