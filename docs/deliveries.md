# Deliveries and shipment preparation

A shipment records the goods, packing and parties. Its transport mode is optional
and expresses a preparation preference. A delivery records the actual journey:
one or more transport legs, their allocations, carrier, times and execution.
Office completion does not assert physical delivery.

## Planning and release

Each leg uses road, rail, inland waterway, sea or air. Several shipments can share
a leg; allocations follow an ordered itinerary. Goods quantities use six decimal
places and discrete item units require whole quantities. Concurrent reservations
are serialized and changes require the current delivery revision.

Plan a leg, complete its document inputs and run its checks before release.
Ordinary road cargo still needs known mass and capacity checks. Missing modal
coverage requires a qualified recorded review; known prohibitions, missing
mandatory information and required source verification cannot be overridden.
DG approval retains the existing dangerous-goods specialist restriction.

An execution-only account sees assigned legs and shipments. Department filtering
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

DG declarations follow their verified source lines. Complete DG lines can be
selected separately from other goods; partial DG lines or ambiguous mappings
remain blocked rather than proportioning declaration quantities automatically.
Resolve those source facts and packing allocations before reserving the goods.

## Documents and retention

Shipment documents are preparation drafts, including PDF, spreadsheet and EDI
outputs. Final files are issued from released delivery legs. Consecutive legs
with identical modal cargo scope may share a document when an explicit contract
reference defines that scope. Otherwise each leg has its own document scope.
Unsupported document formats need an approved external document where supported.

Issued bytes, input snapshots, regulatory editions, reviewer information and
hashes are retained together. Download and email use those same stored bytes.
New issue supersedes earlier versions for the same scope without deleting them;
changed inputs invalidate current release and document eligibility.

With shipment retention disabled, the preparation wizard offers a temporary
single-leg delivery check and final document archive. Its qualified review token
is bound to the actor, inputs and editions and expires after thirty minutes.
This path does not retain a shipment, delivery, event or review record. Retained
execution and external invitations require the retention option.

Shipment balances show reserved, available, received and returned quantities.
Operational reporting counts final receipts by actual receipt date; transfers
between legs do not multiply the delivery total. Historical DGSA reporting stays
separate. Deleting retained history includes delivery files, events and grants.

## Existing records and portability

Legacy trip assessments remain readable. Explicit conversion starts a delivery
concept with the old consignment references; it never invents physical quantities
or execution history. Delivery archives use `emcargo.delivery` version `1.0`.
Import checks local source fingerprints and creates a new concept. Imported
reviews, states, access grants and files never become authoritative approvals.
Onward quantity reductions reset to the source allocation because they require
new local receipt evidence; imported events cannot justify a stock adjustment.
Shipment and cargo export formats remain separate from the delivery archive.
