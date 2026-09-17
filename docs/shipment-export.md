# The structured shipment export

*A shipment as data rather than paper: what was filled in, what is carried, and
what EMCargo worked out. Offered from the export step as **Structured
shipment export (JSON)**, and produced by the same code path as every other
document, so what the button hands out is what the bundle contains.*

## Why it exists

The EU [eFTI Regulation](https://transport.ec.europa.eu/transport-themes/logistics-and-multimodal-transport/efti-regulation_en)
applies in full from **9 July 2027**: from then, authorities must accept freight
information electronically through certified eFTI platforms, and the eFTI data
set is built on the UN/CEFACT Multi-Modal Transport reference data model.

EMCargo is not going to become a certified platform. That is a certification
regime for platform providers; this is a documentation tool. What it can be is
**trivially connectable to one** — and that starts with a shipment being able to
leave the application as structured data at all. Everything else (a mapping onto
MMT-RDM, an eCMR pilot, a platform connector) builds on this file existing.

## What is in it

The format identifier is now `emcargo.shipment`, with format version `2.1`.
Integrations must accept this new identifier before consuming new exports.

```json
{
  "format": "emcargo.shipment",
  "format_version": "2.1",
  "generated_at": "2026-08-23T15:58:51+00:00",
  "generator": { "application": "EMCargo", "version": "1.161.0" },
  "language": "nl",
  "modality": "road",
  "regulations": ["ADR"],
  "consignment": { "consignor_name": "…", "reference": "…" },
  "goods": [ { "description": "…", "quantity": 10 } ],
  "dangerous_goods": [ { "line_id": "1", "products": [ … ] } ],
  "compliance": { "sources": …, "adr_points": …, "package_marking": … }
}
```

| Key | What it holds |
|---|---|
| `format`, `format_version` | The format's own version, not the application's — see below |
| `generated_at` | UTC, to the second |
| `generator` | Which application and which release produced it |
| `language` | The language the documents were drawn up in |
| `modality` | The transport mode the wizard was in. Recorded, never derived from |
| `regulations` | The regimes the consignment travels under, as the compliance answer received them |
| `consignment` | The document fields as filled in |
| `goods` | The goods lines, with what the calculator worked out per line |
| `dangerous_goods` | The declared dangerous goods per position, after Table A was applied |
| `compliance` | **The derived findings** — the whole answer the compliance panel received |

## Three rules the format follows

**The version means something.** `format_version` changes when a reader would
break. A field added is not a break; a field renamed, removed, or given a
different meaning is. A reader that checks the major version and ignores keys it
does not recognise will keep working across minor versions.

**Nothing is invented.** A field the user left empty is *absent*, not an empty
string — the wizard writes an empty string into every field it renders, so
exporting them would fill the file with keys that mean "untouched" while looking
like answers. A zero, a `false` and an empty list are kept: somebody chose those.
A check that did not run is absent rather than reported as passing.

**It carries no user and no installation.** The file describes a consignment,
not who typed it. That keeps it the same file whoever produces it, and keeps
[Privacy](privacy.md)'s promise that a finished job leaves nothing behind.

## Why the derived findings are in it

A reader that receives only the declaration has to compute its own regulatory
assessment, and that is where two systems begin to disagree about one
consignment. So `compliance` carries the whole answer — the 1.1.3.6 points, the
mixed-loading findings, the placarding, the package marking of chapter 5.2, the
segregation — **including the editions each was computed against**, which the
answer already names in `sources` and `regulatory_manifest`.

That last part is what makes the file honest over time. A shipment exported
under ADR 2025 and read after ADR 2027 lands can be told apart from the same
shipment re-derived under the new edition, because the file says which book
answered.

## What this is *not*

- **Not an eFTI message.** The eFTI data set is defined by the implementing
  acts and built on MMT-RDM. This is EMCargo's own structure and says so in
  its first key.
- **Not an eCMR.** An eCMR is a consignment note under the e-CMR Protocol, with
  a signature regime this file has nothing to say about.
- **Not an eFTI view of itself, yet.** Naming a field as though it were the
  standard's while it carries something subtly different is the failure that
  makes an integration silently wrong. The mapping onto the eFTI common data
  set is a separate page, [The eFTI mapping](efti-mapping.md), written against
  the Annex of Delegated Regulation (EU) 2024/2024 element by element; the
  file itself keeps its own keys until the gaps that page names are closed.

## What has to happen before it can be mapped

Done in v1.185.0 as far as reading goes — see [The eFTI mapping](efti-mapping.md)
for what was read and what came out. What stays open, recorded here so the next
person does not start from nothing:

1. ~~**Read the MMT-RDM.**~~ Read as the eFTI common data set, the profile of it
   the regulation adopted, from the Official Journal.
2. **Decide what a "consignment" is.** EMCargo's wizard produces one
   consignment per run; the data set distinguishes the consignment, its items,
   the used transport equipment and the transport movement, and the mapping
   places one goods line as one consignment item and one container as one piece
   of used equipment.
3. **Settle the party model.** The application holds consignor, consignee,
   carrier and notify party as free text; the data set holds an address in nine
   named parts and identifies parties by scheme and code. This is the one
   structural gap the mapping measures.
4. **The signature question.** The per-party signature flow (consignor,
   carrier, consignee) is the second half of an eCMR, and qualified electronic
   signatures are a legal-weight question, not a technical one.

## The EDI sibling

Since v1.189.0 the same parts are also written as the UN/EDIFACT dangerous goods
notification, IFTDGN, offered beside this export for a shipment with dangerous goods —
see [The IFTDGN notification](iftdgn.md). The JSON stays the complete record with the
derived findings; the IFTDGN is what a port community system reads.

## Reading it back

There is no import of this file. It is a one-way export, and a reader that wants to
reconstruct a shipment from it is doing something this application does not
promise. The shipment history (v1.173.0) reopens a kept shipment from the wizard's
own saved state, not from this file; the file is what the history keeps *beside*
that state as the documented record, and what the shipments page hands out as
**Structured export (JSON)**.

## Optional cargo hierarchy (format 2.1)

The additive `cargo` and `cargo_assessment` fields preserve nested physical units,
partial goods allocations, stable identifiers and explicit unknown measurements.
The original `goods` lines remain available. See [Cargo contract v1](cargo-contract.md)
for quantities, revisions, document mappings and the independent plugin interface.
