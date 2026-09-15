# Contributing to EMCargo

Thank you for taking the time. Before you invest any of it in code, one thing up front.

## What this project is

EMCargo is a personal project, built and maintained by one person alongside other
work. It is under active development and its internals move around a lot.

**Reports, corrections and ideas are very welcome.** Unsolicited pull requests are not —
not because they are unwanted in principle, but because a patch against a moving codebase
usually costs more to review and rebase than it saves, and it is unfair to let someone
write code that then sits unmerged.

So:

| You have | Do this |
|---|---|
| A bug, a wrong number, a form that comes out wrong | [Open an issue](https://github.com/jeffreymooiweer/emcargo/issues/new/choose) |
| An idea for a feature | Open an issue and describe the situation you are in |
| A security problem | **Not** an issue — see [SECURITY.md](SECURITY.md) |
| Code you would like to contribute | Open an issue first and ask. If it fits, we agree on the shape before you write it |

A pull request that arrives without a prior issue may be closed without being merged.
That is not a judgement on the code.

## The most useful thing you can report

EMCargo's value is in its data being right. A wrong density, a mislabelled segregation
code, a form field that lands in the wrong box — these are the reports that matter most,
and they are the ones a user is best placed to spot.

When you report one, the single most helpful thing you can include is **the source**.
"UN 1263 should be packing group II" is hard to act on; "ADR 2025 Table A lists UN 1263
with packing groups I, II and III — see 3.2.1" can be checked and fixed the same day.

### Weights and materials

Include the exact input line you pasted. The wizard reads `description | quantity | unit`
with the dimensions inside the description:

```
Stalen hoekprofiel 80x80x8x6000 | 8 | stuks
```

Tell us what weight it produced and what it should have been.

### Documents

Say which document, which box or field, and what should have been in it. A screenshot or
the exported PDF helps enormously. Please **redact real addresses, references and
consignee details** first — see below.

### Dangerous goods

Give the UN number, the column (class, packing group, EmS, 16a, 16b …), what EMCargo
showed and what the source says. Name the source and the edition: ADR 2025, IMDG
Amendment 42-24, the EmS Guide (MSC.1/Circ.1588/Rev.3), the IATA DGR.

Note that EMCargo deliberately runs behind on some points and says so — see
[Rule set editions](docs/dangerous-goods.md#rule-set-editions) before reporting a
mismatch as a bug.

## Please do not send us regulatory text

The repository holds **factual data only**: a UN number mapped to a code, a material
mapped to a density. The regulations themselves — ADR, the IMDG Code, the IATA DGR — are
copyrighted and are **not** in this repository and must not be added to it. This applies
to issues and attachments as much as to code. Quote the clause you need to make your
point; do not paste the chapter.

See [docs/data-sources.md](docs/data-sources.md) for what is in here and where it came
from.

## Privacy in issues

Issues are public. EMCargo is built so that your shipment data never leaves your
machine, and it would be a shame to undo that in a bug report. Before you attach anything:

- Replace real company names, addresses and contact details with placeholders.
- Remove reference numbers, container numbers and licence plates.
- Check exported PDFs — they carry everything you typed.

A redacted report is worth just as much.

## Translations

The interface is Dutch, English, German and French, in `frontend/src/i18n/nl.json`, `en.json`
`de.json` and `fr.json`. If a string reads badly in any of them, an issue quoting the key and
a better wording is genuinely useful and takes two minutes to apply.

That goes double for the German transport terminology. Where the regulations prescribe a
German wording — *Beförderungskategorie*, *Verpackungsanweisung*, *schriftliche
Weisungen*, *entfernt von* versus *getrennt von* — the app should use it, and a native
speaker spotting one that is off is doing real work.

## If we do agree you should write code

Then the ground rules are the ones the project already follows:

- **Run the tests.** `cd backend && DATABASE_URL=sqlite:////absolute/path/to/test.db
  DATA_DIR=/absolute/path/to/data python -m pytest`, and `cd frontend && npm run build`
  for the typecheck. See [docs/development.md](docs/development.md).
- **A behaviour change comes with a test.** Regulatory tables are pinned verbatim on
  purpose, so an accidental edit fails a test instead of silently shipping.
- **Version numbers move conservatively.** Patch for fixes and documentation, minor for
  new functionality, major only for breaking changes. When in doubt, take the smaller
  bump. The policy is in [docs/development.md](docs/development.md#versioning).
- **Update `CHANGELOG.md`** in the same change, under a heading for the version you
  bumped to.
- **Explain why in the commit message**, not just what. The diff already says what.
- **Comments and docstrings are in English.** The interface speaks four languages; the
  source speaks one. A test docstring explains why the test exists and which defect
  provoked it — that is the point of them, and it is worth the extra sentences.

## Code of conduct

Participation is covered by the [Code of Conduct](CODE_OF_CONDUCT.md).

## Licence and contribution rights

EMCargo is source available under Apache 2.0 **with the Commons Clause**.
Contributions offered for inclusion are offered under the current terms in
[LICENSE](LICENSE); contributors retain their copyright. This does not establish
that the maintainer owns every contribution or can relicense it unilaterally.

Identify third-party material, source editions, licenses and applicable notices
with your contribution. Do not add official forms, regulatory text or extracted
datasets on the assumption that a public download permits redistribution.
Changes to registered assets need updated provenance, exact hashes and a review
of the relevant distribution channels. Run `python scripts/check_third_party_manifest.py`.

A [CLA review draft](docs/licensing/CLA-DRAFT.md) describes a proposed arrangement
for future commercial sublicensing. It is **not activated** and no contributor
is treated as having accepted it. Existing contributions do not acquire broader
grants retrospectively. Employer/contractor ownership questions must be settled
before anyone grants rights they do not hold.
