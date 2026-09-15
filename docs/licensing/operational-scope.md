# Operational legal scope

Research date: 2026-09-15. These are applicability decisions to record against
the actual deployment and product offering, not a declaration of compliance.

## GDPR: follow the real data flows

A self-hosted developer who receives no personal data is not automatically a
processor for every installation. Hosted shipment processing, remote support,
diagnostic uploads and geocoding can introduce separate processing operations.
Controller/processor roles follow who determines purposes and means and who
acts on whose instructions, not a label in the software license.
See the [EDPB role guidance](https://www.edpb.europa.eu/sme/learn-the-basics/data-controller-or-data-processor_en).

Record the operator, data fields, recipients, locations, retention, access and
purpose for shipment storage, accounts, logs, backups, support and each external
service. Address autocomplete is an external flow even when the main database
and language model are local. Where processing on behalf of a customer occurs,
prepare the appropriate processor agreement and subprocessor/transfer controls.
Set an incident escalation procedure; security and privacy incidents may have
different reporting tests and deadlines. Do not claim that all shipment data
necessarily stays on the user's machine.

## Cyber Resilience Act: a current applicability question

The [Commission's CRA overview](https://digital-strategy.ec.europa.eu/en/policies/cyber-resilience-act)
describes general application from 2027-12-11. Its
[reporting guidance](https://digital-strategy.ec.europa.eu/en/policies/cra-reporting)
states that in-scope manufacturers' reporting obligations apply from 2026-09-11:
an early warning within 24 hours and notification within 72 hours after awareness
of the relevant actively exploited vulnerability or severe security incident.
Final-report timing differs by incident type. This is not a duty to report every
scanner finding. The guidance distinguishes the later reporting date for
open-source software stewards.

Determine whether the relevant EMCargo offering is a product with digital
elements made available on the EU market in a commercial activity, the responsible
manufacturer and any applicable exception. Assess distributed software and any
remote processing separately. Do not rely on the free/open-source treatment
merely because GitHub is public: Commons Clause restricts commercial exploitation.
The [Commission's open-source guidance](https://digital-strategy.ec.europa.eu/en/policies/cra-open-source)
explains the importance of development/distribution and monetisation context.

Before concluding applicability, document intended use, connection/functionality,
distribution/commercial model, responsible party and the legal basis. If in
scope, map vulnerability handling, secure development, updates/support period,
technical documentation, conformity assessment and reporting to actual owners.
An SBOM is supporting evidence, not a CRA conformity assessment or CE mark.

## AI Act: do not use an obsolete timetable

The [Commission's current AI Act page](https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai)
states that the AI Omnibus entered into force on 2026-07-27. It gives 2027-12-02
for relevant Annex III high-risk uses and 2028-08-02 for high-risk systems
embedded in regulated products, while general application/transparency begins
in August 2026 and AI literacy obligations began in February 2025. The page links
the final instrument as OJ `L_202601744`. The final EUR-Lex text was access-blocked
during this review; these dates are attributed to current Commission guidance,
not a claim to have independently checked every amended article.

An assistant used in transport paperwork is not automatically an Annex III
critical-infrastructure safety component. Record its intended purpose, whether
it is an AI system, provider/deployer roles, interaction with the deterministic
DG engine, human review, autonomy and the applicable classification provision.
Local execution does not itself exempt an AI system. Document disclosure,
staff literacy, limitations, logs and model/version provenance as relevant.
Do not advertise an AI-generated suggestion as regulatory approval.

## Liability and operational promises

Neither source availability nor a disclaimer establishes that outputs are safe
or meets mandatory product, contract or transport duties. The free-use terms
remain a draft; their monetary limits are not a validated risk allocation.
Paid offerings need an identified contracting party, agreed scope, justified
liability terms and consideration of available insurance. Assess mandatory
product-liability rules for the actual placing-on-market date and use before
offering warranties or exclusions.

Preserve the distinction between a tested rule, its edition, a data source and
a qualified person's shipment assessment. The current unknown-value/export
controls support that distinction; they do not certify the substance, packaging,
physical cargo or the complete regulatory position of a real shipment.
