# Roadmap

Current direction, reviewed on 17 September 2026 against v2.15.0 and the product
owner's decisions. Completed work is in [CHANGELOG.md](CHANGELOG.md). Historical
research remains in [Roadmap research](docs/roadmap-research.md),
[The database](docs/database-plan.md) and the usability plans; older release
specifications there do not describe the current product.

## v2.11.0: daily work and document intake

The [implementation plan](docs/workflow-document-intake-plan.md) defines scope,
dependencies, acceptance criteria and delivery gates for v2.11.0.

| Priority | Capability | Outcome |
|---|---|---|
| 1 | Actionable overview | Incomplete shipments, specialist work, loading dates, responsible people and next actions |
| 2 | Local packing-list intake | Read PDFs/photos, inspect the source, correct a proposal and continue in the assistant |

## Available today

| Area | Current state |
|---|---|
| Transport modes | Road, rail, sea and inland waterway selectable; air and multimodal in development |
| Shipment preparation | Manual entry, pasted lists, XLSX/CSV/TXT, weight/volume calculations and document preparation |
| Local assistant | Guided interview requiring the installed local model; unresolved facts remain questions |
| Documents | Official CMR, AVC, CIM and IATA forms plus the existing generated transport, package and equipment documents |
| Dangerous goods | Regulation-specific checks and specialist release by default; known gaps in [DG coverage](docs/dg-coverage.md) |
| Organisation work | Optional saved shipments/private drafts, templates, departments, address book, own goods, trips and DGSA reports |
| Trips | Combined-load assembly and assessment; no spatial load or route optimisation |
| Cargo | Mixed nested packaging, direct unpackaged loads, unique physical IDs, reusable units, packaging library and versioned plugin contract |
| Library | Own goods; vehicles, machines and containers with frozen shipment selections, local files and confirmed location history; sourced density references |
| Density catalogue | 23,957 rows; measurements, manufacturer data, estimates and unverified legacy values distinguished |
| Accounts | Mandatory sign-in, roles, personal settings, avatars, two-factor authentication and audit metadata |
| Deployment | Docker/GHCR, Unraid, native bundles, Kubernetes and updates where supported |
| Interface | Dutch, English, German and French; light/dark and responsive layouts |
| Data exchange | Versioned shipment JSON, IFTDGN D.16A export and eFTI element mapping |

## Next: the organisation's actual assortment

Extend Own goods only with articles the organisation or factory actually trades:
its codes, manufacturer/EAN identifiers, sourced product weights, package variants,
dimensions, stackability and source dates. Shared density references do not populate
that assortment automatically. The equipment library also starts empty.

## Next: build on existing data exchange

- [Structured export](docs/shipment-export.md): shipment data and findings with
  regulatory editions, as versioned JSON.
- [IFTDGN](docs/iftdgn.md): UN/EDIFACT dangerous goods notifications, parsed back and
  checked before download.
- [eFTI mapping](docs/efti-mapping.md): field mappings and explicit coverage gaps.

Next steps need a real counterpart's profile, split postal addresses, identifiers,
code lists, transport, acknowledgements, idempotency and retries. Complete eCMR
exchange also requires party-specific signing and document revisions. EMCargo does
not claim a certified eFTI platform or an operational eCMR network connection.

## Companion modules and ecosystem

Specialist modules remain optional projects using the core API and shipment data.
The [cargo v1 contract](docs/cargo-contract.md) now supplies hierarchy, quantities,
measurements, constraints, identities and revisions. Core contains no spatial planner.

| Module | Planned scope |
|---|---|
| Visual load planning | 2D/3D placement, dimensions, stacking, weight distribution and spatial segregation, accessible from Trips |
| Route planning | Mode-specific journeys and restrictions, including dangerous goods constraints |
| Container fleet extensions | Telemetry, inspection workflows and per-container document bundles; basic inventory, condition, inspection dates and confirmed custody history are available in the equipment library |
| Vessel design | Separate sea-going and inland-vessel tooling |
| Specialist military transport | Separate private module; no operational data or military forms in the public civilian core |
| Plugins and community | Admin-controlled installation, documented integration contracts and a community catalogue |

## Transport modes still in development

Sea is selectable again in v2.12.2 after checking its existing document flow and
specialist release controls. Air needs authoritative quantity limits and the remaining
[DG checks](docs/dg-coverage.md); investigate IATA's own validation integration.
Multimodal follows its validated component modes. Unlock only after end-to-end
verification of the relevant document flow.

## Continuing quality work

- Keep the interface calm, reduce repeated entry and measure important user journeys.
- Maintain regulatory editions, density conditions, gap reporting and export checks.
  Completed office work and generated documents never substitute for DG release.
- Preserve optional retention, private drafts and department boundaries.
- Keep upgrades, rollback and native/container operation reliable.
- Retain the current repository licence; changes require their own decision.

## Outside the accepted scope

- No driver application or process requiring carriers to adopt EMCargo.
- No prefilled organisation assortment or operational equipment in public images.
- No anonymous application access. Optional UN-card QR links and direct card
  downloads require sign-in and retain the requested scan URL through login.
