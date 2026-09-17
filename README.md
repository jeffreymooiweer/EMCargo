<div align="center">

# EMCargo

Developed and maintained by **Jeffrey Mooiweer**.

**Turn a list of packages into finished transport documents.**

Paste your load, and EMCargo works out the weights and volumes, fills in the official
CMR, CIM and AVC forms and sea/inland documents, and checks your dangerous goods before you print.

[![Latest release](https://img.shields.io/github/v/release/jeffreymooiweer/emcargo?logo=github&label=release&color=2ea44f)](https://github.com/jeffreymooiweer/emcargo/releases/latest)
[![Build](https://img.shields.io/github/actions/workflow/status/jeffreymooiweer/emcargo/ci.yml?branch=main&logo=githubactions&logoColor=white&label=build)](https://github.com/jeffreymooiweer/emcargo/actions/workflows/ci.yml)
[![Status](https://img.shields.io/badge/status-under%20development-orange)](ROADMAP.md)
[![Licence](https://img.shields.io/badge/licence-Apache--2.0%20%2B%20Commons%20Clause-blue)](LICENSE)

[![Backend](https://img.shields.io/badge/backend-FastAPI%20%C2%B7%20Python%203.12-009688?logo=fastapi&logoColor=white)](docs/development.md)
[![Frontend](https://img.shields.io/badge/frontend-React%2019%20%C2%B7%20TypeScript-61DAFB?logo=react&logoColor=black)](docs/development.md)
[![Unraid](https://img.shields.io/badge/Unraid-ready-F15A2C?logo=unraid&logoColor=white)](docs/getting-started.md#unraid)
[![Interface](https://img.shields.io/badge/interface-NL%20%C2%B7%20EN%20%C2%B7%20DE%20%C2%B7%20FR-lightgrey)](#)
[![Self-hosted](https://img.shields.io/badge/self--hosted-your%20data%20stays%20yours-6f42c1)](docs/privacy.md)

</div>

---

> [!WARNING]
> **EMCargo is under active development.** Every document it produces is a **draft**.
> Check it, complete it and have it signed by a qualified person before you use it.
> See the [terms of use (Dutch draft)](TERMS.nl.md).

## DG review and roles

Dangerous goods shipments require release by a **DG Specialist** before final
exports by default. **Super Users** manage daily operations without gaining
administrator system controls. DGSA reports are restricted to specialists and
administrators unless the admin explicitly enables Super User report access.
See [roles, release and storage](docs/dg-review.md) for the workflow and settings.

## Cargo and packaging

Combine different goods in a box and nest packages inside larger boxes or pallets.
Keep bulk material, steel, pipes and machinery unpackaged or load them directly
into an own, external or unspecified transport unit. Physical units have stable
IDs; templates and saved shipments retain their own specifications. The
[versioned cargo contract](docs/cargo-contract.md) supports a future separate
planner module.

## EMCargo interface

EMCargo 2.2 uses a navy and cobalt workspace, original transport photography,
a consistent icon set and a redesigned login. Settings are grouped by personal,
organisation and system tasks, with a dedicated Updates page. Dangerous-goods
entry emphasizes unanswered questions, while the final wizard page groups
repeated findings and keeps document actions clear. Mobile layouts and motion
preferences are supported. See the [design review](docs/design/review-2.2.0.md)
and [in-app update setup](docs/in-app-updates.md).

Overview, Shipments, Trips and Articles have permanent entries in organisation
navigation. The overview lists work needing attention, pending specialist reviews,
today's stated loading dates and ready documents. Assign kept shipments to an
authorised colleague and record office completion. Private drafts stay private;
specialist work remains available when optional shipment history is off. See the
[implementation plan and remaining scope](docs/workflow-document-intake-plan.md).
When shipment storage is disabled, its pages explain how an administrator can
enable it. Users can set their profile photo under Settings /
My details; administrators manage accounts in a searchable directory with a
separate edit dialog.

Dangerous-goods assessment remains mandatory within the goods stage. The complete source now uses EMCargo identifiers, including storage and native
installation names. Existing installations require the steps in
[Identity migration](docs/identity-migration.md) before upgrading. The original
licence remains in LICENSE.

Images for this repository are published to `ghcr.io/jeffreymooiweer/emcargo`.
Use `docker compose up --build -d` to build locally before a release is available.

## What is EMCargo?

Preparing freight paperwork is repetitive. The same addresses, the same reference
numbers, the same weights — typed again into every form, each with its own layout and
its own rules. Get a box number wrong on a dangerous goods declaration and the shipment
stops at the gate.

EMCargo does that part for you. You enter your shipment once. It recognises what you
are shipping, calculates the weights and volumes, and fills in the paperwork for the
transport mode you picked. **Road, rail, sea and inland waterway can be selected
today**. Air and multimodal are shown as in development. Sea offers B/L shipping
instructions, VGM, the IMO dangerous goods declaration and container packing
documents, with the existing validation and specialist release workflow.

It runs on your own machine or server and always requires an account.
An administrator can enable saved shipments and private
drafts. Optional online lookups and local assistant features are described in
[Privacy](docs/privacy.md).

## What it does

**Understands your load.** Paste a list, or import an Excel or CSV file. EMCargo
recognises materials and dimensions in Dutch, English, German and French — `Steel angle 80x80x8x6000` —
and works out the weight from a built-in database of **1,093 goods**, from cement and
timber to grain, chemicals and white goods. Anything it cannot work out, you can correct
by hand.

**Fills in the real forms.** The CMR, CIM, AVC and IATA declarations are the genuine
official documents, filled in — not lookalikes drawn from scratch. Everything else is
produced as a clean PDF.

**Asks each question once.** Sender, consignee, route and references are entered a
single time and reused across every form you selected. After that you only see the
fields a given form still needs.

**Knows its way around dangerous goods.** Type a UN number and EMCargo works out the
proper shipping name, class and division, subsidiary risks, packing group, transport
category, tunnel code, EmS emergency schedules and the air freight rules. It warns you
about incompatible loads, calculates the ADR 1,000-point exemption and the IATA Q value,
and refuses to export a declaration that is not complete.

**Hands you the paperwork for your own file.** Alongside the transport documents, a
shipment with dangerous goods can download the UN reference cards for exactly the
substances it declared.

**Finds addresses and terminals for you.** Address autocomplete plus 4,500+ airports,
17,500+ ports and 750+ European railway stations, filtered to the transport mode you
chose.

**Speaks Dutch, English, German and French**, in light or dark mode. The interface, the field labels, the dangerous goods guidance and the generated documents all follow the language you pick.

**Remembers what does not change.** Your language, your consignor details, your emergency
number, your signature — set once, filled in on every shipment, and stored with your
account rather than in one browser. Administrators get their own section: what new users
start with, and whether this installation is allowed to reach the internet at all.

## Try it in two minutes

```bash
git clone https://github.com/jeffreymooiweer/emcargo.git
cd emcargo
cp .env.example .env          # set ADMIN_PASSWORD; the rest has defaults
docker compose up -d --build
```

Open <http://localhost:8080> and log in with the admin account from your `.env`.

The full application always requires sign-in. UN cards opened from document
QR links remain accessible without an account when an administrator enables
that feature. The former open application and `EMCARGO_MODE` are retired.

Running Unraid, or want the full set of options? See **[Getting started](docs/getting-started.md)**.

## Documentation

| Guide | What's in it |
|---|---|
| **[Getting started](docs/getting-started.md)** | Install with Docker Compose or on Unraid, create the first admin account |
| **[User guide](docs/user-guide.md)** | A walk through the app, from picking a transport mode to downloading your documents |
| **[Documents](docs/documents.md)** | Every document EMCargo produces, and which ones are official forms |
| **[Dangerous goods](docs/dangerous-goods.md)** | What EMCargo fills in automatically, and which checks it runs |
| **[DG coverage](docs/dg-coverage.md)** | Per mode: what is checked, what is not, and which gaps matter most |
| **[Document fields audit](docs/document-fields-audit.md)** | Chapter 5.4.1 provision by provision: which fields exist, which are guidance only, which are absent and why |
| **[Shipment export](docs/shipment-export.md)** | The whole shipment as versioned JSON, findings included — the step towards eCMR and eFTI |
| **[Configuration](docs/configuration.md)** | Environment variables and settings |
| **[Data sources](docs/data-sources.md)** | Where the goods, location and regulatory data comes from |
| **[Privacy](docs/privacy.md)** | What is stored, and what is deliberately not |
| **[Development](docs/development.md)** | Running from source, tests, versioning, releases |

Also: **[Changelog](CHANGELOG.md)** · **[Roadmap](ROADMAP.md)** · **[Terms of use (Dutch draft)](TERMS.nl.md)**

## Found something wrong?

EMCargo is only worth as much as its data, and a wrong density or a misplaced box on a
form is best spotted by someone actually shipping. Those reports are the most valuable
ones this project gets — please
[open an issue](https://github.com/jeffreymooiweer/emcargo/issues/new/choose).

It is a personal project, so code contributions work a little differently: ask first, in
an issue. [CONTRIBUTING.md](CONTRIBUTING.md) explains why and what a useful report looks
like. Security problems go through
[private reporting](SECURITY.md) rather than a public issue.

## The AI assistant (optional)

The wizard can be driven in natural language: open the assistant with the AI
mark in the wizard header, describe the shipment ("1000 jerricans of 25 l of
petrol"), confirm what the app recognised, and answer only the questions the
app itself has open — one per screen, phrased in plain language, with the
formal field and its article references behind an info mark, a previous
button that really goes back, and the same address and location suggestions
the wizard's own fields have. What the sentence already said is never asked
again: the count, the contents per package and the totals compute by
themselves.

The assistant also reads packing lists from PDF, JPEG and PNG (up to 20 MB,
10 pages). Text extraction and Tesseract OCR run locally. Inspect the source page,
correct recognised text and review editable goods and shipment facts before
accepting them. Existing fields are preserved until explicitly selected for
replacement. Missing quantities remain open; a stated weight requires a choice
between per item and total. Accepted source excerpts travel with the draft, while
original uploads and page previews are temporary. Always compare the proposal
with the complete source: OCR and model extraction can miss or misread facts.

Docker includes OCR for Dutch, English, German and French. Native installations
need [Tesseract and its language data](docs/installation-native.md#document-ocr).

**The assistant requires a local language model.** An administrator installs
the official Qwen3-1.7B (Apache-2.0) in *Settings*. Its llama.cpp runtime and
weights are downloaded once into `/data/assistant`, verified against this
repository's SHA-256 pins. Without this installation the assistant stays
unavailable, including through its API. The ordinary wizard remains available
for manual entry.

The managed runtime supports Linux x86-64/ARM64 and Windows x86-64. Unsupported
hosts cannot install the assistant. Empty or truncated model files do not enable
it. If the model is removed during an interview, the assistant preserves the
typed answer and pauses until installation is restored and checked again.

The model reads free prose; the application owns the questions and validation.
Exact readers handle simple counts, dimensions and labelled facts without a
model round trip. Unclear input stays open, and model-only choice interpretations
require confirmation. The model never decides regulatory content.

Measured on a standard 4-vCPU runner with the exact pinned runtime (the
`measure-assistant-latency` workflow, so the figures can be reproduced):
model loaded in 2 s, a free-prose sentence split into goods lines in 5.9 s, a
paraphrased answer mapped onto an option in 2.1 s, ~2.4 GB RSS while running,
~1.9 GB disk. These are earlier runtime measurements, not a response-time
guarantee for every shipment or server.

## Good to know

EMCargo is a **civilian** tool. It prepares paperwork; it does not give legal,
customs or safety advice, and it does not replace a dangerous goods safety adviser
(DGSA). The current edition of ADR, RID, ADN, the IMDG Code and the IATA DGR is always
the authority — not this app.

Carrier fields, operational fields and signatures are never filled in for you. Your
signature is only added if you draw or upload one yourself.

## Licence

EMCargo is **source-available software** under Apache License 2.0 with the
Commons Clause — see [LICENSE](LICENSE). Internal use and self-hosting are
permitted subject to those terms. The restriction concerns “Sell” as defined
in the Commons Clause, including relevant hosting and services; consult the
actual text before offering a commercial service.

Third-party software and data retain their own terms; see
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). Official form PDFs and
regulatory model PDFs are supplied locally through Administration → Document
templates. Missing forms are reported explicitly and are not substituted with
an unofficial rendition. The current supported editions and compatibility
fingerprints are in `backend/app/config/document_templates.json`.

The [license history](docs/licensing/license-history.md) records the earlier
MIT revisions. Current restrictions do not retrospectively cancel valid rights
in earlier copies. Fork branding follows [TRADEMARKS.md](TRADEMARKS.md).

Application images and native releases are published after technical validation.
The [rights register](docs/licensing/rights-register.md) and package reports
record outstanding questions as advisory information. Separate card-set and
regulatory-volume publication retains its existing review requirements.
