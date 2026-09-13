# Changelog

All notable changes are documented here, following [Semantic Versioning](https://semver.org/).

## [2.8.2] — 2026-09-13

### Compact shipment management

- Replace large shipment actions with compact icons, accessible labels and full touch targets. Apply the same mobile treatment to shipment details and pagination.
- Keep search immediately available and collapse modality, date and department filters behind one button, with an active-filter count and explicit reset.
- Place selection and trip actions on one compact line. Move mobile selection to the card header and retain shipment status and dangerous-goods badges.
- Delete shipments directly from a card or table row after a confirmation naming the shipment. Preserve the row and selection on failure, clear deleted selections and return to a valid page after deleting the final row.
- Ignore outdated list responses and keep the existing departmental access checks for deletion.
- Remove the duplicate DGSA report shortcut from Shipments; the report remains available through DG control.
- Provide new interface text in Dutch, English, German and French.

## [2.8.1] — 2026-09-12

### Available UN card sets

- Generate, validate and publish a UN card set when its generator or measured source data changes on main, so a new installation has a package to download.
- Keep card releases separate from the latest application release and stop publication when generation fails for a requested card.
- Find older card sets across release-feed pages and ignore drafts, previews and releases without the ZIP asset.
- Disable downloading after a check confirms that no set is published. Explain missing releases and failed downloads in all four interface languages.

Card sets cover the measured ADR, RID, ADN and IMDG tables. ICAO remains explicitly unavailable because the repository has no measured air table.

## [2.8.0] — 2026-09-12

### One workspace for trips

- Assemble, check, save and reopen trips on the Ritten page. Groupage is included here, with redirects for existing bookmarks and shipment selections.
- Add shipments directly from a searchable list or import shipment exports. One-shipment trips and ordinary freight are supported alongside dangerous goods.
- Refresh the combined assessment automatically when the load changes. Stale responses cannot overwrite newer results, and saved checks remain visibly dated snapshots.
- Show blocking findings, incomplete data and required attention before calculation details. Saving a trip does not imply DG release.
- Preserve edits on network errors, protect unsaved changes when switching trips, deduplicate imports, accept decimal commas and expose the vehicle mass when needed.
- Keep search, date and department filters, departmental access rules, optional retention, and all four interface languages.

This remains a load assessment workspace, not route optimisation or a loading-capacity planner.

## [2.7.0] — 2026-09-12

### Business addresses in the shipment assistant

- Look up named companies and their addresses from shipment descriptions using the configured address service, including companies outside the Netherlands.
- Offer distinct establishments for selection and require confirmation even when only one match is returned. Keep manual entry available when results are missing or the service is unavailable.
- Preserve existing addresses and shipment details, ignore stale search responses and allow a selected business address to be undone.
- Recognise conversational intent phrases without losing the goods and quantities in the shipment description.
- Remove the visible frame around the assistant header icon and show four lines in address answers.

Address coverage depends on the configured provider. Results are proposals, not an exhaustive business register or verification of a delivery entrance. The assistant still requires an installed local language model.

## [2.6.0] — 2026-09-12

### A more capable local shipment assistant

EMCargo 2.6.0 improves guided shipment creation from ordinary language through to a checked transport document.

- Understand mixed goods, combined dimensions and weights, company names in conversational answers and explicit corrections to earlier goods.
- Ask for clarification when quantities or total/per-item weights are uncertain or inconsistent. Keep optional questions available for later completion without losing required follow-up questions.
- Preserve supplied weights, packaging and route cities through calculations, saved shipments and CMR exports. Refresh results after late assistant edits and distinguish incomplete volume from a known total.
- Require an installed local language model in both the interface and API, with verified native Windows runtime support and clearer recovery when the model becomes unavailable.
- Improve goods imports, account role display, assistant controls, field labels and document download layout across the four interface languages.

Validation includes complete browser flows with the installed local model, saved and reopened ordinary road shipments, rendered CMR checks, backend and frontend regression tests, and container validation.

The assistant prepares a shipment for review. Missing facts remain questions; it does not replace specialist validation. This release includes the improvements developed under the unreleased 2.5.1 version.

## [2.5.1] — 2026-09-12

### More reliable shipment answers

- Apply recognised spreadsheet column order to file and Excel clipboard imports;
  keep manually entered weights when dimensions change, show translated choices
  in folded document groups, and label stored shipment/trip timestamps as UTC.
- Make the PDF, startup, catalogue and updater test fixtures portable to Windows;
  resolve the configured Bash executable and keep POSIX permission checks on POSIX.
- Repair the blank development page, select the pinned native Windows runtime,
  and reject empty or truncated model installations. Pause and resume a pending
  answer when the model disappears; reveal recovery messages on small screens.
- Keep articles before the next field label out of company names, and show
  translated choices in the shipment summary and when revising an answer.

- Require the installed local language model before using the assistant, in
  both the interface and API. Explain installation and manual continuation;
  preserve answers if the model is removed during an interview.
- Keep supplied counts, dimensions and weights together. Never replace a
  stated weight with a density estimate, guess alternative counts, or treat a
  package quantity as the sender. Keep ambiguous corrections open.
- Understand spoken count answers and German/French package units. Validate
  explicitly labelled intake addresses as strictly as follow-up answers.
- Allow weight and dimension corrections directly from the shipment summary
  without discarding later answers. Use plain shipment questions, open the
  relevant explanation for unknown answers and improve small-screen controls.
- Cover the reproduced defects with calculation, API and interaction tests.
- Leave incomplete model-read addresses open and never turn a failed model
  read into a goods line containing the whole story. Omit unstated model
  fields to reduce unnecessary output and invented references.

## [2.5.0] — 2026-09-09

### A guided shipment assistant

- Replace the small survey with a focused shipment workspace: a live summary,
  editable facts, optional details by choice, clear progress stages and a review
  handoff. Add an original compass icon, restrained motion, reduced-motion
  support, keyboard focus management and a compact layout for small screens.
- Let the application's calculation, DG preparation and document definitions
  drive the questions. Read multiple labelled facts, corrections, route answers,
  relative dates and spoken counts. Keep unclear answers visible and explain
  what is still needed instead of saving guesses or silently advancing.
- Validate dates, quantities, negative and ambiguous measurements, weight units,
  and total versus per-item weight. Ground local-model output in the source text
  and prevent guessed addresses, measurements and regulatory choices.
- Preserve assistant answers across recalculation and the move into the DG step.
  Restore complete snapshots on Previous, retain the weight basis, map removed
  goods rows correctly and ignore late responses after closing the assistant.
- Repair missing shared-library links in the downloaded local model runtime,
  including existing installations, and include its system libraries in the
  container. Verify the pinned server starts inside the built image. Bound extraction time and output, and improve
  the structured intake prompt. Simple inputs avoid a model round trip.
- Keep ordinary document validation, authentication, specialist release and DGSA
  permissions in force. The assistant prepares a draft for review; it grants no
  transport release. Include regression tests and a critical review record.

## [2.4.2] — 2026-09-09

### Unraid update setup and a cleaner update screen

- Prefill the Unraid Docker socket mapping and show it in the normal template
  view. Explain in the template how it enables administrator-confirmed in-app
  updates and the Docker/host permissions it grants. Keep the mapping removable.
- Remove Docker installation instructions from the app and use concise capability
  messages. Keep the Check for updates switch, update confirmation and native or
  Kubernetes update commands. Update installation documentation for new and
  existing Unraid containers.

## [2.4.1] — 2026-09-09

### In-app updates without an extra switch

- Enable in-app updates for administrators whenever the installation supports
  them. Retire `UPDATE_APPLY_ENABLED`, including existing `false` values from
  older Unraid templates. Remove the extra setup step from the interface,
  translations, Compose override and Unraid template.
- Keep administrator authorization, update confirmation, Docker socket and
  official-image checks, progress reporting and rollback. Updates still start
  only when an administrator confirms them.

## [2.4.0] — 2026-09-08

### Specialist release and operational roles

- Add DG Specialist and Super User roles. Super Users manage ordinary users,
  other Super Users, departments, equipment and organisation defaults. Privileged
  account management, installation security, branding, mail, connections, updates
  and AI configuration remain administrator-only, enforced by the API.
- Require DG Specialist release for dangerous goods shipments by default. Add a
  review queue with immutable submitted inputs, explanations for requested changes,
  reopening in the wizard and live review status in the export step. Release binds
  to the exact document content across single downloads, bundles, mail and history.
  Drafts stay editable; changed inputs require a new review.
- Restrict every DGSA report route and its interface to Admin and DG Specialist.
  Administrators can optionally grant Super User report access; the default is off.
- Keep review submissions separately from opt-in shipment history and explain the
  stored data before submission. Removing a review revokes its release. Reopening
  the same released review reuses its kept shipment instead of double-counting it.
- Put all transport modes in one grid. Sea and multimodal are disabled with a short
  development label; air remains disabled too. Preserve existing sea calculations
  and saved records. Colour the EM in the shared EMCargo wordmark blue.
- Replace the former disclaimer with the supplied Dutch terms, adapted to EMCargo,
  its review workflow and account access. Provide the complete downloadable source,
  readable articles and translated navigation. Keep the document explicitly a draft
  while contracting-party details and the effective date are unconfirmed. Remove
  contradictory blanket liability language from document notices.
- Align overview links, navigation, department filters, user management, settings,
  output notices and privacy documentation. Preserve public UN-card QR access and
  authentication for the application. Translate new interface controls in all four
  supported languages; the full legal source remains explicitly Dutch.

## [2.3.0] — 2026-09-08

### One full application, with sign-in

- Retire the open application and its anonymous visitor account. Every
  installation now serves the full account-based application; an obsolete
  `EMCARGO_MODE=open` variable cannot bypass authentication.
- Always load and save preferences with the signed-in account. Remove guest
  navigation, browser-only preference handling and the mode selector from
  installation examples. Restore the requested application address after login.
- Preserve public access to UN-card QR links and their PDFs. These still work
  without an account when card links are enabled. Login branding, sign-in and
  recovery, and health/setup probes remain accessible before authentication.
- Require a session for API documentation and the regulatory metadata endpoint.
  Preserve administrator permissions, second-factor enforcement and optional
  shipment retention.
- Preserve existing accounts, saved settings, shipments and auditing when
  upgrading. Former open installations create their first administrator through
  the existing `ADMIN_*` configuration. No automatic database reset is added.

## [2.2.1] — 2026-09-08

### Find your workspace and manage your team

- Keep Overview, Shipments, Trips and Articles directly visible in organisation
  navigation, including mobile and quick navigation. Explain disabled storage
  on the page and link administrators to its setting. Storage remains opt-in.
- Give Overview a clearer greeting, daily totals, recent shipments and quick
  actions. Clear stale records when storage is disabled or a request fails.
- Replace the crowded user controls with a searchable directory, role and
  status filters, and a focused edit dialog. Save changes explicitly, report
  failures inside the dialog, and keep account security actions in a disclosure.
  Preserve current-user and last-administrator protections and deletion undo.
- Let users upload, replace or remove their own profile photo in Settings /
  My details. Show it in the account menu and user directory, with initials as
  fallback. Store a normalized 256-pixel WebP in the installation database,
  accessible to the account owner and administrators. Strip image metadata;
  reject unsupported, animated, oversized or invalid uploads.
- Add the avatar table automatically at startup without changing existing user
  columns or shipment records. Deleting an account also removes its photo.
- Translate all new controls and messages into Dutch, English, German and French.

## [2.2.0] — 2026-09-08

### EMCargo, throughout the workspace

- Introduce a navy and cobalt identity, a new vector logo and a consistent set
  of line icons. Seven original generated photographs cover the transport
  choices and the login backdrop. Preserve custom branding and transport locks.
- Reorganize Settings into personal preferences, organisation and system.
  Updates have their own destination. Security owns two-factor policy and
  session duration; connections own the installation address; UN cards own
  card availability and QR links. Mail settings contain mail controls.
- Show the dangerous substance and its unanswered questions first. Keep
  derived details and special cases in disclosures, preserve every regulatory
  warning, and clear stale findings when the input changes.
- Give the final wizard page a review grid and a quieter document workspace.
  Identical warnings appear once with their affected documents. Failed document
  checks remain explicit; missing-field links and export blockers are preserved.
- Prioritize library and user lists. Creation forms open on demand, equipment
  fields have persistent labels, and secondary pages share the same hierarchy.
- Restyle notifications with restrained status colours and common icons. Pause
  timed messages while pointed at or keyboard-focused; retain undo semantics.
  Confirmation dialogs keep keyboard focus inside and return it on closing.

### Updating from inside EMCargo

- Open Settings / Updates directly from the update notification. Show installed
  and available versions, manual checking, prerequisites and persistent progress.
- Resume progress after navigation or restart and report failed updates inline.
  Prevent concurrent installation attempts, including the helper handover window.
- Preserve named mounts and a custom data directory in the updater helper,
  recognize official digest-pinned images, write progress atomically, and avoid
  overwriting a fast helper's completion. Wait for the replacement health check
  before removing the previous container.
- Add an optional Compose override and Unraid template controls for the existing
  Docker opt-in. See [in-app update setup](docs/in-app-updates.md) and the
  [implementation and visual review](docs/design/review-2.2.0.md).
- No database migration, reference-table or transport-calculation change.

## [2.1.1] — 2026-09-08

### Simpler goods entry

- Replace nested goods cards with a flat, responsive list. Keep description,
  quantity, unit and one localized total immediately visible and editable.
  Move dimensions, per-item figures and completed substance explanations into
  the named Details disclosure; retain the confirmed UN identity on the row.
- Combine file import, Excel paste and the template behind one Import action.
  Preserve column mapping, append/replace choices and import undo. Opening the
  dialog traps focus; Escape returns to its trigger. Cancelled file parsing
  cannot apply a late response, including when a file was dropped.
- Keep unanswered substance questions and actionable calculation errors visible.
  Show names alongside multiple UN candidates. Rejecting a suggestion keeps its
  existing meaning and does not declare goods non-dangerous.
- Shorten mobile progress labels and the Continue action in all four languages.
  Separate long document names and readiness messages in the desktop summary.

### Calculation stability

- Preserve a saved line's total when recalculating unchanged goods. Previously,
  a rounded per-piece value could override the independently rounded total:
  two 25 L petrol packages could change from 37.25 kg to 37.24 kg on reopening.
  Older snapshots and manual totals remain supported; a per-piece-only saved
  weight still works. No database migration is required.
- Record actual mobile and desktop screenshots, regression results and the
  independent focused review in [the 2.1.1 review](docs/design/review-2.1.1.md).
  Container publication remains exclusive to GHCR.

## [2.1.0] — 2026-09-08

### A quieter workspace

- Introduce a consistent charcoal interface, restrained blue accents, clearer
  typography, larger step targets, responsive goods rows and subtle motion that
  respects reduced-motion preferences. Light mode remains supported.
- Replace transport photo tiles with four clear transport choices. Preserve
  custom organisation images and explain unavailable modes in a disclosure.
- Add keyboard navigation with Ctrl/Cmd K, search and immediate page access.
  Suggestions respect the current installation mode and account permissions.
- Keep recommended documents visible; move additional documents and integrations
  into disclosures without changing their selection or validation.
- Make the shipment summary available on phones. Improve login labels, busy
  feedback and compact account-security reminders in all four languages.
- Load secondary pages on demand instead of shipping every screen at startup.

### Reliability and security

- Restore drafts and saved shipments reliably after delayed requests and page
  remounts. Entry and autosave wait for restoration; failed reads can be retried
  without overwriting existing work. Preserve goods when switching transport mode.
- Keep private drafts accessible only to their author, including after an author
  changes department. First publication shares a draft with the author's current
  department; previously saved shipments keep their existing sharing scope.
- Fetch shipment/trip list metadata without loading document JSON, using joined
  relationships instead of per-row queries. No database migration is required.
- Use local calendar-day boundaries for dashboard counts and shipment/trip
  filters, including daylight-saving changes and database microseconds.
- Require current second-factor proof before replacing recovery codes. Rate-limit
  second-factor verification and record replacement in the audit log.
- Default to same-origin access and explicit proxy trust. An origin wildcard,
  including one in a list, never enables credentialed cross-origin requests.
- Share strict quantity parsing between API validation, DG checks and IFTDGN:
  `.5 L` stays 0.5 L; ranges, formulas and non-finite values are refused. Bound
  quantity text before parsing to avoid excessive work on malformed input.

### Upgrade notes

- Reverse-proxy installations must explicitly set `TRUSTED_PROXY_HEADERS=true`
  and the correct proxy count when forwarded headers are required. Set
  `CORS_ALLOWED_ORIGINS` only for deliberately separate frontend origins.
- Custom clients calling `POST /api/auth/two-factor/recovery-codes` must send
  `{ "code": "<current verification code>" }`.
- Containers remain exclusive to GHCR. See [configuration](docs/configuration.md)
  and [the design review](docs/design/review-2.1.0.md) for validation and limitations.

## [2.0.0] — 2026-09-08

### EMCargo 2

- Release the EMCargo identity and dark desktop and mobile interface introduced in 1.207.0.
- Simplify shipment entry with three visible stages, direct Excel paste, draft resume,
  searchable shipments and explicit save-and-close.
- Publish container images exclusively to `ghcr.io/jeffreymooiweer/emcargo`,
  including `latest`, `2.0.0` and `v2.0.0` tags for amd64 and arm64.
- Preserve existing shipment data, user preferences, import formats and native
  installation identifiers. Dangerous-goods checks remain mandatory.

### Known limitation

- Exact visual comparison with the approved mockups remains outstanding because
  the test browser was blocked. Automated tests and build checks cover functionality.

## [1.207.0] — 2026-09-08

### EMCargo dark interface

- Rename the product, generated-document branding, email templates and new 2FA
  enrolments to EMCargo. Keep existing data, import formats and licence attribution.
- Follow the approved dark desktop and mobile mockups: persistent navigation rail,
  overview with draft resume and quick start, three shipment stages, adjacent
  shipment summary and a bottom action bar.
- Add direct Excel paste entry, searchable recent shipments, grouped row actions,
  keyboard-accessible mobile navigation and explicit save-and-close with ordered
  draft writes.
- Use dark mode for new installations while preserving explicit user preferences
  and custom organisation branding. Keep all four interface languages.
- Point release checks and container updates to EMCargo's own repository and GHCR
  image. Preserve native service and archive names for upgrade compatibility.


## [1.206.2] — 2026-09-07

### One form of address

The interface used both at once. The Dutch introduction on the transport-mode chooser
addressed the reader formally; the two-factor notice a couple of centimetres below it
addressed them informally. One screen, two registers — which is what happens when strings
are written one at a time and nobody is looking at the whole.

The owner picked the formal one. **Twenty Dutch strings and four German ones** were
rewritten by hand rather than by substitution, because neither language only swaps the
pronoun: both also change the verb that follows it, and in German the participle clause
around it. French was already formal throughout, and English has no such distinction.

**And a guard, so it cannot drift back.** `test_interface_register.py` reads the four
translation files and fails on an informal pronoun in any of them, with the offending key
and sentence named. It also fails if a fifth language turns up without a rule of its own —
a language nobody wrote a rule for is a language nobody checked.

## [1.206.1] — 2026-09-07

### Two things wrong with the update notice

**The two sentences ran together.** *EMCargo 1.206.0 is available This installation does
not update itself…* — the notice is the version line plus the hint, joined with a space, and
the version line never ended in a full stop. It does now, in all four languages; the stop
belongs to the sentence, not to the join.

**A long action still squeezed a short message.** v1.173.1 put a long toast's action under
its message and forgot the other half: the action itself. An inline action does not wrap —
it takes the width its words need and the message gets whatever is left — so beside *View
the release notes* on a phone the message got about 135px and broke mid-word, four
characters to a line. Both have to be short now. The threshold is measured rather than
picked: across the four languages the labels that are commands come out at 4 to 16
characters (*Undo*, *Set it up*, *Jetzt einrichten*) and the ones that are sentences at 22
to 29.

Only the first of these was still on a current installation; the squeezed layout comes from
a build older than v1.173.1, which is what an installation showing this notice is by
definition running.

## [1.206.0] — 2026-09-07

### The shell plan, measured

The last release of [the shell plan](docs/ux-shell-plan.md), and the one that has to say
whether the other four were worth anything. The full report is in
[the baseline](docs/ux-baseline.md).

**The ten tasks cost exactly what they cost before the plan: 53 actions, no windows, all
finished.** Not one got cheaper. For four releases that moved nearly every piece of
furniture on the screen, that is the outcome worth having — the thing that could have gone
wrong is a rebuilt frame quietly costing two presses somewhere, and it did not.

**Two tasks were added, because none of the ten could see what the shell changed.** None of
them opens a goods line's details, and none comes back to an interrupted entry from outside
the wizard. Both new ones were run against the v1.202.0 build as well as this one, so the
comparison is a measurement rather than a memory:

- *One measurement filled in on a goods line*: **6 actions and 1 window became 5 and none.**
  The window was worth an action on its own — with the dialog open the list underneath could
  not be reached until it was dismissed.
- *Back into an interrupted entry*: **the same four presses, and the count is not the
  point.** The chooser offers four modes and marks none of them as yours; the overview names
  the one your entry is in.

**And the phone was run**, which the first plan recorded as not run. Every task finishes at
390×844, at the same cost as on a laptop, except getting back into an entry — one press
more, because the rail is behind the hamburger. That is the mobile layout working as
designed, counted rather than stepped around.

### What the run found

**The shipments list offered five identical *Select* boxes on a phone.** The table's
checkbox has carried its shipment's reference as its accessible name since the selection was
built; the card's — which is what a phone shows — said only *Select*, with nothing telling a
screen-reader user which shipment each one selected. Both carry it now.

And two things about the harness, which was measuring less than it claimed. It could not
read the step on a phone, where the pills are icons carrying an accessible label and no
text, so every phone run reported the step as *unknown* and marked two finished tasks
unfinished. And it looked for the shipments' selection inside a `<table>`, which a phone
does not have — measuring half the application and reporting the other half as having no
selection at all.

## [1.205.0] — 2026-09-07

### Somewhere to come back to

The fourth release of [the shell plan](docs/ux-shell-plan.md): an overview, at **`/overzicht`**.

Four things, in the order somebody arriving in the morning wants them:

1. **Where you left off.** The running draft, with the way back into it — in the mode the
   draft is in, which the wizard needs and nobody remembers. It was already restored when
   you opened the right mode's wizard; here it says which one that is.
2. **What today has been.** How many shipments were kept and how many trips were put
   together since midnight. Counted by the server with a date filter and read for their
   totals, not assembled out of a page of results: a number built from the first fifty rows
   quietly stops being a total at the fifty-first.
3. **Somewhere to begin.** The available modes, one press each.
4. **What was made before.** The last few shipments, to open or to start from. The running
   entry is not among them — it is entry in progress, it has its own box at the top, and a
   thing listed twice is a thing to reconcile.

**`/` is untouched.** The chooser still has its six tiles with their pictures, the two
locked ones with their reasons, and the redirect that takes somebody with a preferred mode
straight into the wizard without a stop. [The usability plan](docs/ux-plan.md) asked for
recent shipments as templates *without sending somebody with a default mode through a
dashboard first*, and putting this on `/` would have done exactly that. So it has an address
of its own, it is first in the rail for whoever wants to start their day there, and nobody
is sent through it.

**And it is honest about an installation that stores nothing.** Where the history is off
there is no draft, no count and no recent shipment: the page says so in one sentence, shows
the quick start alone rather than four empty boxes, and asks the server for nothing. The
rail leaves the link out there entirely, the way it already does for the shipments page.

## [1.204.0] — 2026-09-07

### What the shipment adds up to, beside the work

The third release of [the shell plan](docs/ux-shell-plan.md).

Two things were true before this and neither was good. The counts — lines, weight, volume,
warnings — were four cards on the goods step and nowhere else, so the moment you moved to
the questions the totals you were entering against went off the screen. And the documents
being prepared were only visible on the step that asks their questions, so on the goods step
nobody could see what all the typing was *for*.

**One panel, on every step**, holding both: the four numbers, and the document set with what
each one is still waiting for. A document short of an answer says how many and **the count
is the way in** — pressing it goes to the first of them, the same jump release 111 built for
the export step's chips, now offered from a place you pass much earlier. A blocked document
says it is blocked instead: blocked means the substance itself is not established, there is
no one field to go to, and offering a jump would send somebody nowhere.

**Attention is one number now.** What the calculation flagged on the goods and the substance
questions nobody has answered were counted separately; they are added, because two counts of
"not right yet" are two counts to reconcile.

**Where it stands, and why that is not a contradiction.** The rail folds away when the
wizard opens because the lines table wants 1,620px — so a column beside it looks like it
must cost the list its width. It does not: since v1.193.0 the list is a row of fields that
wraps rather than a table with fixed columns, and 1,620px is what it uses happily rather
than what it needs. Measured at 1440 with the panel beside it, the row is still one line. So
the panel is a sticky right-hand column from `xl` up, and below that it is a card above the
list — which is where the four counts always were.

The action bar's attention count and the panel's are the same number, so only one of them is
ever on the screen: the panel's from `xl`, the bar's below it.

## [1.203.0] — 2026-09-07

### A goods line that opens, with its substance in it

The second release of [the shell plan](docs/ux-shell-plan.md).

**The line expands where it stands.** Everything that was behind the details icon — the
article, the cargo form, the dimensions, the wall thickness, the own weights, the
dangerous-goods tick — now opens underneath the row instead of in a window over the list.
The arrow says which way it will go, one line is open at a time, and the row above it stays
on the screen. The description, the quantity and the unit are not repeated in there: they
are one line up, and a second copy of a field is a second place for the answer to be wrong.

**The substance is stated on the line that carries it.** For a dangerous line the panel also
holds its identity: the UN number, the proper shipping name, the packing group, the type of
package and the net per package. Those were asked on the dangerous-goods step — one step
after the step that had already recognised the substance and put a UN number on the row.
What is answered here is seeded into that step's product, and what is left empty still comes
out of the tables. The class is deliberately not asked: it follows from the UN number
through Table A, and a field for it invites somebody to state something the tables then
contradict.

The dangerous-goods step keeps everything it is actually for — the compliance check, the
tunnel code, the transport category, mixed loading, the 1.1.3.6 calculation, the special
cases of 5.4.1.1. The plan said that step would disappear for a common shipment; it already
does, and for a shipment that does carry dangerous goods there is always something to
assess. The plan now says so, with the reason.

Two disagreements between the row and the panel, found by opening one and looking:

- The calculation marks a line dangerous when it reads a UN number in the description, and
  the row says so — while the panel's tick stood empty, saying the opposite. It follows the
  calculation now until somebody sets it themselves.
- The recognised UN number was nowhere in the UN field. It stands there as the placeholder:
  it is what the next step starts from, and it is not something anybody has stated yet.

## [1.202.0] — 2026-09-06

### The shell: one header instead of four strips of furniture

The [usability plan](docs/ux-plan.md) made the work cheaper — 83 actions became 53 and the
two impossible tasks became possible. [The second plan](docs/ux-shell-plan.md) is about
where the work *sits*, and this is its first release.

**One header.** What a shipment is called, what has happened to it, where you are in it and
which transport mode it is being entered for, in one box. It was four strips stacked on top
of each other: a modality chip with a link beside it, a row of step segments, a draft line,
and then, wherever the open step happened to end, that step's own pair of buttons.

**The mode is now a switcher.** It changes the mode of the shipment in front of you, and the
entry comes with it: the goods, the answers, the substances, the signature. The calculation
does not travel — it was made against the rules of the mode you have just left, and carrying
it over would put totals on the screen that claim to come from a book they were never read
out of — so the wizard lands back on the goods step and works it out again. Choosing where
to *begin* is still the tiles at `/`, which have not moved and are still one link away from
the header.

**One action bar, at the foot.** Every step's buttons land in it, so the way forward is in
the same place on every step instead of wherever the step ended. It is `sticky`, not
`fixed`, and the difference was measured rather than assumed: a sticky bar stays in the
layout and takes its own height at the end of the page, so the last row of a long form —
and the error standing next to it — is never left underneath it. What sticky does not claim
is that it never overlaps at all; while you are scrolled above its resting place it floats
over what is behind it, one scroll away. The code and the plan both say so now.

**The rail folds to icons instead of to nothing.** Opening the wizard used to take the whole
menu off the screen, and getting back to it meant unfolding first. It now folds to 56px of
glyphs, each carrying its label as its accessible name, and the shell's width cap moved by
exactly those 56px so the lines table keeps the width it was measured to need.

Twenty-one icons came in for this, supplied by the owner. Their provenance is recorded
honestly in [the source list](docs/data-sources.md): four are drawn the way a Uicons export
is and seventeen are not, so the Legal page names them on their own line rather than
stretching the Uicons credit over them, and what is still needed to credit their authors is
written down.

Found by looking at a phone rather than at the code: a single wrapping header row left the
title twenty pixels wide — a shipment called *N…*. The title has a row of its own now.

## [1.201.0] — 2026-09-06

### The plan measured to its end, and two things it turned up

The twelve releases of [the usability plan](docs/ux-plan.md) are built. This one runs the
whole set of ten tasks once more, in one pass against the finished application, and writes
the closing measurement at the foot of [the baseline](docs/ux-baseline.md).

**83 actions became 53, eleven extra windows became none, and the two tasks the baseline
could not finish now finish** — a substance suggestion closed, judged and revisited, and a
reload halfway through entry. Two rows went up, and both are the release's point rather than
a regression: the fourth action of the fifty-row import is the narrowing that made the one
unclear line findable at all, and the sixth of the trip is the action that turns the
shipments on the screen into one.

The run itself turned up two things, both fixed here.

**The export step said *Update in history* over a shipment nobody had kept.** Since drafts
arrived the entry has a row of its own from the first keystroke, and the button read that
row's existence as "kept". Kept and written are not the same word: it says **Keep in
history** until the shipment has actually been kept.

**And the harness had to be taught to start from a standing start.** The wizard now resumes
the draft the previous visit left behind — which is release 115 working exactly as intended,
and wrong for a measurement, where every task begins from the same place. It discards the
running draft before it starts, the way a person would with **Discard the draft**.

## [1.200.0] — 2026-09-06

### The list does the work, and the menu says what it holds

Releases 116, 117 and 118 of [the usability plan](docs/ux-plan.md) — the last three — in
one version.

**Reuse is on the row.** The [baseline](docs/ux-baseline.md) found *no reuse action on the
shipments list at all*: opening the detail page was compulsory before anything could be
done with a kept shipment. **Open**, **Use as basis** and **Documents again** now stand
beside every shipment, on the phone as on a wide screen, and each row says in a word what
it is — *draft*, *still to complete* or *ready*. The entry somebody is in the middle of
stands above the list with the way back into it.

**A copy is a new shipment.** As well as the reference and the dates it already dropped, a
template now drops the signature and every declaration somebody had signed for. A form
arriving with last week's confirmation already ticked is a form declaring something about
goods nobody has looked at.

**And a shipment can start from an earlier one where a shipment starts:** the last few kept
shipments are offered on the goods step, while nothing has been entered.

**A trip starts from the shipments you are looking at.** Tick them on the list and **Add to
a trip** opens the groupage check with the selection in it. The authorisation did not move
— each one is fetched in the viewer's own name, and a shipment they may not see is simply
not there — the same shipment cannot be added twice, and the file import stays exactly as
it was.

**The menu is four groups**: the work, the libraries it draws on, what an administrator
keeps, and this account. Every address is the one it always was. On the mode chooser the
modes that can actually be used come first; the ones that are not ready stay on the page,
because what they say about themselves is worth reading.

**A defect found while measuring:** an empty wizard was writing a draft on every visit,
because the dates it fills in by itself counted as entry. They do not: a shipment nobody has
typed a word into is not entry in progress.

Measured: an earlier shipment as a basis went from 2 actions to 1. Five shipments into one
trip counts 6 where the baseline counted 5 — five ticks on the list and the one action that
makes a trip of them, instead of five presses on a page the user had to reach separately.

## [1.199.0] — 2026-09-06

### A last look before the documents, and an entry that survives a reload

Releases 114 and 115 of [the usability plan](docs/ux-plan.md), in one version.

**The export step opens with what is about to go on paper.** Who is sending and receiving,
the route, the goods with their totals, what is actually being carried, the assessment, and
the language the documents are drawn up in — each with **Change** beside it, going to the
answer itself rather than to the step it lives on. An answer nobody gave says *nothing
filled in yet* instead of showing an empty space.

**One action finishes the job**, with one document as with five: the package is downloaded
by the same button either way, and the separate downloads, the mail and the integration
formats stay beside it as the secondary things they are. **A partial package is called
partial** — *download what is ready (3 of 5)* — and names the documents that are not in it.
And when the download is done the step says so plainly: the documents are in your downloads,
check them, sign them where that is needed, and get them to the driver. Having a document is
not having sent it.

**The entry survives a reload.** The [baseline](docs/ux-baseline.md) reloaded halfway through
a shipment and found the wizard back at the goods step with nothing left of what had been
typed, and nothing had warned beforehand — the second of the ten tasks it could not complete.

Where the installation keeps shipments, the running entry is now kept as a **draft**: its own
row, marked as such in the database, left out of the shipments page and out of the safety
adviser's annual report, readable by its author and nobody else. The screen says which of
*Saved at 14:49*, *Saving…* or *Could not save* is true, never claiming a save that failed,
and a reload comes back to the shipment on the step it was on. **Discard the draft** throws
it away. Saving the same row without the draft flag is what makes it a kept shipment — there
is no copying and no second row.

Where nothing may be stored — the open application, or the history switched off — nothing is:
the screen says *this installation stores nothing: a reload loses your entry*, the browser
asks before the page is left, and the draft can be downloaded as a file and opened again
later. A promise not to store anything is not a licence to lose somebody's work silently. An
administrator switching the history off discards any drafts along with it.

This release carries a schema step: `is_draft` on the shipments table, stamped on a fresh
database and added to an existing one.

Measured on the same tasks: the reload is **completable** for the first time — the entry is
there and the wizard is on the step it was on — and the reload where nothing is stored says
so and offers the file, in two actions. A simple shipment measured unchanged at 19 actions.

## [1.198.0] — 2026-09-06

### The document advice arrives before the work, and says why

Release 113 of [the usability plan](docs/ux-plan.md). The document set was chosen on the
export step — the [baseline](docs/ux-baseline.md) found it *behind eleven checkboxes, after
every document field has been filled in*. Deciding what to prepare after preparing it is
the wrong order, and it made every late change cost a walk back.

**The advice now sits on the step that asks the questions**, above them: this is what we
are preparing, and this is why. The export step no longer chooses anything; it offers one
way back to the choice.

**Each document says why it is on the list** — the transport document carrying the 5.4.1
particulars for this modality, a supporting paper for dangerous goods, the customary
document for this modality, a commercial document that is the consignor's choice. Every one
of those is read off the registry: which document a modality names for 5.4.1, which papers
are dangerous-goods only, which document a modality customarily uses. No rule is invented
for a label. Where a whole group is on the list for the same reason it is said once above
it; where the reasons differ, each card says its own.

**The JSON export and the EDI notification are no longer offered as documents.** They are
data read by another system, so they sit in their own **Integration** group, marked as such
in the registry rather than guessed from the name of their exporter.

**And choosing a document says what that added.** Ticking one names how many questions came
with it and leads to the first one that is needed — or says, when that is the truth, that it
adds none because everything it needs is already being asked. Measured: the delivery note
added five questions and the cursor landed in the first; the packing list chosen after it
added none.

Measured on the same task: choosing an extra document in place — on the step it belongs to
— costs 3 actions and no step change. Task 5, which starts from a finished shipment and
must walk back to the choice, went from 4 actions to 5; that fifth is the way back, not the
choosing.

## [1.197.0] — 2026-09-06

### The questions are grouped by what they mean, not by which document asks

Release 112 of [the usability plan](docs/ux-plan.md). The shipment-details step was built
per document: one form with the shared fields, then one form for every selected document
that had fields of its own. Four documents meant four forms — and because the answers are
one map keyed by field key, a document asking for the container number was re-asking what
an earlier form had already asked, under its own box number.

**The step is now one page with three groups: parties, route, additions.** The additions
hold the references and whatever each document needs beyond them, under that document's
name. A field is asked once. Where more than one document wants it, the form says so
underneath the field — *also asked by: Delivery note (Date)* — instead of asking again,
and a field any selected document requires is marked required, whatever the document that
defined it first called it.

Counted from the registry: a sea shipment of an IMO declaration, a bill of lading
instruction, a VGM and a packing list put 68 questions across its forms and now asks 62,
each once; road with a packing list and a delivery note goes from 39 to 37, air from 43 to
40.

**A group that wants nothing more folds to what it says**, with **Change** beside it — so a
shipment reopened from the history or built from a template is three summaries and a way
on, rather than a form to scroll past. Folding is decided when the step opens: a group
never folds itself away under the hands of somebody who has just finished filling it in.
**Next** still tells before it walks on, and it now opens the folded groups that are hiding
something empty.

Measured on the same tasks: a simple shipment crossed two forms inside the details step and
now crosses one (19 actions, was 20), and an extra document chosen on the export step brings
no form of its own at all.

## [1.196.0] — 2026-09-06

### From the notice straight to the field it is about

Release 111 of [the usability plan](docs/ux-plan.md). The export step named what a
document was still missing — *Missing: Consignor — name, Consignor — address and
country, Consignee — name…* — in one line of plain text. Reaching any of it meant
pressing **Back**, finding the form the field lives on among the ones the step is built
from, finding the field on it, and walking forward again. The [baseline](docs/ux-baseline.md)
measured that as 11 actions and four step changes to correct a single field.

**Each missing field is now a button.** Pressing it opens the step it belongs to, the
form within that step, and the field itself, with the cursor already in it. **Back to
the overview** returns to the card that asked. Every field on the shipment-details step
carries an identity from the document registry, so its label is really a label — its
`for` names the control it belongs to — and a field can be arrived at by name from
anywhere. That includes the address fields, whose textarea, not their lookup box, is
what a document reads.

**The progress bar became a way back.** A step somebody has already been on is a button
that returns to it. The step you are on is not a link to itself, and a step nobody has
reached is not offered — that would be a way to skip what is in between, and there is
nothing there to go back to.

**And Next tells before it walks on.** A form with required fields still empty says
which, above the form and on the fields themselves, instead of walking on quietly. It
says it on **Next** and never while somebody is halfway through typing: the marks appear
on the press and clear the moment something is typed. A second press carries on anyway —
EMCargo does not block a document it cannot finish, the export step keeps saying what
is missing, and the server has the last word on what a document needs.

Measured on the same tasks: correcting an error named on the final overview went from 11
actions to 3, and an extra document's one new answer from 7 actions and three forms
crossed to 4 and two. A shipment whose fields are filled measured unchanged, so the
telling costs nothing when there is nothing to tell.

## [1.195.0] — 2026-09-06

### The substance question is asked on its line, and answered in words

Release 110 of [the usability plan](docs/ux-plan.md), and the one the
[baseline](docs/ux-baseline.md) recorded as a task that could not be completed at all.

The name recognition asked its question in a snackbar at the bottom right of the screen,
away from the line it was about, and its close button was an answer: the × set
`dg_dismissed`, so "not now" was stored as "not this substance". The line then showed no
trace of the question, so the decision could not be found again, let alone revised.

The question now sits under the line it belongs to, with three answers spelled out.
**Take UN 1203** ticks the line and carries the number to the dangerous goods step. **A
different substance** ticks it and leaves the number to that step, where a substance is
actually established. **This suggestion is wrong** rejects the candidate and nothing
else — it says so on screen, *rejecting says only that this substance is not it, not that
the goods are harmless*, and it touches neither the dangerous-goods tick nor anything the
compliance check reads.

An answered line says which of the three it was, with **Change the answer** beside it. A
decision you cannot find again is a decision you cannot check.

**And an unanswered question stays visible.** The goods step counts it above the list, next
to the lines that want attention, and the filter narrows to it; the export step says how
many lines still carry one, with a way back. "We thought this might be UN 1203 and never
found out" is precisely what a document check is for.

Measured on the same task: closing a suggestion, judging it and revising it later went
from 8 actions, 2 windows and **not completable** to 5 actions, **0 windows** and done.

A shipment saved before this release opens with its answers intact: a `confirmed_un` reads
as confirmed and a `dg_dismissed` as rejected, and the assistant keeps speaking the field
it always did.

## [1.194.0] — 2026-09-06

### The import is on the goods step, and says what it left behind

Release 109 of [the usability plan](docs/ux-plan.md). Pasting a list from Excel and
choosing a file were one **Importeren** button that opened a dialog, and inside that
dialog the file chooser was an icon. Both are now actions with names on the goods step
itself, and the panel takes a file dropped on it.

**It only asks where there is doubt.** A file whose heading row the server recognised has
nothing left to ask about, so an empty shipment simply gets the lines. A file whose
columns were guessed from their order still shows the mapping first — that is the one
case where a wrong guess is invisible afterwards. Asking every time is how a column
question becomes something people click past.

**Adding or replacing.** A shipment with nothing in it is not asked which of the two it
wants; there is nothing to replace. Once there are lines, both are offered by name, and
either can be taken back from the snackbar that follows — the lines that were replaced
come back with the numbering they had. That undo is what makes offering "replace" at all
reasonable.

**What came out is said above the list** — *49 settled, 1 wants attention* — with a button
that narrows the list to those. The baseline had that one row sitting 5,746 pixels down
the page with nothing pointing at it; it is now one action away. Measured on the same
task: fifty rows imported went from 3 actions and **1 window** to 4 actions and **0
windows**, and the fourth action is the one that was impossible before — narrowing to the
row that needs looking at.

**And the reason is readable.** The goods pipeline can put seven messages on a line and
five of them had no translation at all, so the screen showed the bare code
`dimensions_missing` to whoever needed the sentence most. All seven now say what is
wrong and what to do about it, in four languages, and a test reads the pipeline's source
so the next one added cannot slip past.

`ImportDialog` is gone with this; the column mapping it wrapped is unchanged and now sits
inline.

## [1.193.0] — 2026-09-06

### The goods line, edited where it stands

The first release of [the usability plan](docs/ux-plan.md). A goods line carried its
description, its quantity and its unit behind an edit icon, in a dialog, and the
[baseline](docs/ux-baseline.md) measured what that cost: five quantity corrections took
fifteen actions and five windows, none of which was the number itself, and nine of the
twenty-six actions a three-line shipment needed were the dialog opening and closing.

Those four things — description, quantity, unit, and what EMCargo worked out from
them — are on the line now. The thirteen fields the old table died of are not back:
dimensions, wall thickness, packaging, own weights and the article stay in the detail
dialog, one click away under **Details**. The row wraps rather than switching layouts, so
a phone stacks the same fields with the same validation and the same focus order instead
of getting a second implementation.

Measured after, on the same tasks with the same harness: a simple shipment 26 → **20**
actions and 3 → **0** windows; five quantity changes 15 → **5** actions and 5 → **0**
windows. The produced CMR carries the same three goods lines, the same consignor and the
same places as before.

Three smaller things that came with it:

- **A new line gets the cursor**, in its own description; **Enter** makes the next one,
  so a list can be typed without the mouse. Adding a line used to leave the focus on the
  button that added it.
- **The figures no longer blink away on every keystroke.** A line whose own text has not
  changed keeps what was worked out for it, greyed and marked *to be rechecked*, while
  the recalculation runs. The line being edited shows no figures at all: a weight that
  belongs to the previous description is not a weight.
- **The catalogue searches only while its list is open**, and the equipment library is
  fetched once for every box on the screen. A fifty-line import used to mount fifty
  boxes, each asking for the library and each firing a catalogue search for the text it
  was mounted with. The suggestions also close on Escape and on Tab, instead of staying
  open over whatever comes next and swallowing its clicks.

`RecordCards` is gone with this: it existed to make a read-only record work at every
width, the goods line was its only user, and the goods line is not read-only any more.

## [1.192.0] — 2026-09-06

### The usability plan, and the baseline it will be judged against

An external usability review of v1.189.0 read the wizard, the goods step, the import,
the document fields and the shipments and trips pages. Its claims were checked against
the code one by one; what held up is now written down as twelve releases in
[The usability plan](docs/ux-plan.md), from inline goods editing to drafts and a trip
built from a selection.

Before any of it is built, the ten tasks the review names were driven through the real
interface in a real browser and counted:
[The usability baseline](docs/ux-baseline.md). The harness that did it,
[`scripts/ux_bench`](scripts/ux_bench/README.md), stays in the repository so every later
release can rerun the tasks it touches and report a measurement rather than an estimate.

What the run found, in short: a simple three-line shipment costs 26 actions and three
dialogs, nine of them the line dialog opening and closing; five quantity changes cost 15
actions and five windows; one unclear row among fifty imported sits nearly six thousand
pixels down the page with nothing pointing at it; closing a substance suggestion stores
it as a rejection that cannot be found again; the export step names eight missing fields
in text that cannot be clicked, and none of the three step pills goes back; a reload
during entry loses everything without a warning; and the shipments list offers neither a
reuse action nor a multiple selection. Two of the ten tasks cannot be completed at all
as they are written.

No product code changed in this release.

## [1.191.0] — 2026-09-06

### The dependencies the audit flagged, upgraded

The other half of the external review of v1.189.0: the runtime pins with published
vulnerabilities. Its own release because one of them is a major version of the web
framework, and a framework upgrade that rides along with bug fixes is a framework
upgrade nobody can back out on its own.

- **FastAPI 0.115.6 → 0.141.1, Starlette 0.41.3 → 1.6.0.** Starlette 1.x drops the
  `on_event` hooks; start-up is a lifespan now, the same moment under another name.
  FastAPI 0.141 keeps an included router as one entry in the route table instead of
  flattening it, which silently emptied the tests that walk that table for unguarded
  addresses — they passed for the wrong reason. They read the effective table through
  FastAPI's own iterator now (`tests/route_table.py`) and assert that they saw it.
- **python-jose 3.3.0 → PyJWT 2.13.0.** The tokens are HMAC-signed with the
  application's key and read nowhere else; python-jose's asymmetric algorithms were
  never used, and its ECDSA dependency has an advisory with no fix. PyJWT does the one
  thing needed with no such baggage. Existing sessions stay valid: same algorithm,
  same key, same claims.
- **python-multipart 0.0.19 → 0.0.32, pypdf 6.14.2 → 6.17.0**, the fix versions of
  every advisory `pip-audit` reported against them.
- **pytest 8.3.4 → 9.1.1, pytest-asyncio 0.24.0 → 1.4.0** in the development set.

`pip-audit` against the runtime set reports nothing after this.

## [1.190.0] — 2026-09-06

### What an external audit found, fixed

An independent review of v1.189.0 with synthetic data and its own test scripts named
eighteen findings. The ones that held up against the code are fixed here; the rest are
either design choices that stay (the proxy headers are trusted by default for an
installation behind a reverse proxy) or cosmetic (a 405 where a 404 would read better).
The dependency upgrades it asked for are the next release, on their own, because they
carry a FastAPI major version.

**A removed department left its trips behind.** Removing a department cleared the users
and the shipments and forgot the kept trips, which kept the old department id — and
SQLite hands that id to the next department created, so a new department inherited
another's trips. The removal now clears every table that names a department and says
how many trips it touched.

**Quantities read a thousandfold wrong.** Every reader took the first run of digits with
one optional separator, so `1.250,5 L` was 1.25 litres in the IFTDGN, in the 1.1.3.6
points and in the LQ measures alike. One parser now reads for all of them, with the
thousands rules written out in `services/quantities.py` and pinned by tests; a
negative quantity is refused rather than made positive; a net per package is multiplied
by the packages instead of being written as the item's total.

**The IFTDGN said what it did not know.** A UN number that was not four digits was
padded into `0000` and sent as fact; a filled column 7a was written as `LIMITED
QUANTITY` whether or not the consignment travelled under 3.4; an emoji became a bare
`?` — the release character — because the character set was applied after the
escaping. The notification now names a bad UN number and a bad quantity as problems
before it leaves, writes no limited-quantity statement, and replaces what ISO 8859-1
cannot hold before the service characters are released.

**A kept trip under a regime that does not exist.** `POST /api/trips` accepted any
string as a profile and judged the trip under ADR anyway. Unknown profiles are refused
with a 422; `adr` and `IATA` are read as `ADR` and `IATA_DGR`, as the compliance request
reads them.

**The audit export could hand a spreadsheet a formula.** A shipment reference `=1+1`
went into the CSV as typed. Cells that start like a formula are prefixed with an
apostrophe, the convention every spreadsheet reads as text.

**A working second factor could be replaced without a code.** Starting an enrolment over
a confirmed one overwrote the secret from a borrowed session. It is refused now: a
factor is switched off with a code first, never quietly replaced.

**A required second factor was a notice, not a rule.** The policy was checked at
sign-in and the screen sent people to the panel, but every route let the session
through. The server now refuses every call except the panel's own — who am I, the
factor, my preferences, the public settings — with `auth.two_factor_required`, and the
interface takes the person to the panel and says why. Nobody is locked out; nobody can
work around it either.

**A reference outside ISO 8859-1 broke the export download.** An emoji in the shipment
reference turned the structured export into a 500, because the file name was written
into the `Content-Disposition` header as it was. The header now carries an ASCII
fallback and the real name percent-encoded, per RFC 6266.

**A wildcard origin travelled with credentials.** `CORS_ALLOWED_ORIGINS=*` with
credentials makes Starlette reflect whatever origin asks, cookie included. The wildcard
is now answered without credentials; named origins keep them. The interface served by
the application itself is same-origin and unaffected.

**A damaged spreadsheet was a 500.** A file that is not the `.xlsx` its name says is
refused with `import.unreadable_file`, in the user's language.

## [1.189.0] — 2026-09-05

### The IFTDGN notification, written from the D.16A directory

The UN/EDIFACT dangerous goods notification — the message port
authorities and port community systems read — as an export beside the
JSON, built from the same parts.

- **The message.** IFTDGN, directory D.16A, revision 8: BGM 890 with the
  shipment reference, DTM 137, TDT with the Recommendation 19 mode and the
  vehicle, NAD for the carrier, the forwarder and the consignor, EQD for the
  container, one CNI consignment with its places of loading and discharge,
  and per dangerous product a GID goods item with DGS (the regulation, the
  class and a subsidiary risk, the UN number, the flashpoint, the packing
  group as danger level, the EmS, the hazard identification number as the
  orange placard, the labels, the tunnel code), FTX AAD with the technical
  name, FTX AAC with what the codes cannot say, MEA with gross and net, and
  SGP with the container. ADN travels as `ZZZ` and says so: the D.16A code
  list has no code for it.
- **The syntax and the check.** A segment writer that releases every service
  character and drops trailing empties, a parser, and a validator that walks
  the segment table — every message is parsed back and checked before it is
  written. The export refuses a shipment without dangerous goods, a product
  without UN number or class, and a product without any mass, each with a
  sentence in the four languages.
- **Where.** *Dangerous goods notification (UN/EDIFACT IFTDGN)* on every
  transport mode in the export step and the bundle, as an `.edi` file with
  the media type `application/EDIFACT`. *The IFTDGN notification* in the
  documentation gives the segment-by-segment account, the worked example
  and what is deliberately left out (the consignee, coded package types,
  the gateway's own identifiers).
- **The directory stays out of the repository.** Its licence allows use but
  not modified redistribution; `backend/app/config/iftdgn_d16a.json` holds
  the segment table and the code values EMCargo uses with their
  checksums, and the test suite verifies them against the directory
  whenever it is at hand.

## [1.188.0] — 2026-09-05

### The history switch is the administrator's

`EMCARGO_HISTORY` dated from the three privacy levels; with two
applications and one history it was the last feature switch that could only
be flipped at deploy time. It is now a setting on the screen.

- **Keep shipments (history)** under Settings, Administration, for
  administrators of the organisation application. Off by default; on, the
  shipments, trips and articles pages, the address book and the adviser's
  report appear at once, without a restart — the history routes are mounted
  and answer 404 while the setting is off, so "nothing is kept" is still a
  matter of what answers.
- **Off destroys data, and the screen says so first.** The server refuses to
  save the switch off while kept shipments or trips exist; the screen fetches
  the counts, asks, and on confirmation deletes them (the address book, the
  articles and the reports stay) and then saves the switch. The audit log
  gets `settings.history_discarded` with the counts.
- **Never a hidden table.** A database that holds kept shipments while the
  setting says off — an installation that dropped the variable from its
  environment after upgrading — gets the setting switched back on at
  start-up, with a line in the log. `EMCARGO_HISTORY_DISCARD` is gone;
  nothing is deleted at start-up any more, ever.
- **The variable is the starting value only**, like every other setting with
  a screen counterpart: read until an administrator saves the Administration
  screen, ignored from then on, and never in the open application. New
  installations need not set it.

## [1.187.0] — 2026-09-05

### Groupage trips kept in the history

The judgement over a whole load used to live only on the screen that asked
for it. An installation that keeps its shipments may now keep the trip too.

- **What is kept.** The consignments as they sat on the vehicle — their
  names, their dangerous goods entries and, when picked from the history,
  which kept shipment each came from — the permitted maximum mass of the
  transport unit, and the check's answer as it was given: what each
  consignment said alone, what they said together under 1.1.3.6, the
  mixed-loading findings of 7.5.2 and the limited-quantities marking of
  3.4.13/3.4.14, with the editions all of it was computed against. The
  server runs the check itself on what is sent, so the kept judgement is
  produced by the same code as the one on the screen.
- **Where.** A box under the assessment on the groupage page: name the trip
  and press *Keep trip*; a reopened trip is brought up to date with *Update
  trip*. *Trips* in the menu lists them with the points together and a mark
  where the exemption fell away; the record shows the judgement as it stood,
  reopens the load on the groupage page through `?trip=<id>`, or removes it.
  Who sees which trips follows the departments rule the shipments use.
- **Only with the switch.** Without `EMCARGO_HISTORY=true` the trips
  addresses do not exist and the groupage page says, as before, that the
  trip is not stored. Switching the history off counts the kept trips with
  the shipments, refuses to start while either is there, and deletes both
  with `EMCARGO_HISTORY_DISCARD`. Schema step seven adds the table to an
  existing database; the audit log gets `trip.kept`, `trip.updated` and
  `trip.forgotten`.

## [1.186.0] — 2026-09-05

### The administrator's audit log

Who did what, and when — for the administrator of an organisation
application, and never what a material list said.

- **What is written.** Signing in and a refused sign-in (the name tried and
  why: unknown, wrong password, inactive, wrong code — never the password),
  signing out, a password changed or reset, a second factor switched on or
  off; an account made, changed (which fields), cleared of its second factor
  or removed; the installation's settings changed (which keys, never a
  value — the mail password among them); a shipment kept, updated, reopened
  for its documents, exported or removed (its reference); a document or the
  bundle downloaded (the document keys), the bundle mailed (the keys and how
  many recipients, never who); the safety adviser's report drawn. Each line
  carries the account, the moment and the address the request came from.
- **What is never written.** The contents of a shipment. The test suite
  keeps, exports, re-renders and removes a shipment with named parties and
  dangerous goods and then searches the whole table for them.
- **The page.** *Audit log* in the menu, administrators only: filter by
  account, by action or its group, by date; page through; export the same
  selection as CSV. The action codes are shown as sentences in the four
  languages; a code the interface does not know yet is shown as itself.
- **Retention.** *Audit log retention (days)* under Administration, 365 by
  default; whatever is older is deleted at start-up.
- **Where it does not exist.** The open application has no accounts, writes
  no line and does not have the addresses; the schema runner adds the table
  to an existing database as step six.

## [1.185.0] — 2026-09-05

### The export placed against the eFTI common data set

Regulation (EU) 2020/1056 has the authorities accept freight transport
information electronically from 9 July 2027, through certified eFTI
platforms, and Commission Delegated Regulation (EU) 2024/2024 establishes
what those platforms exchange. Its Annex has now been read from the
Official Journal and the structured shipment export placed against it.

- **The Annex as a seed.** `scripts/build_efti_seed.py` reads the 789-page
  regulation and writes Table 1 (the common data set: 681 data objects with
  identifier, name, definition, type, format and code list), Table 2 (the
  subsets per EU provision: the road transport document, and the ADR, RID
  and ADN transport documents among them, with the status of every element),
  Table 30 (53 code lists) and Table 31 (122 business rules) to
  `backend/seed/efti/`, with the ELI and the checksum of the file.
- **The mapping.** `backend/app/config/efti_mapping.json` places every field
  of the export — the parties, the route, the references, the goods lines,
  the dangerous goods with their derived findings — against the element it
  answers, in three kinds: carried as such, derived by the application, or
  carried in the application's vocabulary and still to be translated into
  the element's code list. `app/services/efti.py` measures it against the
  subsets, and *The eFTI mapping* in the documentation gives the numbers
  and names what is missing: the address in nine parts the party elements
  want, which the application holds as one block of text, and the fields
  the wizard does not ask (class 7, fuel gas systems, fumigation, the
  competent authority).
- A test keeps the seed at the Annex's counts, every mapping entry on an
  element and a field that exist, and the numbers on the page equal to the
  numbers the code counts.

## [1.184.0] — 2026-09-05

### Box 24 of the CIM picks its NHM code from the nomenclature

The NHM code on the rail consignment note was a free-text field with a
format check and a note that the code had to be looked up elsewhere. The
UIC's own correspondence table between the NHM 2025 and Eurostat's NST
2007, supplied by the project owner, carries every position with its
English and French label — and is now behind the box.

- **5,640 six-digit codes**: 5,612 Harmonized System subheadings and 28
  railway-specific positions of chapter 99 (groupage freight, empty wagons,
  loaded intermodal units), each with both labels and the NST 2007 group it
  maps to, in `backend/seed/nhm.json`; `scripts/build_nhm_seed.py` rebuilds
  it from a next edition of the table.
- **Pick by code or by word.** Typing the start of a code lists the
  subheadings under it; typing a word searches both labels, accents or not,
  a word start ranking above a word middle and the shorter heading above the
  longer one. A code typed in full is read back in words under the box.
  `GET /api/nhm?q=` and `GET /api/nhm/{code}` behind the login.
- Labels stay in the two languages the UIC publishes; the box says so
  rather than translating them.

## [1.183.0] — 2026-09-05

### The customs conditions, read in the texts themselves

v1.182.0 derived the ENS and AES conditions from the route on excerpts of
the official pages, because the pages themselves were out of reach. The
texts have now been read in full — the consolidated Union Customs Code,
the eCFR print of 15 CFR Part 30 as of 3 September 2026, DG TAXUD's ICS2
page and HMRC's guidance of 9 July 2026 — and three things changed:

- **Great Britain asks for its own entry summary declaration.** HMRC:
  goods brought into Great Britain from anywhere — the EU included — need
  an ENS in the Safety and Security GB service, lodged by the carrier. A
  route into England, Scotland or Wales now says so; from Northern Ireland
  it names HMRC's waiver for qualifying Northern Ireland goods. Into
  Northern Ireland the earlier reading stands: from Great Britain and from
  outside the EU, in ICS2; from the Union, none.
- **Puerto Rico and the Virgin Islands are not "the United States" for the
  Canada exemption.** § 30.2(a)(1) reads the United States as the 50 states
  and the District of Columbia and names the two beside it, so a shipment
  from San Juan to Toronto is filed like any other export; v1.182.0 had
  left that open. The other territories — Guam, American Samoa, the
  Northern Marianas — are excluded from filing altogether (§ 30.2(d)(2)),
  from them and between the United States and them.
- **A domestic route outside the area** is said to be domestic rather than
  "neither end is in the ICS2 area", and the transit sentence now follows
  Article 127(2)(a): a stop brings goods in, a passage through waters or
  airspace does not.

The module's account of its sources quotes the provisions it rests on.

## [1.182.0] — 2026-09-05

### The route decides the customs conditions

Two reference fields on the details step carry a condition rather than a
rule: the **ENS reference** for goods entering the EU customs territory,
the **AES ITN** for exports from the United States. Until now the help text
named the condition and the person filling in the form decided whether it
applied. The route is on the same screen, so the application now reads it.

- From the country of the loading point and of the destination — a location
  picked from the database, an address from the lookup, or a country typed in
  any of the four interface languages — each field says whether it **applies
  on this route**, does not, or is exempt, and on what ground. Goods from
  outside entering the ICS2 area (the EU customs territory of Article 4 UCC,
  with Northern Ireland, Norway and Switzerland) ask for the carrier's entry
  summary declaration; a movement within the area does not, and neither does
  one that leaves it. An export from the United States, Puerto Rico or the
  U.S. Virgin Islands asks for the AES filing of 15 CFR 30.2(a)(1); Canada as
  country of ultimate destination is exempt under § 30.36, with its exceptions
  named; the value exemption of § 30.37(a) is named for the person to judge,
  because the application does not know the value.
- The places Article 4 takes out of a Member State — Heligoland, Büsingen,
  Ceuta, Melilla, Livigno, and the Faroe Islands and Greenland by their own
  codes — read as outside; Northern Ireland reads as inside, by name, by its
  ports' district codes and by its three airports.
- A route the application cannot place gets no verdict rather than a guess,
  and the condition stays in the help text as before.
- An applicable reference left empty is a **warning** on the export, in the
  document's language, on the documents that carry the field — never a
  refusal, because the ENS is the carrier's to lodge and its MRN often
  arrives after the papers are drawn up.

## [1.181.0] — 2026-09-05

### Installing without Docker

Docker stays the first-class route in, and now it is not the only one.
Every release from this one carries a **native bundle**,
`emcargo-<version>-native.tar.gz`, beside its notes on the GitHub
release: the backend, the built web interface, the templates, the changelog
and the deploy files — the tree the image carries, as a tarball.

- **A native service** under systemd on Debian, Ubuntu and the like.
  `deploy/native/install.sh` downloads a release, unpacks it under
  `/opt/emcargo/releases/<version>`, makes a virtual environment, writes
  the environment file from the example if there is none, installs the unit
  and starts it. `update.sh` does the same for a newer release and moves the
  `current` link; rolling back is moving it back. The data lives in
  `/var/lib/emcargo` and is never touched by an update.
- **Kubernetes** manifests in `deploy/kubernetes/emcargo.yaml`: a
  namespace, a persistent volume claim, a secret for the first
  administrator's password, a config map, a deployment of one replica with
  the `Recreate` strategy (SQLite on one volume), a service and an ingress.
- **`INSTALL_METHOD`** — `docker`, `native` or `kubernetes` — tells the
  application which route it came in by. The settings screen names the
  update route that applies instead of offering an update button that needs
  a Docker socket: the update command for a native install, the rollout
  command for Kubernetes.
- A new page, *Installing without Docker*, in the documentation, and a test
  that keeps the scripts parsing, the unit and the script agreeing on the
  paths, the environment example and the manifests naming only variables
  the application reads, and the release workflow attaching the bundle the
  install script downloads.

## [1.180.0] — 2026-09-05

### Your own articles library

The company's article codes, entered once. On an installation that keeps its
shipments, the **Articles** page holds one article per code with what the
library knows about it: the UN number, the proper shipping name, a technical
name, the class, the packing group, the type of package and the content per
package. A spreadsheet template, an export and an import in the same columns,
so the list can be maintained wherever the office maintains lists; the same
code brings the one article up to date rather than adding a second.

On a goods line the dialog offers **Article from the library**: pick a code
and the line takes the article's name, is flagged as dangerous goods when
the article carries a UN number, and hands the dangerous goods step what the
library holds — only what it holds; the tables fill the rest as they always
did. The code shows on the line as a badge, and can be detached again.

Schema step 5 makes the table on an older database. The routes exist only
beside the history, like the address book's.

## [1.179.0] — 2026-09-05

### The annual report in the shape the competent authority gives it

The DVSA — the UK's Driver & Vehicle Standards Agency — publishes a *DGSA
Annual Report for the Carriage of Dangerous Goods* (December 2025), a
competent authority's rendering of ADR 1.8.3.3 with a fixed structure:
company and adviser details, a risk rating, an executive summary,
activities, incidents, training, high consequence dangerous goods, a
transport table per class with the operations and the quantity band,
practices and procedures, a class 7 block, additional points, comments, who
prepared it, and a checklist DGSA1 to DGSA21. This release gives the
report that shape.

**Fill in the report**, the second tab of the DGSA annual report page,
draws the form from a definition in four languages — the English wording is
the template's own, reused under the Open Government Licence with the
UK-specific bodies written as "the competent authority". What the history
can propose — the classes and quantities in tonnage bands, the method of
carriage, the high consequence goods the 1.10.3 check found, the annual
tonnage, the company name from the branding — sits under a **Take over**
button and is never written into an answer by itself; a class carried by
both mass and volume gets its figures shown and no band chosen. The
answers are kept per year and scope (schema step 4), so a report is filled
in over weeks and found again in five years.

**Report as PDF** draws it on the installation's paper in the template's
order: the answers, the adviser's saved signature from the settings, the
counted figures as an appendix, and the checklist last with each line
naming the section of the report that answers it. Unanswered stays visibly
unanswered.

The thirteen duties on the figures tab now carry the DVSA's English wording
and their checklist codes.

## [1.178.0] — 2026-09-05

### The installation's name and logo on every document

Every document EMCargo draws itself — the packing list, the delivery
note, the placarding sheet, the label sheet, the equipment list, the stowage
plan, the on-board pack, the packing certificate and the rest — is now
printed on the installation's paper: the brand name and the uploaded logo in
the header of every page, the name and the page number in the foot, and the
"generated with" line naming the installation rather than the software.
Where no brand is set, the documents carry EMCargo's own name and logo,
as before. The disclaimer keeps naming EMCargo: the licence is the
software's, not the installation's.

The official forms — CMR, CIM, AVC — are somebody else's paper, filled in
and left alone.

One page frame serves every renderer, and the brand is resolved once per
request rather than handed from function to function, so a renderer added
later cannot forget it.

## [1.177.0] — 2026-09-05

### The safety adviser's annual report

ADR 1.8.3.3 obliges the safety adviser to draw up a yearly report to
management on the undertaking's activities in the carriage of dangerous
goods, kept five years and shown to the authorities on request. The
provision prescribes the report and not its contents, so this release does
two things and keeps them apart.

It **counts what the history can prove**: over the kept shipments of one
calendar year, within what the reader may see, the shipments with and
without dangerous goods, per month, mode of transport, regulation and
department; per class and per UN number with kilograms and litres kept apart
and a quantity without a usable unit counted as unknown rather than guessed;
what the 1.1.3.6 points count said about each shipment when it was kept; and
which documents were issued. The **DGSA annual report** page on the shipments
page shows the count, and **Download workbook** hands it over as an `.xlsx`,
one sheet per table.

It **leaves the adviser's judgement to the adviser**: the practices 1.8.3.3
says the adviser must check — identification, equipment, training,
emergency procedures, incident analysis, subcontractors, procedures,
awareness, documents on board, packing and loading, the security plan of
1.10.3.2 — are listed as headings, in the workbook with an empty column
beside them. A generated opinion on any of them would be worse than a blank.

The duties are read in the official Dutch edition (ADR 2025 NL, 1.8.3.3);
the English, German and French wordings in the report are translations of
that reading, which the file says. The report exists only beside the
history, and a shipment that was never kept is not in it — the report says
that too.

## [1.176.0] — 2026-09-05

### The address book, and a kept shipment as a template

The same five customers, entered once. On an installation that keeps its
shipments, the parties section of the details step carries an **address
book** shared by everyone: pick a consignor, consignee or carrier and their
name, address and contact are filled in; **Save** beside a party puts what
was typed into the book under that name. Saving a name that is already there
brings the one entry up to date rather than adding a second — the button is
pressed on every shipment, and the book must not grow by one entry each time.
The carrier's single "name and address" field is saved with its first line
as the name and joined back the same way.

On the shipments page, **Use as template** starts a *new* shipment from a
kept one: the same goods, dangerous goods, parties and route, with the
shipment reference, the carrier's numbers (booking, AWB, transport document,
ENS, AES, customs MRN, container, seals, VGM, registration, wagon) and every
date left empty. It opens on the goods step without the record's identity,
so keeping it makes a new entry instead of overwriting the old one.

Both live beside the history, and like everything the history brings, exist
only with `EMCARGO_HISTORY=true`; the open application has neither. The
address book is schema step 3, applied on an older database at start-up.

### Fixed

- Every kept shipment listed as "(no reference)": the index read a field
  named `reference` while the wizard writes `shipment_reference`. The index
  now reads the wizard's field first, and shipments kept before this
  release show their reference again the next time they are kept.

## [1.175.0] — 2026-09-05

### Groupage picked from the history

The groupage page took its consignments as JSON exports, because there was
nothing to pick from. On an installation that keeps its shipments there is,
so the page gains a second way in beside the file: **From the history** — the
kept shipments the viewer may see, searched by reference or party, added to
the vehicle with one click. The same structured export the file route reads
is used underneath, so a consignment picked and a consignment uploaded are
the same thing to the check; a shipment without dangerous goods says so
instead of offering a button, and one already on the vehicle cannot be added
twice.

Nothing about the trip is kept, still. Whether an installation with a history
should keep the judgement over a load is the open question the roadmap
records, and this release does not answer it.

## [1.174.0] — 2026-09-05

### Departments: who sees whose kept shipments

The shipment history of v1.173.0 showed every kept shipment to every signed-in
user. That is right for a small office and wrong for an organisation where
sales, the yard and the dangerous goods desk each draw up their own. So:
**departments**, managed on the users page beside the accounts.

**The rule, in one place.** An administrator sees every kept shipment and
gets a department filter on the shipments page — a department, or the
unassigned. Anybody else sees the shipments of their own department, and a
user without a department sees the ones nobody's department claims. An
organisation that never makes a department therefore keeps the plain rule,
everybody seeing everything, without anyone setting anything. The rule lives
in `services/departments.py` and both the list and the detail routes go
through it; a test asserts they agree, so the list can never show a row the
detail refuses.

**Not there, rather than forbidden.** A shipment another department kept
answers 404 for a user who may not see it — not 403, which would tell them
it exists.

**A shipment keeps its keeper's department.** Copied onto the row at the
moment of keeping and never moved: somebody moving departments does not take
last year's shipments along, and keeping a shipment again leaves it where it
was. Removing a department leaves its people and its shipments without one
rather than deleting either; the dialog says so, because "remove" beside a
count of shipments reads as if the shipments go too.

**Schema step 2.** The departments table and the column on users and on
shipments, added by the runner of v1.173.0 to an existing database and
stamped on a fresh one. `PATCH /api/users/{id}` accepts `department_id`, with
null taking somebody out of theirs and an absent key leaving it alone.

## [1.173.1] — 2026-09-05

### A long toast puts its action underneath

A toast with one action put it beside the text, where "Undo" has always
been. That is right for "Deleted. Undo" and wrong for the two-factor
reminder: five lines of text with a button floating top-right beside them,
squeezing them narrower still, read as a layout accident on a phone.

Past sixty characters the single action now goes under the message, in the
same row a question's answers already use, and the text takes the full
width. Short messages are unchanged. The threshold is a character count
rather than a measured wrap, so the first paint and the test see the same
thing.

## [1.173.0] — 2026-09-05

### The shipment history

`EMCARGO_HISTORY=true` makes the organisation application keep the
shipments it makes. Off — the default, and what every installation was until
now — nothing changes: a shipment drawn up is a shipment forgotten.

**The switch, the storage and the page, in that order.** The roadmap fixed
the order by principle: there must never be a version that stores without
the control. So the shipments routes are not mounted without the switch, and
answer 404 like any address the installation does not have; the open
application ignores the switch altogether; and an installation whose
database still holds kept shipments while the switch is off **refuses to
start**, naming the count and `EMCARGO_HISTORY_DISCARD`, the second
variable that lets the next start delete them. Nothing is deleted by
default.

**What a kept shipment holds.** Three documents per row, each for a
different reader: the wizard's own state, which is what "open in the wizard"
restores; the document bundle request as the export step sent it, which is
what "the documents again" re-renders through the same code path as the
download button; and the structured shipment export of v1.161.0 with its
derived findings and the editions they were computed against, which is what
a later reader — a report, a groupage picked from the history — reads. The
server builds the export itself from the parts, so the kept record and the
downloadable one cannot disagree. The index columns a list filters on are
copied out of it at save time.

**When a shipment is kept.** Downloading its documents keeps it, because
"the shipments made" is what the page lists and a download is what makes
one; a **Keep in history** card on the export step keeps it before that. A
reopened shipment carries its id, so keeping it again brings the same row up
to date rather than adding a second.

**The shipments page.** A table on a wide screen, cards on a phone, with a
search over reference and parties, a transport-mode filter and a date range.
Opening a row shows the record and the three things one does with a kept
shipment: open it in the wizard, download its documents again, or remove it
after a confirmation. Every signed-in user of the organisation sees every
kept shipment; departments, which narrow that, are the next phase.

**The schema runner.** `create_all` never adds a column to an existing
table, which is why the settings tables held one JSON document each. The
history is the first thing that wants real columns, so `app/core/migrations.py`
now runs numbered steps recorded in a `schema_version` table: a fresh
database is stamped rather than migrated, an old one has the pending steps
applied in order, each in its own transaction, and every step is written to
be safe to run twice. The development guide's "there is no migration runner"
section is replaced by how to add a step.

Also: `/api/health` reports `"history"` beside `"mode"`; the groupage page's
hint no longer says there is no list to pick from, because on an installation
that keeps its shipments there is one.

## [1.172.0] — 2026-09-04

### Branding: the installation's own name, logo and tile pictures

An organisation that hosts EMCargo for its own people would rather see its
own name on the door and its own pictures on the tiles. **Settings →
Administration → Branding** now holds three things: a name, a logo, and a
picture per transport mode. The header, the sign-in page, the browser tab, the
modality tiles and outgoing mail follow.

**The name is a setting, the pictures are files.** `brand_name` joins the
instance settings, with `BRAND_NAME` in the environment as its starting value
like every other one, and is saved with the administrator's save button. The
pictures act the moment a file is chosen — a picture is a file on the server,
not a value in a form, and "choose a file, then also press save" is the step
everyone forgets. Each has a way back to the default.

**The bytes decide what a file is.** An upload is recognised as PNG, JPEG or
WebP by its first bytes, never by its name or its declared type, and is stored
under the extension the bytes earn. SVG is refused: it is a document that can
carry script, and an image route that serves one is a page that runs it. A
logo may be 1 MB, a tile 3 MB, checked while reading so an oversized upload is
refused before it is held whole. A file planted in `DATA_DIR/branding` with
another extension is not served.

**The door is readable before anybody signs in.** `/api/branding` and the
image routes ask for no session, because the sign-in page shows them — a door
has its sign on the outside. Changing them is an administrator's act on routes
the open application does not mount; its operator places the same files in
`DATA_DIR/branding` by hand and sets `BRAND_NAME`, and the door reads the same.

**An uploaded logo is not inverted.** The default glyph is black and is
inverted for the dark theme; a company's logo is shown in its own colours in
both, because inverting it is not a theme, it is damage. One uploaded tile
picture replaces both the light and the dark default: nobody uploads a company
photo twice.

**The mail carries the same logo as the screen**, with the subtype the file
actually has — a JPEG labelled PNG is a broken image too.

## [1.171.0] — 2026-09-04

### The open application

`EMCARGO_MODE=open` runs EMCargo as a public installation anyone may use
without an account and without leaving anything behind. It is the first half of
the roadmap's two modes; the organisation application — what every installation
was until now — is unchanged and remains the default.

**Not switched off: not mounted.** The routes that presume an account — sign-in,
users, the settings screen, the equipment library, mailing documents, the
administrator's maintenance — are not registered in the open application and
answer 404 like any address that never existed. `backend/app/main.py` now names
the two groups in so many words, `WORK_ROUTERS` and `ACCOUNT_ROUTERS`, and a
test walks the account routes one by one asserting their absence, then the same
list against the organisation application asserting their presence. Two routers
were split for it: the public half of the settings endpoints, and mailing the
bundle, which now lives on its own router beside the download.

**The caller is a visitor.** `get_current_user` returns a transient user with no
name and the plain role, so every route that judges or renders works unchanged,
and `require_admin` refuses it as it refuses anybody — a belt for the braces of
the admin routes not being there.

**The environment is the whole configuration.** No administrator, no screen, and
no saved settings row is read — a row left by an earlier organisation life of the
same database must not govern a public site. The switches an administrator would
otherwise flip on the screen gained environment names: `ADDRESS_LOOKUP_ENABLED`,
`UN_CARDS_ENABLED`, `CARD_LINKS_ENABLED`, `PUBLIC_URL`, `DEFAULT_LANGUAGE` and
`DEFAULT_THEME`. They work in the organisation application too, as the starting
value a saved setting overrides, which is the rule every other variable follows.
A typo in any of them falls back rather than failing.

**No mail, whatever `SMTP_*` says.** A visitor who can download the papers does
not need the installation to send them, and an installation that sends what
strangers type to addresses strangers choose is a spam relay. Removing the
action removed the guards the roadmap had drafted for it.

**The browser keeps what the account would have.** Consignor, contact, carrier,
loading point, emergency number, language, theme and signature live under one
`localStorage` key and travel only with the shipment being drawn up. The
settings screen says so in four languages, and says that clearing the browser
data clears them.

**The promise is checkable.** `/api/health` reports `"mode"`, the chrome says
"Open installation" where the account name would stand and beside the version,
and [Privacy](docs/privacy.md) gained the section a visitor reads.
`/api/setup-status` reports the mode as well.

Also: `ADMIN_*` is ignored in the open application, with no warning about a
missing administrator; accounts left in the database by an earlier organisation
life are reported at start-up and left alone. `EMCARGO_MODE` set to anything
but the two words runs the organisation application and says so in the log.

## [1.170.2] — 2026-09-04

### Two modes instead of three privacy levels

Documentation only; no behaviour changes. The roadmap's "privacy levels" are
restated as **two modes and one feature**, because the three-step ladder encoded
two questions that are not the same kind of question — who gets in, and what is
kept — and made a stored shipment history sound like a step *down* in privacy
when it is a function an organisation switches on for itself.

- **Open**: anyone, no account, nothing kept about anyone. Defaults live in the
  visitor's browser; no equipment library; **no mail**. An earlier version kept
  mail at Open behind a second switch, per-recipient caps and a spam-relay
  warning. All of it existed to make one feature safe for strangers, and a
  visitor who can download the documents does not need the installation to send
  them — so the feature goes, and the switch, the caps and the warning go with
  it.
- **Organisation**: today's behaviour, named. Signed in; accounts, settings and
  the equipment library kept; nothing about shipments. Unset means Organisation,
  so no existing installation changes.
- **History**, a feature of Organisation: the shipments kept, which unlocks the
  shipments page, departments, the address book, groupage from kept shipments
  and the DGSA report. Still deploy-time, because switching it off destroys data
  and refusing to start is the one honest place to say so.

Two things the ladder did not say and this version does. **The promise has to be
checkable**: a visitor cannot see an environment variable, so an Open
installation says in its footer and its version endpoint which mode it runs in,
and the source is public. And **the two pieces of work are independent**: Open is
removing from today, history is adding to it, and Open can ship with history
never built.

**The groupage line no longer pre-empts the history.** The roadmap, the research
note and three docstrings said a trip "is never stored", settled "by the privacy
levels". What is true is that nothing is stored *today*; whether an installation
that keeps its shipments keeps the judgement over a load as well is recorded as
an open question for that phase. `docs/privacy.md`, `docs/database-plan.md` and
`docs/shipment-export.md` follow the same wording.

## [1.170.1] — 2026-09-04

### A copy glyph beside the sign-in code

The two-factor mail now shows the copy glyph next to the six digits, with one
line underneath saying what to do with it.

**It is a cue, not a button, and that distinction is the whole design.** A mail
client runs no JavaScript and has no clipboard API — Gmail, Outlook and Apple
Mail all strip both — so nothing in an e-mail can copy on a tap. What does put
the code on the clipboard is the reader holding a finger on it, which every
phone mail app supports. So the glyph marks *which* six characters are worth
pressing, and the sentence beside it says to press them: "Houd de code even
ingedrukt om hem te kopiëren", in all four languages. A glyph on its own would
have promised a button that cannot exist.

Three details that are not decoration:

- **The glyph sits in its own table cell**, never inside the code's. Inside it,
  a long press would sweep the image into the selection and the reader would
  paste six digits and a picture.
- **It is a PNG, attached to the message**, because Gmail strips inline `<svg>`
  from mail outright — and attached rather than linked, on the same terms as
  the logo: a linked image makes the reader's client call this server, which is
  a tracking pixel by accident and a broken image on an installation the
  internet cannot reach. A message with no code carries no glyph.
- **The colour is slate 500, deliberately.** Gmail's dark mode inverts the card
  behind the icon but never the icon itself, so a glyph drawn in the text colour
  disappears on exactly the phone this was asked for. Slate 500 holds roughly
  4:1 against the light card and 3:1 against Gmail's dark one — legible on both,
  which for a glyph that only has to be recognised is the right trade.

**The drawing is the application's own**, rendered by
`scripts/render_mail_icons.py` from the same paths as the interface's copy
button, so no third-party licence travels into the mail and the eight credited
Uicons icons stay eight. A test asserts the two drawings cannot drift apart.

## [1.170.0] — 2026-08-26

### The sea's own chapter 3.4, finally read — and the restraint paid out

Since the LQ diamond shipped in v1.165.0, the sea deliberately claimed nothing about it.
The IMDG Code has a chapter 3.4 of its own with its own numbering, the CI reader's
anchor for it landed in the Dangerous Goods List, and answering the sea out of ADR's
book is the mistake column 6 already made once. So the sea answer carried an open point,
`imdg_chapter_3_4_not_read`, and nothing else.

The operator's upload made the chapter readable directly — and it turned out the file
was already in the store: byte-identical to the pinned `imdg_42_24`, which was
thereby verified to carry the complete typeset 2024 edition (Parts 1–7, chapters
3.1–3.5, Appendix A, Appendix B and the index), not the amendment instructions alone.
Chapter 3.4 was read from PDF pages 797–799 on 2026-08-26.

**What the reading found, in both directions:**

- **The package mark is the identical diamond.** IMDG 3.4.5.1 states the same square at
  45°, the same 100 mm minimum and 2 mm line, the same reduction to 50 mm and 1 mm. The
  artwork drawn for the land serves the sea unchanged — but that identity is now a
  finding from reading both texts, recorded in the seed with the pages it came from,
  not an assumption. The sea cites 3.4.5.1 and never the land's number, carries the "Y"
  variant at 3.4.5.2 with the multimodal recognition of 3.4.5.3.1, and adds the
  durability clause the land does not state: readable after open weather exposure.
- **Everything around the mark differs, which is why the waiting was right.** The unit
  mark of 3.4.5.5 turns on **no tonnage at all** — no 12-tonne trigger, no 8-tonne
  dispensation: a cargo transport unit carrying only limited quantities always bears
  the 250 mm mark, durable through three months' immersion in the sea. And where ADR's
  chapter 3.4 lifts the transport document altogether, the sea keeps chapter 5.4
  applicable (3.4.1.2.5) and 3.4.6.1 puts **"LIMITED QUANTITY" or "LTD QTY"** beside
  the description.

**What changed in the application:**

- A sea line within the LQ limits now carries the mark in the package-marking answer,
  under the sea's provision numbers; the open point is gone.
- The LQ check names the sea's two extra duties on every within-limits IMDG line — the
  document words of 3.4.6.1 and the threshold-free unit mark of 3.4.5.5. Named, never
  inserted: whether the consignment actually travels under chapter 3.4 remains the
  consignor's declaration.
- The package label sheet says the sea prescribes the same mark, and names the two
  differences.

### Registered: the IMDG Code Supplement, 2020 edition

Operator-supplied and pinned as `imdg_supplement_2020`. The register is honest about
what the file is: a text-preserving reconstruction in which 138 of the 184 source
images are missing, so it is usable for text and never for figures. **No value in the
repository is read from it yet** — the EmS source of record remains
MSC.1/Circ.1588/Rev.3. The third file in the upload, MSC.1/Circ.1498, was already
pinned as `ctu_circ_1498`.

## [1.169.0] — 2026-08-25

### Groupage: several consignments on one vehicle, judged as one load

Every other screen in EMCargo reasons about a consignment, because a consignment is
what somebody fills in. The ADR does not look at anybody's administration — it looks at
what is physically on the vehicle. Three of its rules are decided per transport unit and
cannot be decided per consignment however carefully each one is completed.

**Open Groupage in the menu**, add the consignments, and the load is judged as a whole.

- **The 1.1.3.6 points.** The finding this exists for, and the one no per-consignment
  screen can produce: two consignments that each stay under the 1000 points can pass it
  together. Each customer is told "exempt", truthfully, and the vehicle is not — and the
  whole load then needs orange plates, an ADR-certified driver and the equipment of
  8.1.5. The screen shows what each consignment said alone beside what they say
  together, because a total without that comparison does not explain what combining
  cost.
- **Mixed loading (7.5.2).** Checked within one consignment since long ago; between two
  consignments from different customers it was checked by nobody. Warnings name the
  consignment as well as the substance, since two customers shipping the same UN number
  otherwise produce two identical labels and "these may not travel together" does not
  say which pallet to take off.
- **The limited-quantities marking (3.4.13/3.4.14).** Both of its conditions are about
  the unit rather than the consignment. See below.

**Consignments come in as the shipment exports** of v1.161.0. That is deliberate: this
application keeps no shipment history, so there is no list to pick from, and inventing
one to make this screen convenient would break the privacy stance the rest of it keeps.
The file the planner already has is the honest input.

**The trip is never stored.** Privacy levels 1 and 2 keep nothing about shipments, so a
trip in the database would break that promise for the sake of a screen. It is assembled
from the request, judged and forgotten: no trip id, no history, nothing to retrieve, and
reloading the page clears it. A test asserts the service touches no database at all, and
another asserts the answer carries no identifier. The roadmap's open design question —
trip as entity or as transient calculation — was settled by the privacy levels rather
than by preference.

### Fixed: three thresholds of 3.4.13/3.4.14 that had been run together

The limited-quantities marking carries *three* separate quantities, and the
consignment-level check had collapsed two of them into one.

| value | what it is | what it does |
|---|---|---|
| 12 t | maximum mass of the **transport unit** | triggers the requirement (3.4.13) |
| 8 t | gross mass of the **LQ packages** | allows it to be dispensed with (3.4.14) |
| orange plates (5.3.2) | a property of the **whole load** | an exception in its own right |

The check compared the LQ gross mass to 8 tonnes and reported that as the 3.4.13
requirement. That attributes the dispensation's threshold to the requirement, and it
dropped the orange-plate exception entirely — which in groupage is the common case: add
one full-ADR consignment and the unit carries plates anyway, and 3.4.13 then does not
ask for the LQ mark at all.

The consignment-level message now states the rule as it reads and says which two
conditions a single consignment cannot settle. The trip check evaluates all three,
because there the application can see the whole load — and asks for the vehicle's
permitted maximum mass, the one fact about the load it cannot derive. Without it the
marking is reported as undecided rather than guessed.

Read from ADR 2025 Volume I, page 665, through the repository's own reading workflow —
not from memory.

### Also

- **A total past the threshold is past it whatever is missing.** The points check reports
  `incomplete` when a line has no quantity, and the trip check used to read that as
  "undecided". Unstated quantities can only add points, so a load already over 1000 is
  over it: a 1500-point load with one blank field no longer comes back undecided.
- `dg_trip` is rate limited at 30 a minute and appears in `test_ratelimit_key`'s one
  table with all the others; it runs one points check per consignment plus one over the
  load, so its cost grows with the vehicle rather than being fixed.

## [1.168.0] — 2026-08-25

### A QR code on documents, and the first door that opens without a key

Every transport document EMCargo renders can now carry a QR code that opens this
installation's UN cards for the UN numbers on that document. It is off until an
administrator turns it on, under **Settings → QR code with UN cards on documents**.

The page behind that code is the only one in the application that does not ask for a
sign-in, and that is the whole point. The people a code on a transport document is for —
the driver at the roadside, the warehouse taking the pallet in, the responder who arrived
because something went wrong — have no account here. A code that asks them to log in is a
code that does nothing.

Because it is public it is the narrowest thing in the application.

- **What the code carries** is the UN numbers and the regime, and nothing else. No
  consignor, no consignee, no quantity, no reference, no shipment identifier — there is no
  shipment to look up, because none is stored. The document the code is printed on already
  carries those same UN numbers in plain text and larger, so the code discloses nothing the
  paper in the reader's hand does not already say.
- **The regime travels with the numbers.** A card is per UN number *and* modality, because
  ADR and IMDG print different obligations. A code on a sea document that opened the road
  card would be answering the wrong question quietly, which is the one failure worse than
  answering none.
- **A missing card is reported missing**, never left out. Somebody standing at a vehicle
  counting cards against the document needs to be told one is absent; a shorter list looks
  exactly like a document with fewer substances on it.
- **It needs an address as well as a switch.** Nothing is printed until the installation's
  public address is configured, and the settings screen says so beside the toggle. The
  address cannot be taken from the request the way a mail link's can — nobody is making a
  request when the driver scans the sheet three days later — and a code on paper that leads
  nowhere is worse than no code, because whoever holds the paper cannot tell the difference.
- **With the switch off the route answers 404, not 403.** An installation that has not
  opened this door does not owe a stranger the information that the door exists.
- **Bounded:** at most thirty UN numbers per link, thirty requests a minute per caller, and
  files served only from the card set an administrator imported.

Nothing here expires. The link addresses a UN number rather than a consignment, so a code
scanned in a year answers what it answered on the day it was printed. That dissolved the
roadmap's open question about link lifetime rather than answering it.

### The printed code is sized from its data, not from the page

A QR is read by its *module*, the single square, and the amount of data is not fixed: one
UN number encodes to a 33-module symbol, thirty need 57. At a fixed printed size the
squares therefore shrink on exactly the documents that carry the most substances — the ones
somebody most needs to scan. The module size is fixed instead and the printed size follows
from it: 25 mm for one UN number, 40 mm for thirty, with the modules holding at 0.62 mm
throughout. Error correction is at level M rather than the library's default L, because a
code that lives in a cab and a warehouse should survive being smudged.

The 0.62 mm is a chosen number and is recorded as one. The published minimums for printed
symbols sit behind specifications this build environment cannot reach, so rather than cite a
figure from memory it is set where a 600 dpi laser puts roughly fifteen dots across a module
— and `docs/roadmap-research.md` lists it as not assessed, with the one constant to correct.

### Fixed

- **An air consignment asked for every regime's cards.** `IATA_DGR` is the profile name the
  wizard actually sends, and it was missing from the profile-to-modality map. An unmapped
  profile does not fall through to nothing there — it falls through to *all five*
  modalities, so an air-only shipment requested road, rail, inland and sea cards as well.

### Also

- A sweep test now lists every route the application serves that answers without a signed-in
  user, so a second public router cannot appear without somebody deciding it should.
- `backend/tests/test_ratelimit_key.py` prints the two new public limits in the same one
  table as all the others.

## [1.167.0] — 2026-08-24

### Return shipments in one click

The drums that just went out come home empty and uncleaned, and the return is the
outward consignment read backwards — the same drums, the same substance, the two parties
the other way round. The export step now turns it round in one button.

- **The parties swap**, with their addresses and contacts. The filler receives what they
  sent.
- **Every line becomes empty uncleaned**, which the document line already understood:
  5.4.1.1.6.1 puts the words after the description, and 5.4.1.1.1 (f) then composes no
  total quantity because these are residues nobody has weighed.
- **Every quantity is cleared** — the ADR total, the net per package and per inner
  packaging, the gross mass, the net explosive mass, the Q values. Not because they are
  stale but because they are *false*: an empty drum does not contain 200 litres, and a
  form that carries the number over invites somebody to sign for it. Copying is the easy
  part of a one-click return; knowing what may not be copied is the work.
- **The number of packages stays.** The same drums come back — that one is not a lie.
- **The declaration and the signature do not come along.** Both were given for the
  outward goods, and carrying them onto a different consignment would put somebody's name
  under something they never saw.

**The turn is the server's, not the browser's**, because what may not be carried over is
a regulatory judgement rather than a copying convenience, and it belongs where it is
tested with the rest of the regulatory code. Nothing is stored: the answer is the same
shape the wizard already holds, and every check then runs on it exactly as on a shipment
somebody typed — including the one this needed first. The same drums are 900 points
outward and **0 on the way back**, and a test asserts that end to end.

Also corrected: the roadmap research note that said this item needed no research. True of
the description, which has been built since v1.90.0; not true of the points, which
v1.166.0 had to fix before the button could stand on them. "No research needed" is a
claim about one half of a feature, and the half it is not about is where the regulation
hides.

## [1.166.0] — 2026-08-24

### An empty drum counted for 900 of the 1000 points

ADR **1.1.3.6.1** reassigns an empty uncleaned packaging: one that contained a transport
category 0 substance stays in category 0, and one that contained anything else becomes
**category 4** — whose factor is 0, so it counts nothing at all towards the thousand. The
two closing lines of the 1.1.3.6.3 table say the same from the other side, and name
UN 2908 as the exception, because that entry is itself an empty packaging and the table
lists it under category 4.

The points check read the substance's own category instead. **One empty drum of a
packing group II liquid came to 900 of the 1000 points** — nearly the whole exemption
budget spent on a drum the regulation counts for nothing. Wrong in the safe direction,
and still wrong: a relief the regulation grants was withheld, and a load went out under
rules it did not have to follow.

- **The reassignment is applied, and named** — a reassigned line reports its category, 0
  points and `1.1.3.6.1` as its basis, so the arithmetic can be checked against the book.
- **A reassigned line needs no quantity.** 5.4.1.1.1 (f) composes none for residues
  nobody has weighed, and factor 0 makes the arithmetic the same whatever it would have
  been. Asking for a number that changes nothing is how a form teaches people to invent
  one.

**And one trap inside the fix.** Category 0's factor is **null**, not zero, and the two
mean opposite things: zero is "counts nothing", null is "no exemption exists at all". The
first version treated them alike, and a drum that had contained a category 0 substance
came back as a possible exemption — the one direction this arithmetic must never be wrong
in. Both cases are now tested, along with UN 2908.

This was found while scoping the roadmap's return-shipment item, whose research note says
"no research needed". That is true of the description — `empty_uncleaned` and the wording
of 5.4.1.1.6.1 have been built since v1.90.0 — and was not true of the points.

## [1.165.0] — 2026-08-24

### The limited quantities diamond

The last mark the package label sheet owed. It belongs to **chapter 3.4**, not 5.2, which
is why chapter 5.2 could be closed in v1.163.0 with this still outstanding.

ADR 3.4.7.1 states nearly all of it: a square set at 45 degrees, the top and bottom
portions and the surrounding line black, the centre white or a suitable contrasting
background, minimum 100 mm by 100 mm, the line at least 2 mm. It leaves exactly one thing
to the drawing — how deep the black portions run — under "where dimensions are not
specified, all features shall be in approximate proportion to those shown".

- **That one number was measured, not chosen.** Figure 3.4.7.1 was cut out of the edition
  and the two black portions came back at 81 and 82 pixels of a 353-pixel height. The
  figure is symmetric, so the two measurements agreeing to a pixel is the check on the
  measurement; the mark is drawn at 0.231 of its height.
- **Drawn, not cut**, for the same reason the battery mark is: the edition wraps the
  figure in "Minimum dimension 100 mm" annotations with leader arrows, and they abut the
  diamond. A mark carrying a caption about its own minimum size is not the mark the
  regulation prescribes.
- **Whether a line travels under chapter 3.4 is not decided twice.** The LQ check already
  tests the line against column 7a and the 30 kg limit of 3.4.2; the marking check calls
  that same function rather than testing the limits again, and a test asserts it does.
  Two readings of one question is how a package comes to carry the mark on one screen and
  not on the other.
- **Named and not applied:** the 250 mm mark of 3.4.15 on the transport unit, because
  3.4.13 turns on 12 tonnes and 3.4.14 on 8 tonnes and both are about the whole load,
  which this check does not see; the 50 mm reduction of 3.4.7.2, a judgement about the
  package in front of the packer; and the "Y" of 3.4.8, which a package *may* bear rather
  than shall. All four are on the sheet, in four languages.

**The sea does not get it.** The IMDG Code has a chapter 3.4 of its own with its own
numbering, and the attempt to read it landed in the Dangerous Goods List instead — the
phrase "Limited quantities" matches in the wrong half of that book. Answering the sea out
of ADR 3.4.7 is exactly the mistake column 6 already made once, so the sea answer carries
`imdg_chapter_3_4_not_read` and claims nothing.

Also here: a crop may now name the volume it was measured in, because chapter 3.4 is in
ADR Volume I while everything cut before it was in Volume II; and the crop finder's
`--pages` said "printed page" while the code has always meant the PDF page, which in
Volume I differ by twenty.

## [1.164.0] — 2026-08-24

### The limits reach the endpoints that cost something

v1.163.4 fixed *how* rate limits are counted. This extends *what* they cover. Until now
six limits guarded signing in and its neighbours, and everything expensive was
unprotected — guarded, in effect, by the login page in front of it. Eight more:

| Endpoint | A minute | Why |
|---|---|---|
| Render one document | 60 | A consignment carries a dozen papers, and correcting a field means going round again |
| The whole bundle | 10 | Every document, the UN cards and the instructions in one archive |
| Mail the bundle | 5 | Lower than building it on purpose — this cost lands on somebody else |
| UN cards | 10 | Generation per set |
| Read a carrier confirmation | 20 | File parsing, and the size of the work is the caller's choice |
| A turn of the assistant | 120 | Inference where a model is installed |
| Ask for the model download | 3 | An administrator's button with a multi-gigabyte fetch behind it |
| Address autocomplete | 60 | Proxies to a Photon instance — the cost falls on somebody else's free service |

- **Every limit in the application is now in one table**, asserted by
  `test_ratelimit_key.py`. Half of them live on their routes in `auth.py` and half are
  named in `core/ratelimit.py`; the test is the one place both halves are visible at
  once, so changing any limit means changing that list.
- **Mailing the bundle is asserted to stay tighter than building it**, as a relation
  rather than two numbers, because the reason outlives any retune.

**The first number for the assistant was wrong, and the test suite said so within the
minute.** It was set at 20 on the reasoning that a conversation goes at the speed
somebody types. But the assistant is a *survey*: it offers every optional field it could
still fill in, and "skip" is one turn each. The archetype test walks eighty of them — and
so does a person who wants none of the optional fields, because clicking skip is far
faster than typing. A limit a real user reaches is a bug report, not a defence, so it is
now 120: beyond any person, still a hard ceiling on a script.

**And the tests needed a `conftest.py`, which this repository did not have.** Under a
`TestClient` every test in the session is the same caller, `testclient`, so the counters
accumulated across the whole run and a test posting one message failed because eleven
earlier tests in other files had posted theirs. The budget is now reset before each test.
Switching the limits off in tests would have been the other way, and would have left the
end-to-end limit tests measuring nothing.

## [1.163.4] — 2026-08-24

### Behind a proxy, everyone was the same caller

The rate limit that guards signing in was keyed on `request.client.host`. Behind a
reverse proxy — which every installation that terminates TLS has — that is the proxy, so
every person arriving through it counted against one budget. **Fifteen colleagues behind
one nginx shared ten sign-in attempts a minute and could lock each other out**, and one
person getting their password wrong spent everybody's allowance.

- **The key is now read from `X-Forwarded-For`**, one entry from the right per proxy in
  the new `TRUSTED_PROXY_COUNT` (default `1`, which is one nginx, Caddy or Traefik in
  front; a CDN above that is `2`). When `TRUSTED_PROXY_HEADERS` is off, the header is
  ignored entirely.
- **From the right, and that is the whole of it.** A proxy *appends* what it saw, so the
  header the application receives is `<what the caller claimed>, <what the proxy saw>`.
  Reading the left of that list is not a smaller version of this fix but a rate limiter
  with a bypass in it: a caller who invents a new value per request gets a new budget per
  request, and one who copies a colleague's address spends theirs. Both directions are
  tested.
- **Misconfiguration degrades to useless, never to open.** Ask for two proxies where only
  one hop is present and the key falls back to the peer address — everyone in one bucket
  again, which is the bug this fixes, but never a key the caller chooses.

**And the fix nearly shipped as a no-op.** There were two `Limiter` instances: one built
in `main.py` and placed on `app.state`, and a second built in `api/routes/auth.py` that
carried all six `@limiter.limit` decorators. Only the second enforced anything. Re-keying
the first changed nothing whatsoever, and a unit test of the key function passes either
way — it was caught by driving a real request through the stack and reading back the key
slowapi puts in its own warning line. There is one limiter now, in
`app/core/ratelimit.py`, imported by both, and a test that sweeps the source so a third
cannot appear quietly. The end-to-end test was run against the old code first, where it
fails exactly as described.

Also documented: `TRUSTED_PROXY_COUNT` in `docs/configuration.md` and `.env.example`,
with what setting it too high and too low each cost.

## [1.163.3] — 2026-08-24

### Mail and rate limiting at the open level

Documentation only; no behaviour changes. Level 1 of the privacy levels decided in
v1.163.2 said "no mailing documents" and left rate limiting as one line. Both were too
short, and reading the code for them turned up something that is not a roadmap item at
all.

- **Configuring a mail server at level 1 needs nothing new.** `SMTP_HOST` and the seven
  values beside it have been environment settings since v1.141.0, added in so many words
  "for installations that would rather configure it in the environment than in the
  screen". At level 1 that stops being an alternative and becomes the only way, because
  there is no settings screen.
- **What does need building is a second switch**, kept deliberately apart from the
  first: `SMTP_*` says whether the installation can send at all, and a separate setting
  says whether someone who never signed in may make it send. Off by default at every
  level. Answering the second question with the first is how an installation becomes a
  spam relay with a good amplification ratio, spending its own domain's reputation.
- **The rate limiter is half-built, and the existing half is the wrong half.** `slowapi`
  is already a dependency and the limiter is already wired up, but all six
  `@limiter.limit` decorators sit on authentication routes — the routes level 1 deletes.
  What costs real money there is unprotected today precisely because a login stands in
  front of it: document generation, the assistant's inference, the Photon proxy, mail.

**And one live defect, found while writing the above.** The limiter is keyed on
`slowapi.util.get_remote_address`, which returns `request.client.host` and never reads
`X-Forwarded-For`. Behind a reverse proxy — which every TLS-terminating deployment has —
every caller collapses into one bucket. That is not only a level 1 concern: **today** an
organisation of fifteen people behind one proxy shares the 10/minute sign-in budget and
the 5/minute password-reset budget, and can lock each other out. `trusted_proxy_headers`
already exists for the scheme and host and is the switch the key function should read.
Recorded here rather than fixed in the same breath, because changing how a security
limit is keyed deserves its own release and its own tests.

## [1.163.2] — 2026-08-24

### The privacy levels, decided

Documentation only; no behaviour changes. The roadmap had "privacy levels" as a single
paragraph with a list of things gated on them, and no statement of what the levels
actually were. They are now three, ordered by what the server knows about you:

| | Who gets in | What the server keeps |
|---|---|---|
| **1 — Open** | Anyone, no account | Nothing about anyone |
| **2 — Closed** | The organisation's people, signed in | Accounts and their settings |
| **3 — Kept** | The organisation's people, signed in | Accounts, settings, and the shipments made |

Level 1 to 2 changes who gets in; level 2 to 3 changes what is kept. **Level 2 is what
EMCargo does today**, so it is the default and the only level reachable without a
migration.

- **The level is an environment variable the application can read and not write.** A
  privacy promise an administrator can click away is not a promise — and level 1, having
  no accounts, has no administrator interface to click it in.
- **Level 1 has no accounts at all**, and three things follow that are consequences
  rather than omissions: what would be filled in for you lives in the visitor's browser
  (the signature included, which is the only image the server ever holds); there is no
  equipment library, because an administrator fills it and there is none; and documents
  cannot be mailed, because an anonymous send endpoint is an open relay. Rate limiting
  becomes load-bearing at this level and nowhere else.
- **Going down a level destroys data, so the application refuses to start.** Moving from
  3 to 2 means the stored shipments have to go — leaving the table while the interface
  denies it exists is worse than either level. There is no screen to confirm on, so
  startup reports how many shipments it found and names the second variable that
  authorises discarding them. Loud, and destroys nothing by default.
- **One combination is refused:** no login *with* a shipment history. The roadmap used to
  describe turning the login page off as the *strictest* setting, for a closed network
  where the network is the boundary. That is the opposite argument — safe because nobody
  untrusted can reach it, rather than safe because nothing is kept — and putting the two
  on one ladder would produce an installation that records what was shipped with no idea
  who typed it. That sentence is gone.

`docs/roadmap-research.md` carries what each level costs to build, traced to the files
already in the tree, and `docs/privacy.md` now says which of the three it is describing.

## [1.163.1] — 2026-08-24

### The material warning was not on the page you print from

The package label sheet prints labels at full size, on the reasoning that a package
label really is printed on adhesive stock in practice — where a placard on a laser
printer is not a placard, which is why chapter 5.3 is deliberately not drawn. That
reasoning holds only as long as the sheet says what the material has to be, and it did
say so: in full, in four languages, naming BS 5609 as the standard the labelling trade
uses to show a material survives ADR 5.2.1.2's open weather and the IMDG Code's three
months in the sea.

It said so on the working page only. The material is not chosen there. It is chosen at
the printer, and the page in hand at that moment is the artwork page — so the one
statement of what the stock has to be sat on a sheet that may never be printed, or that
is set aside before the labels come out.

- **Every page carrying a figure now repeats it in one line** — the label pages, the
  marine pollutant and environmentally hazardous mark, the battery mark and the
  orientation arrows alike. It keeps the two provisions and the standard, which are the
  parts that are of any use, and leaves the full sentence about whose responsibility the
  material is on the working page.
- **It sits above the cut marks, and that is the right place rather than a compromise.**
  The label itself cannot carry it: a label with a sentence printed on it is not the
  label the regulation prescribes. So the warning does its work before the cut — at the
  moment it can still change something — and comes off with the offcut.
- **A test asserts no artwork page is without it**, in all four languages, finding those
  pages by the figure on them rather than by page number, so a working page that one day
  grows onto a second sheet cannot silently narrow what is covered.
- The module docstring claimed the sheet said this "on every copy". It said it once.
  That sentence now says what the code does.

## [1.163.0] — 2026-08-23

### Column 6, read

The last thing chapter 5.2 said it had not done. IMDG 5.2.2.1.2 lets a special provision
in column 6 of the Dangerous Goods List add a subsidiary hazard label where column 4 shows
none and remove one where it does; 5.2.2.1.2.1 lets one drop the labelling altogether for
a substance of a low degree of danger. Until now the sea answer carried a flag saying the
column had not been read.

- **All 262 provision numbers the column cites were found in chapter 3.3.** Forty-two of
  them mention a label, a mark or an exemption, and every one was judged: eighteen bear on
  the labels a package carries, twenty-four name a mark or an exemption while doing
  something else. Both lists are in the seed by number, and a test asserts they account
  for all forty-two — because the difference between a provision that was judged and one
  that was never opened is the whole of what a coverage claim means.
- **One provision is applied, not merely named.** Special provision **384** says in as
  many words that the label is model No. 9A and that only the placard on the cargo
  transport unit is model No. 9. The battery label now comes from the column that assigns
  it, per substance, rather than from the inference across three other provisions that
  v1.161.1 had to make.
- **The other seventeen are named against the entry that cites them**, with the effect
  they would have and whether it applies — because they turn on a competent authority's
  permission, on how much phlegmatizer a mixture holds, on whether an article is
  water-activated, on which packing instruction was used. A packer who can see the drum
  can finish those sentences. This application cannot, and removing a label on a condition
  nobody checked is the failure the whole module is arranged against.
- **The package label sheet says it too**, in four languages, for every sea consignment
  whose entries cite something that touches labelling.

**The reading took three wrong parsers.** The first found the chapter heading in the table
of contents and cut six "provisions" out of the front matter. The second read the page as
a stream of lines, which returns the number column as one block, so provision 199 swallowed
forty of its neighbours. The third measured the numbers' position — and found 140 of 262,
with no complaint about ordering, because the half it read was internally perfect. The
chapter is printed with **mirrored margins**: the numbers sit at x=125 on one side of the
spread and x=96 on the other. That the two positions account for exactly 262 between them
is what gave it away.

**And one fault in this repository, not in the Code.** Both books have a column 6 and they
are different sets of numbers — UN 3480 carries special provision 384 in the Code and does
not in Table A. The first version of the check read Table A to answer the sea question:
the exact mistake this module was built to avoid, and one that would have left no trace,
because the numbers look plausible either way. The two readers are now named for the book
they come from.

Nothing on chapter 5.2 is left open.

## [1.162.0] — 2026-08-23

### The two figures nobody had measured

The package label sheet named the battery mark and the orientation arrows instead of
printing them, because their artwork had never been cut from the official edition the way
the twenty-three class label models were. Both are now measured, and the sheet prints
them.

- **The orientation arrows** are cut whole. The page prints them twice, identical apart
  from a rectangular border 5.2.1.10.1 calls optional, under two captions set side by side
  on one line — so shape cannot tell them apart, and the captions were matched to the
  drawings by their own horizontal position. The framed one is Figure 5.2.1.10.1.2, and
  that is what is cut. The provision gives them **no size at all**, only "clearly visible
  commensurate with the size of the package", so the size on the page is named there as
  this sheet's choice and not as a requirement — together with the four cases of
  5.2.1.10.1 that call for them, the six exceptions of 5.2.1.10.2 and the prohibition of
  5.2.1.10.3.
- **The battery mark** is cut down to its symbol. Its printed figure is wrapped in
  dimension annotations that abut the hatched edging, and everything except the symbol is
  stated in 5.2.1.9.2 in words: a rectangle 100 mm by 100 mm, red hatched edging at least
  5 mm wide, the symbol above the UN number or numbers. So the frame is built from those
  numbers and the symbol is the edition's own — which also fixes what printing the figure
  verbatim would have got wrong. The figure carries an asterisk where the number goes, and
  an asterisk on a package says nothing; the sheet prints the number of the cells inside.
- **The environmentally hazardous substance mark and the marine pollutant mark** are now
  printed as well. The sheet could already tell you a line needed one; it kept the figure
  it holds to itself.

**One bug found on the way, and it was the interesting one.** The detector that finds a
figure on a rendered page thresholded the **red** channel and called anything above it
paper. Red ink has a high red value, so the battery mark — whose edging is hatched in red
— was invisible to a detector pointed straight at it, and so would have been anything else
printed in colour. For a chapter about coloured labels that is the whole subject.

**And a size that was quietly a fraction short.** The artwork files are trimmed to their
ink and are not all exactly square. Fitting one inside a 141.42 mm box puts the other
direction under it, and the environmentally hazardous mark was printing at 99.8 mm on a
side where the minimum is 100. The scale now comes from the smaller side, so no direction
ends up under the minimum.

One open point remains on this chapter: **column 6** of the Dangerous Goods List, which
can add a subsidiary label where column 4 shows none and remove one where it does. It
deserves its own phase.

## [1.161.1] — 2026-08-23

### Three of the four open points were a read away

v1.160.0 recorded four things about chapter 5.2 as unanswered. Three of them did not need
anybody to supply anything: the IMDG Code is in the regulatory store and had been read
from all session. Asking instead of looking was the mistake, and this corrects it.

- **The IMDG Code places the lithium battery mark at 5.2.1.10** — where the land
  regulations put the orientation arrows. The sharpest illustration yet of why an IMDG
  rule may never be cited by an ADR number.
- **It asks for the three months' immersion twice**: at 5.2.1.2 for marks, and at
  **5.2.2.2.1.7** for labels. The sheet's note now cites both.
- **Special provision 188** names model No. 9A alongside that mark, and carries
  exemptions of its own — button cells installed in equipment, and no more than four
  cells or two batteries in equipment where the consignment holds at most two packages —
  plus an overpack rule keeping the mark visible or reproduced, with "OVERPACK" in
  lettering of at least 12 mm.

**And the sheet now says what a compliant label is made of.** Every copy names **BS
5609**, the British Standard for pressure-sensitive labels for marine use, by which the
labelling trade demonstrates a material survives the IMDG Code's three months in the sea.
Telling a packer that paper will not do, without saying what will, is half an answer.

What stays open is genuinely open: IMDG 2.10.2.7, which three read runs have not
surfaced; which of model 9 and model 9A the Dangerous Goods List intends per class 9
entry, since the specimen table row that assigns them has not been read; the remaining
column 6 provisions; and the artwork for the battery mark and the orientation arrows,
which has to be cut from the edition rather than drawn.

## [1.161.0] — 2026-08-23

### A shipment can leave as data

Every exporter in this application produced paper. This one produces the shipment: what
was filled in, what is carried, and — the part that makes it more than a form dump —
**what EMCargo worked out**. Offered on every transport mode as *Structured shipment
export (JSON)*, documented in [Shipment export](docs/shipment-export.md).

The EU eFTI Regulation applies in full from **9 July 2027**, from when authorities must
accept freight information electronically through certified platforms. EMCargo is not
going to become one — that is a certification regime for platform providers, and this is
a documentation tool. What it can be is trivially connectable to one, and that starts
with a shipment being able to leave at all.

**The derived findings travel with the declaration**, and that is the point. A reader
that receives only the typed fields has to compute its own regulatory assessment, and
that is where two systems begin to disagree about one consignment. So the file carries
the whole compliance answer — the 1.1.3.6 points, the mixed loading, the placarding, the
package marking of chapter 5.2, the segregation — **including the editions each was
computed against**. A shipment exported under ADR 2025 can therefore be told apart from
the same shipment re-derived under a later edition, because the file says which book
answered.

**It invents nothing.** A field the user never touched is absent rather than an empty
string: the wizard writes one into every field it renders, so exporting them would fill
the file with keys that mean "untouched" while reading as answers. A zero and a `false`
stay, because somebody chose those. No regulatory profile means no assessment rather than
a guessed regime. And the file carries no user and no installation — it describes a
consignment, not who typed it.

**And it says what it is not**, in its own first key. Not an eFTI message, not an eCMR,
and not a mapping onto UN/CEFACT: naming a field as though it were the standard's while
it carries something subtly different is the failure that makes an integration silently
wrong. The four things that mapping needs first are written down rather than guessed at.

### Fixed

- The document export route named every produced file a PDF, in both the filename and
  the media type. A JSON file served as `application/pdf` is one the browser will not
  open, so the type now follows the file — with a test that the documents which do
  produce a PDF still do.

## [1.160.0] — 2026-08-23

### Chapter 5.2: what goes on the package

Chapter 5.3 — what goes on the outside of the vehicle, wagon, vessel or container — has
been derived per mode since v1.53.0. Chapter 5.2 is the other half and had nothing: the
application knew which labels a substance carries, because column (5) of Table A is read
for eight other purposes, but nobody had asked it what the person taping the drum shut has
to stick on it.

Four editions were read on a runner before a line was written, and the sea turned out not
to be the land renumbered:

- the **IMDG Code marks the proper shipping name on every package** (5.2.1.1), where ADR,
  RID and ADN ask for it on Class 1 (5.2.1.5) and radioactive material (5.2.1.7.2) only;
- it calls the environmentally hazardous substance mark the **marine pollutant mark** and
  places it at 5.2.1.6, not 5.2.1.8, and its numbering diverges from 5.2.1.5 onwards, so
  no IMDG rule may be cited by an ADR number;
- its labels come from **two columns** — the primary from column 3 of the Dangerous Goods
  List, each subsidiary from column 4 — where Table A has one;
- its durability rule is **three months' immersion in the sea**, against ADR's open
  weather exposure.

RID and ADN were quoted beside the ADR in the same run and are identical word for word.

**The sheet.** A working page listing what each package carries per regime and under which
provision, then the class labels themselves at full size: 100 mm on each side, 141.4 mm
from point to point, one per A4 page with corner cut marks and a caption naming the model
and the goods line. The artwork is the official one, cut from the ADR; nothing is redrawn.
Divisions 1.1 to 1.3 print as model 1, which is what the regulation prints for all three,
with the division and compatibility group in the caption. It requires no typed field, so
it can be printed at the packing bench before the paperwork is complete.

**What it refuses to say.** The orientation arrows (5.2.1.10) turn on the kind of
packaging, which the application cannot see, so they are reported as not assessed with the
provision's own four cases named. The marine pollutant exemption routes out to IMDG
2.10.2.7, which has not been read, so nothing is exempted. Column 6 of the Dangerous Goods
List can add and remove subsidiary labels and has not been read per substance. The sea
battery label is left open, because column 3 gives plain 9 for UN 3480 while IMDG
5.2.2.2.1.3 describes a model 9A with a layout of its own, and a 9 printed over a 9A is a
wrong label rather than a missing one. The battery mark and the orientation arrows are
named and not drawn, their artwork never having been cut from the edition. Air is absent:
the IATA marking rules have not been read.

**And what paper cannot promise**, on every copy: 5.2.1.2 wants a mark that withstands the
weather, and the IMDG Code one still identifiable after three months in the sea. The sheet
gives the right content at the right size; the material stays the user's responsibility.

One value had to be settled outside the regulation. "100 mm x 100 mm" for a square set at
45 degrees leaves two readings that differ by root two, and measuring the official figure
did not decide it — the ADR draws the prescribed 5 mm inner line at 0.51 pt on a 96.89 pt
side, which is the stroke width of the outline, so the drawing is schematic there. 49 CFR
172.407(c)(1) prescribes the identical shape, the identical 100 mm and the identical 5 mm
border measured from the outside edge, and says "on each side".

## [1.159.0] — 2026-08-22

### Fixed

- **A selected option is readable again in the dark theme.** Choosing "replace
  the current lines" in the import dialog, a theme in the settings, or an
  answer in the assistant turned the option near-white with near-white text on
  it — the one option you had picked was the one you could not read.

  The cause was not in any of those screens. The brand colour defined five
  shades and the interface used eleven, and Tailwind generates nothing at all
  for a shade that does not exist. Twenty-nine classes across ten files were
  therefore doing nothing, and the ones that mattered most were the dark-theme
  backgrounds: a selected option carried a light background for the light
  theme and a dark one to override it in the dark theme, and the override
  never existed. The palette is now complete, so selected options take the
  deep blue they were always meant to have. The five original shades are
  untouched, so nothing that already rendered changes colour.

### Added

- **A warning kind of notification**, amber and staying until it is closed —
  for something that is wrong and stays wrong until somebody acts, as opposed
  to something that failed. The reminder for an account that does not meet
  the installation's two-factor policy now uses it.

### Changed

- The goods cards keep their measured width on a wide screen, now confirmed
  rather than provisional.

## [1.158.1] — 2026-08-22

### Changed

- **The close button of a notification is back in its corner.** v1.157.1
  centred it along with the icon; only the icon needed it. The kind icon still
  sits against the whole message, and the close button stays top right however
  tall the toast grows.
- **The import and assistant buttons lost their frames.** Two boxes drawn
  around single icons where hover and, for the assistant, its own fill already
  say what they are. The assistant's open state keeps its brand colour and
  background, which is what carried that signal.

## [1.158.0] — 2026-08-22

### Added

- **The two-factor reminder is firmer where the installation requires it.**
  Where an administrator has set the policy to demand a second factor and the
  account does not have one, the snackbar now says so — that the installation
  requires it, and to set it up while signing in is still possible — instead
  of the general recommendation. A policy an account does not meet is a
  different thing to be told than advice not taken. Everything else about the
  reminder is unchanged: it stays until closed, never blocks the screen, and
  returns at the next sign-in.

## [1.157.1] — 2026-08-22

### Changed

- **A notification's icon is centred against its message.** It sat against the
  first line, which showed as soon as a message wrapped to two — an error
  hanging its exclamation mark up in the corner. The close button and a
  single action button follow it, since one of the three sitting high while
  the others centre reads as a fault rather than a choice.

## [1.157.0] — 2026-08-22

### Fixed

- **The import button no longer costs a band of screen on a phone.** It sat
  below the heading and its description, pushed to the right on its own row,
  which left an empty strip above the first goods line — on the screen where
  space is scarcest. It now sits on the heading's own line at every width, and
  carries its name rather than only an icon: the sentence underneath points at
  it by that name, and a phone has no hover to reveal a title.
- **A recognised substance is asked about again after a replacing import.**
  Importing with "replace" numbers the lines from 1 again, and the guard that
  stops a second snackbar for the same question remembered the line number and
  substance for good. A new consignment whose first line held the same
  substance as one already answered was therefore never asked about — the
  quiet kind of failure this step exists to prevent. The guard now remembers
  only questions that are still open.
- **Errors from the goods import now surface as toasts**, like every other
  transient failure since v1.153.0. They were still inline paragraphs inside
  the dialog: the sweep matched on the name of the state it replaced and this
  one was called something else, so a failing template download or an
  unreadable spreadsheet reported itself in the old visual language.

### Changed

- The import and assistant icons are drawn glyphs from the same set as the
  notification icons, replacing two hand-drawn ones. The goods step and the
  equipment library had each drawn their own import icon; they now share one.
  The close buttons of both import dialogs use the set's cross as well.
- The credit on the Legal page now names what it covers — notifications,
  importing and the assistant — since the set is no longer only in toasts.

## [1.156.1] — 2026-08-22

### Added

- **The icon set is credited on the Legal page.** The notification icons are
  Uicons by Flaticon, free to use on the condition that the maker is named.
  The credit is now in the application itself, with the required link, rather
  than only in a repository file — a condition met where nobody using the
  application will ever read it is not met. [Data
  sources](docs/data-sources.md) records the same, with the one qualification
  worth stating: the spinner's origin is confirmed, the other five arrived in
  the same delivery and are recorded under the same set, and if any turns out
  to come from a different pack its author's line has to be added beside this
  one.

## [1.156.0] — 2026-08-22

### Added

- **A reminder to switch on two-factor authentication.** Signing in to an
  account that has no second factor now raises a snackbar saying so, with a
  button that opens the setting. A password on its own is one leaked reuse
  away from somebody else drawing up consignment papers in your name, and
  until now nothing in the application ever said that to the person it
  concerns.

  It is deliberately mild: it stays until it is closed rather than sliding
  away — an action that disappears after four seconds is a button nobody
  clicks — but it never blocks the screen, and "not now" costs one click. It
  returns at the next sign-in rather than on every page load, so refreshing
  mid-work does not renew it and nobody is trained to dismiss it unread.
  Nothing is shown when the status cannot be fetched: a backend that will not
  answer is not evidence that an account is unprotected.

### Changed

- **The settings remember which tab you are on, in the address.**
  `/settings?tab=details` opens that group directly, which is what lets the
  reminder above land on the two-factor panel instead of on the theme
  settings with the panel three tabs away. Switching tabs updates the address
  without filling the back button, an unknown tab falls back to the first one,
  and an administrator tab reached by hand-typing still does not open for a
  plain user.

## [1.155.1] — 2026-08-22

### Changed

- **The notifications have proper icons.** The five kinds of toast and the
  close button drew plain text characters — a ✓, an ℹ, a bare `!` and `?` and
  an ellipsis — which read as punctuation rather than as signs and sat at
  whatever weight the font felt like. They are now drawn SVGs: a check, an
  exclamation and an i in a circle, a question in a speech bubble, an open arc
  that actually spins while something is loading, and a cross in a circle to
  close. Each inherits the toast's own colour, so they stay legible in both
  themes, and their size comes from the interface rather than from the file.
  Recorded in [Data sources](docs/data-sources.md), where their licence terms
  are noted as an open item.

## [1.155.0] — 2026-08-22

### Changed

- **The dangerous-goods name recognition is now a snackbar with an accept
  button.** Typing "benzine" still recognises UN 1203, but the question is no
  longer a block on the goods card — it is asked where the application asks
  everything else. The snackbar names the line and the substance and offers
  the answer as a button; where the name matches several UN numbers (two
  sulphuric acids differing only in their qualifier) it offers a button per
  number, up to three. It never dismisses itself, because four seconds is not
  an answer, and closing it with the × *is* an answer — the same final "not
  this line" the reject chip used to mean. The goods card is now purely a
  summary.
- **An import that went cleanly is a toast, not a report.** Importing an
  equipment file with nothing skipped and no row errors now confirms with
  "3 created, 2 updated" and closes the dialog. The report stays in the dialog
  exactly when it earns the space: a skipped row or a row error is something
  to read through rather than something to notice in passing.
- Toasts can carry more than one action button, and a question puts its
  answers under its text so several UN numbers do not squeeze the sentence
  asking about them.
- **A crowded stack now drops the passing notes first.** With more than five
  toasts on screen, transient confirmations give way before anything that
  stays on purpose — a question waiting for an answer, or a notice meant to be
  read. Previously the oldest went regardless, so "settings saved" could push
  out a substance recognition nobody had answered yet.

## [1.154.0] — 2026-08-22

### Changed

- **The goods step is one shape now: cards, on every screen.** The desktop
  table is gone. It was a table you *typed* in — thirteen columns of input
  fields — and everything built around it existed to fight its width: columns
  weighed against the available space and dropped when they did not fit, a
  minimum width so the fields would not be squeezed to thirty pixels, a
  detail panel to reach what had been dropped. All of that machinery is
  removed with the table.
- **A line is shown, not typed, on the card.** The card carries read-only
  values — what you scan by stays visible, the rest opens with "show more",
  exactly as it already did on a phone. That is what makes one layout work at
  every width: text reflows, a row of input fields cannot.
- **Editing happens in a dialog**, opened with a new pencil icon beside the
  duplicate and delete icons. Every field of the line sits in it, one per row,
  at the same width on a phone and on a monitor. Changes apply as you make
  them, as they did in the table, so the dialog closes rather than saves.
- Length, width and height now read as one measurement — "200 × 80 × 40 cm",
  or "200 × ⌀ 80 cm" for a round cross-section — instead of three cells that a
  table needed but a reader does not.
- The dangerous-goods name suggestion stays on the card itself, visible
  whether the card is open or closed. It is the one thing on a line that asks
  the user a question, and a substance recognised but never confirmed is what
  this step exists to catch.

### Fixed

- **A number field now hands you its number when you click it.** Every field
  with a figure in it — quantities, dimensions, weights, session lifetime,
  port numbers — put the caret next to the existing value and left it there,
  so replacing a 1 with a 12 meant typing the new number and then going back
  to delete the old one. Clicking a number field now selects what is in it, so
  the first keystroke replaces it. Clicking a second time still places the
  caret, for changing a single digit, and drag-selecting still works.

## [1.153.0] — 2026-08-22

### Added

- **One notification mechanism: toasts.** A self-built toast system (no new
  dependency) replaces the transient half of the application's 87 inline
  notices, its four native `confirm()` popups and the hand-built update
  notice. Success and info toasts dismiss themselves after four seconds;
  errors stay until closed, because a missed network error is a document that
  silently never went out; a loading toast follows a slow action — mailing
  the documents, sending a test mail, applying an update — from "working" to
  its outcome in a single toast. On desktop the toasts stack bottom-right; on
  a phone they land as a full-width snackbar at the bottom. Errors announce
  assertively to screen readers, everything else politely.
- **Undo instead of "are you sure?".** Deleting a user, deleting a piece of
  equipment and removing the installed UN card set no longer ask first — they
  act immediately in the interface and hold the real API call for six
  seconds behind an Undo button. Undo within the window means the call never
  happens, which is why an undone user keeps their password: nothing was
  deleted yet. Closing the toast, its timer running out, or being pushed out
  by newer toasts all let the deferred call fire — a delete the user asked
  for must not be cancelled silently.
- **The application's own confirmation dialog** for the two actions that stay
  deliberate: clearing somebody's two-factor verification (a security action
  deserves a step before, not a regret window after) and applying an update
  (it restarts the application under everyone using it). Translated, themed,
  focus on the safe choice, Escape cancels — where the browser's native
  `confirm()` was none of those.

### Changed

- "Settings saved", the mail-server test result, the invite outcome and the
  other transient confirmations moved from inline paragraphs into toasts.
  What deliberately stays inline: field validation at the field, sign-in and
  password-reset errors on their forms, the assistant's clarification
  questions in its conversation, the equipment import report (counts and
  per-row errors are something to read, not a passing note), and every
  regulatory compliance finding — a safety warning must not slide away.
- The update-available notice for administrators now rides the toast system
  as a sticky info toast, keeping its behaviour: shown once per release,
  dismissing it remembers that version, and only an explicit dismissal
  counts — being pushed out by other toasts does not mark it as seen.

## [1.152.4] — 2026-08-22

### Added

- **Groundwork for every roadmap item, written down before any plan.** A new
  [Roadmap research](docs/roadmap-research.md) document records, per subject,
  what the market does, what the regulation says — measured where it could be —
  what already exists in this repository, and which questions a future plan has
  to answer. Highlights of what the research turned up:

  - the package-mark sizes of chapter 5.2 were read from ADR 2025 itself
    (labels 100 × 100 mm, the LQ diamond reducible to 50 × 50, orientation
    arrows with their measured exemption list), so the label-sheet idea starts
    from the text and not from memory;
  - the EU eFTI regulation applies in full on 9 July 2027 and builds on the
    UN/CEFACT multimodal data model — the anchor a structured shipment export
    should map to;
  - self-hostable route engines (openrouteservice, GraphHopper) already
    evaluate ADR tunnel categories from OpenStreetMap, with the honest caveat
    that hazmat tagging is sparse and coverage must be measured first;
  - open-source truck-loading solvers exist with axle-load support (xflp),
    and no commercial load planner does segregation — which is exactly what
    EMCargo could add to the 3D module;
  - HACS (Home Assistant Community Store) is the model for the community hub:
    an index of authors' own repositories, not a file host, with admin-only
    install;
  - IATA's DG AutoCheck Connect API is a second, legitimate route to the air
    unlock — validation by IATA's own service instead of unobtainable tables;
  - Apache 2.0 already permits everything the plugin ecosystem needs, and
    carries a patent grant MIT lacks — worth knowing before switching.

  The roadmap gained a "Documents and data" section for the newly researched
  items (package marks, structured export, DGSA annual report, own articles,
  EDI, groupage, returns, QR codes), each pointing at its research brief.

## [1.152.3] — 2026-08-22

### Fixed

- **The documentation says what the application does.** Every markdown file was
  checked against the running version. Three of them still told the reader that
  sea was locked, which stopped being true in v1.152.0 — the README, the
  documents guide and the user guide. The sea row in the per-mode document
  table gained the IMDG placarding sheet it has offered since v1.150.0.

- **Two documents still called the IMDG Code unreadable.** The coverage
  assessment listed sea among the modes whose text had not been read, and the
  data sources page named the Code alongside the IATA DGR as paywalled. The
  consolidated volumes are indeed sold, but the freely distributed resolution
  that adopts Amendment 42-24 prints the complete text — which is how the
  Dangerous Goods List was extracted in v1.48.0 and chapter 5.3 in v1.150.0.
  Both now say so, and air is named as the one regime that genuinely cannot be
  read. The December 2025 corrigenda and MSC.1/Circ.1498 were added to the
  source table.

### Added

- **The user guide covers the account and mail features.** Two-step
  verification, recovery codes, forgotten passwords, mailing the documents from
  the export screen, and — for administrators — the mail server, the two-step
  policy and the users page. All of it has shipped since v1.141.0 and none of it
  was in the guide; only `configuration.md` described it, which is the wrong
  place for someone trying to switch on two-step verification.

- **The dangerous goods guide explains what certain classes add to the
  document**, with the table of which field is asked in which situation, and a
  link to the fields audit — which until now was reachable only from a
  changelog entry. The audit is listed in the README's documentation table too.

## [1.152.2] — 2026-08-22

### Changed

- **The roadmap plans installing EMCargo without Docker.** It ships as a
  container and assumes one; that stays the default and the tested path, but it
  is currently also the only way in. Planned: a native installation on common
  Linux distributions with a systemd unit, and Helm charts or manifests for
  Kubernetes. The entry names the consequence up front — the in-app updater
  replaces the running container over the Docker socket, a mechanism a native
  install does not have, so each installation method needs its own update route
  and the settings screen should explain the one that applies rather than offer
  a button that cannot work.

## [1.152.1] — 2026-08-22

### Changed

- **The roadmap says where the project is going, and where it now is.** Sea is
  released, so it no longer appears under the locked modes; the update
  experience section described three things that shipped in v1.125.0, v1.126.0
  and v1.133.0 and is gone. The status table gained the users-and-mail work and
  the sea placarding sheet.

  Added from the maintainer's own notes: two more companion modules (container
  fleet management, vessel design) beside the route planner, 3D container
  handling and the military module; privacy levels per installation and what
  they unlock (a shipments page with filters and an edit route back into the
  wizard, departments, turning the login page off on a closed network, an
  address book and templates); one notification mechanism — toasts and
  snackbars — instead of the current mix; admin-set branding including the
  transport-mode images; and a plugin page, a licence change and a community
  hub where plugins are shared and install straight into the application.

## [1.152.0] — 2026-08-22

### Added

- **Sea transport is off the modality lock.** It joins road, rail and inland
  waterway over the same bar: the checks come out of the IMDG Code itself, and
  the flow is verified end to end rather than by hand once. What was missing
  was never the substance data — the Dangerous Goods List has been read since
  v1.48.0 — but chapter 5.3, which arrived in v1.150.0, and the end-to-end
  verification that unlocked rail in v1.122.0.

  Writing those sea archetypes found two things a live test would otherwise
  have found, at the cost of a real consignment each:

  - **The 24-hour emergency number went nowhere.** IMDG 5.4.1.5.11 asks for
    it, and the application asked the user for it — and then had no field for
    it on the IMO form or the B/L instruction, so it was collected and
    silently dropped. It is now on both.
  - **The container number had two names.** The IMO form called it
    `container_identification` while the VGM and the B/L instruction called it
    `container_number`: the same box, typed twice, on one consignment. They
    agree now, and a test pins it, because the next sea document added is the
    one that would drift again.

  What sea still cannot do is on the screen rather than hidden: the stowage
  category is shown and not enforced, segregation from foodstuffs is raised to
  verify because the application cannot see what else is in the container, and
  nothing about the ship is claimed. Air stays locked — the IATA quantity
  tables are still not held.

- **A container can be named on every mode that carries one.** A container of
  dangerous goods rarely travels one leg: it is packed inland, trucked to the
  terminal, put on a barge or a wagon and then on a ship, and the box number
  identifies the load throughout while the vehicle under it changes at every
  handover. Only rail and sea had anywhere to write it. A CMR for a container
  had no box number and no seal, and neither did the ADN transport document —
  so the number lived in the operator's head, which is where a consignment
  note exists to take it out of. Both now carry a container number and seal
  numbers, and a test holds all four modes to it.

## [1.151.0] — 2026-08-21

### Added

- **The statements chapter 5.4.1.2 asks for are fields now, not advice.**
  Before a real consignment was ever put through the application, chapter
  5.4.1 was audited as a whole against the fields it holds — the result is
  [docs/document-fields-audit.md](docs/document-fields-audit.md), which marks
  every provision as held, guidance only, or absent.

  "Guidance only" was the category worth finding. The compliance panel told a
  consignor to state the control and emergency temperature, to name a
  responsible person for class 6.2, to give the end of the holding time for a
  refrigerated gas — and then printed a document without any of it, because
  there was nowhere to answer. Being told about a gap by a program that
  produces a document looking complete is worse than silence.

  Six fields close it: `control_temperature` and `emergency_temperature`
  (5.4.1.2.3.1), `end_of_holding_time` (5.4.1.2.2 (d)), `specific_gas_name`
  for UN 1012 (5.4.1.2.2 (e)), `responsible_person` (5.4.1.2.4) and
  `firework_classification` (5.4.1.2.1 (g)). Each is asked **only in the
  situation its provision describes** — an ordinary drum of petrol gains no
  questions at all — and which situation that is comes from the Dangerous
  Goods List rather than a guess: the entries needing temperature control say
  "TEMPERATURE CONTROLLED" in the proper shipping name, refrigerated
  liquefied gases say "REFRIGERATED LIQUID". Each prints in the provision's
  own words, in the document's language.

  An unanswered field leaves nothing behind. 5.4.1.2.3.1 prints one sentence
  carrying both temperatures, so one without the other is suppressed entirely
  rather than rendered as "Control temperature: -10 °C Emergency temperature:
  °C" — which looks answered.

- **The elevated temperature mark on the inland waterway (ADN 5.3.3).** It was
  the one part of ADN chapter 5.3 left underived, because it turns on a
  temperature nothing in the consignment implied. The carriage temperature
  added in v1.150.0 is that temperature, so 5.3.3 is answered from it, read
  in the English edition on printed page 319: the same 100 °C and 240 °C
  thresholds as at sea, but ADN's own placement — wagons on both sides,
  vehicles on both sides and at the rear, containers and tanks on both sides
  and at each end.

### Fixed

- **A claim in the ADN placarding check is no longer true and no longer made.**
  It said the elevated temperature mark was deliberately not derived because
  the carriage temperature was something "nobody tells the application". That
  was accurate when written and stopped being accurate the moment the field
  existed.

## [1.150.0] — 2026-08-21

### Added

- **Sea placarding: what the container shows on the outside (IMDG 5.3).** Road,
  rail and inland waterway have had their chapter 5.3 derived for several
  releases; sea had none, on the belief that the Code was unavailable. It is
  not — resolution MSC.556(108) replaces the complete text of the Code — so
  chapter 5.3 was quoted verbatim from it and derived under its own rules.

  Those rules are not the road's renumbered, and reusing the road answer would
  have been wrong in five separate ways. A freight container is placarded on
  **each side and each end**, not two sides. The **proper shipping name** is
  marked on the unit itself, which no land regime asks for. The **UN number**
  rides inside the placard or on an orange panel beside it — never on an
  orange plate of its own — and only in the five cases of 5.3.2.1.1, never for
  class 1. **Class 9 is placarded as model No. 9**, while table A gives 9A for
  exactly the lithium and sodium battery entries most likely to travel in a
  container. And the **marine pollutant mark** has no land counterpart at all.

  Also derived: 1.4S carrying no placard at any quantity, class 1 aggregated to
  the highest division, the subsidiary placards of 5.3.1.1.3, the placement
  rule per kind of unit (the kind being something the application cannot see),
  the 4,000 kg arithmetic of 5.3.2.1.1.2, and the removal of everything once
  the goods and their residues are discharged. It reaches paper as the IMDG
  placarding sheet, beside the ADR, ADN and RID ones.

- **Carriage temperature as a field.** The elevated temperature mark turns on
  the temperature the goods are offered at — 100 °C liquid, 240 °C solid — and
  nothing else in a consignment implies it: MOLTEN says the substance travels
  liquid, not how hot, and a substance that is not molten can still be loaded
  hot. Left empty, the check reports the mark as unassessed rather than as not
  required, because a missing triangle on a hot tank is not a detail.

### Changed

- **The coverage assessment is true again**, and one of its entries was simply
  wrong. It listed the IMDG Code's own text under "not worth building, or not
  buildable here" because the consolidated Code is sold by the IMO. But the
  freely distributed resolution that adopts Amendment 42-24 prints the complete
  text, so the Code has been readable all along — which is how the Dangerous
  Goods List was extracted in v1.48.0 and chapter 5.3 now. The entry says so,
  and the document is maintained up to this release rather than to v1.128.0.

## [1.149.0] — 2026-08-21

### Added

- **The December 2025 IMDG corrigenda are registered and verified.** The
  operator's shared Drive folder gained an `Imdg` subfolder with three PDFs.
  One turned out to be byte-identical to the already-pinned resolution
  MSC.556(108) (Amendment 42-24), which independently confirms that pin.
  The second is the IMO's errata and corrigenda of December 2025 to that
  amendment: its full text was read and checked against every extracted sea
  seed, and none of its eleven corrections touches a value the extraction
  carries — they correct prose, cross-references, an alphabetical order in
  IBC520, an entry name in T50 and three special-provision texts, all
  outside the columns that were read. The third, MSC.1/Circ.1498
  (informative CTU-packing material), is registered for provenance and
  marked as deciding nothing. Both new documents are pinned by hash in the
  source register.
- **The fetch workflow can survey and read incoming documents.** A Drive
  take-in now reports what every incoming PDF *is* — identity hash, page
  count, text layer, and where its readable parts sit — before anything is
  registered, and a `dump_text` input prints short documents (such as a
  three-page corrigenda) in full, with a page cap so a book cannot be
  poured into a log by accident.

### Fixed

- **Files in Drive subfolders are recognised again.** Adoption walked only
  the top of the incoming directory, so a Drive folder containing
  subfolders left those files invisible; it now walks the whole tree.

## [1.148.0] — 2026-08-21

### Fixed

- **Mail now fits a phone.** The messages carried no viewport line, so a
  mail client laid them out in a desktop-width container — Gmail on Android
  assumes about 980 pixels — and showed the phone a slice of that. Measured
  in a 980-pixel container the card sits centred starting at x=210: a wide
  empty margin on the left and the card running off the right, which is
  exactly what an invitation looked like on the phone that reported it.
  Every message now declares `width=device-width`.

  Three other things were brought to the way mail is normally built, and are
  named for what they are: not the cause, but what keeps a message looking
  the same in Outlook, Apple Mail and Gmail alike. The gutter is a table
  cell rather than padding on `<body>`, which Gmail drops; the card is
  centred by `align="center"` as well as `max-width`, because Word ignores
  `margin:0 auto`; and a long reset link may break anywhere, so a
  60-character token cannot set a minimum width for the whole message.

## [1.147.0] — 2026-08-21

Three things a real installation ran into.

### Fixed

- **A used link says so on arrival.** An invitation or reset link that had
  already been spent looked exactly like a fresh one: you thought up a
  password, typed it twice, pressed the button, and only then learnt you
  were too late. The page now checks the link before drawing the form. It
  still says no more than yes or no — which account, and whether the link is
  unknown, expired or spent, are differences that only help a guesser.

### Changed

- **Setting a password signs you in.** Holding the link proved the mailbox
  and the password was chosen on that very screen; a sign-in form asking for
  both again proves nothing to anybody. A second factor is not waived by
  this: where one is active, the same second step follows as at any sign-in.
- **Codes by e-mail can be switched off again.** Turning the second factor
  off asks for a working code — and with the mail method a code exists only
  once one has been sent. The panel now has a button that mails one, so the
  setting cannot be switched on and never off. A recovery code still works
  there too.

## [1.146.0] — 2026-08-21

Outgoing mail, rewritten as letters.

### Changed

- **Messages are written in the reader's language.** All four of them, and
  the reader's own choice decides — a colleague whose EMCargo is in
  German gets a German invitation, whoever made the account. A brand-new
  account has no preference yet and gets the installation's default; the
  covering letter with a consignment's documents follows the language the
  papers themselves are drawn up in, because its reader is a carrier rather
  than a user of this installation.
- **Every message is a letter now**: the EMCargo logo, a heading, a
  button where there is something to open. Plain text goes along in the same
  message, saying exactly the same things — it is what a client that refuses
  HTML, a screen reader, or a forwarded copy falls back to.
- The logo travels **inside** the message. A linked image would make the
  reader's mail client call this server: a tracking pixel by accident, and a
  broken image on an installation the internet cannot reach.

### Security

- **The invitation no longer names the administrator who sent it.** "admin
  has made an account for you" told every reader which account is an
  administrator's, including readers who should never have learnt it. It
  says "an administrator" now, in each of the four languages.
- User names are escaped where they appear in HTML: a name is not markup,
  and a mail client is a renderer.

Two-factor verification, with a way back in.

### Added

- **A second step when signing in**, chosen per person under Settings → My
  details: a code from an authenticator app, or a code by e-mail. The app is
  the stronger of the two — it works offline and does not depend on the mail
  server — and the QR code is drawn by this server, because a QR fetched
  from an image service would hand the shared secret to somebody else.
- **Who needs one is the administrator's choice**: voluntary, required for
  administrators, or required for everyone. Switching it on locks nobody
  out — someone without a second factor signs in as before and is asked to
  set one up.
- **Eight recovery codes**, shown once when it is switched on. Each works
  one time and is accepted wherever a code is asked for, so a phone in a
  canal does not mean hunting for a different form.
- **An administrator can clear a lost second factor** from the users page —
  one more reason for an installation to have more than one administrator.

### Security

- **The challenge is not a session.** A right password now answers with a
  short-lived challenge that says only that: it is refused everywhere a
  session is expected, so the second step cannot be skipped by keeping the
  challenge. A password changed in the meantime invalidates it.
- **Codes are stored as hashes and cost something to guess.** A mailed code
  expires in five minutes and dies after five wrong attempts; asking for a
  new one kills the old. An authenticator code is accepted one 30-second
  step either side of now, which is what an unsynced phone looks like, and
  no further.
- **Switching it off needs a working code**, or a borrowed session would be
  enough to strip the protection it is facing.
- TOTP is implemented against RFC 6238 rather than pulled in, and pinned to
  the specification's own test vector.

A new colleague can be invited instead of handed a password.

### Added

- **Send an invitation** when creating a user, with a mail server
  configured. No password is typed by the administrator at all: the new
  colleague gets a link and chooses their own, so it never travels by chat,
  note or a second message — and the administrator never knows it either.
  The link is valid for seven days, because someone may be on holiday the
  week their account is made.
- Until the link is used the account carries a random hash: an account
  nobody can sign in to, rather than one with a password somebody might
  guess.

### Changed

- **Whether the invitation went out is reported back**, in the same
  sentence as the account being made — sent, no mail server, or the mail
  server's own refusal. An administrator who believes a message was sent
  that never was is worse off than one who knows to pass the link on by
  hand. The account is kept either way; unmaking it would help nobody.

## [1.143.0] — 2026-08-21

Forgetting a password no longer means asking an administrator.

### Added

- **"Forgot your password?"** on the sign-in screen, with a mail server
  configured. A user name or an address gets a link to choose a new
  password; the link opens a page that asks for it twice.
- **The address of this installation** is now a setting. The links in
  outgoing mail need it; left empty, it is read from the request and from
  the proxy headers when those are trusted, which is right unless a reverse
  proxy hides its own host.

### Security

- **The form tells nobody who has an account.** Whether the account exists,
  is active, has an address, or the relay accepted the message: every
  request gets the same answer. A form that distinguishes them is a way to
  find out who works here, one guess at a time. What went wrong is written
  to the log, where the administrator can see it and an outsider cannot.
- **A reset token is treated as the password it effectively is.** Only its
  hash is stored, so a leaked database hands out no working links; it works
  once, expires after an hour, and asking again invalidates the previous
  link. Spending a token also drops every other outstanding one for that
  account.
- **Resetting ends the old sessions.** The session token carries a
  fingerprint of the password hash, so every sign-in from before the reset
  stops being accepted — which is the point of resetting when someone else
  may know the old password.
- The request form is rate-limited to five attempts a minute.

## [1.142.0] — 2026-08-21

The documents of a consignment can be mailed straight from the export step.

### Added

- **Send by mail.** Beside "Download all", a button that sends the same
  archive as an attachment — to the carrier, the consignee, or several
  addresses at once (separate them with a comma). Subject and message are
  yours to write, or are written for you: the default message names the
  colleague who sent it, because the recipient has to know who mailed them a
  consignment's papers.
- The archive is built by the same code as the download, so the mail cannot
  quietly carry a different set of papers — README of omissions included.

### Notes

- The archive is deleted the moment the message is out. EMCargo keeps no
  copy of a consignment's documents.
- One message may carry 15 MB of attachments. Beyond that the size and the
  limit are named, rather than leaving the relay to answer with a code.
- Without a mail server the button does not appear: a button that can only
  fail is not a feature. Configure one under Settings → Administration.

## [1.141.0] — 2026-08-21

An administrator can point EMCargo at a mail server.

### Added

- **Mail server settings.** Settings → Administration → Mail server asks for
  the server, the port, how the connection is encrypted (STARTTLS, direct
  TLS, or none for a relay on your own network), the sign-in if the server
  wants one, and the sender address and name. Four languages.
- **A test message.** One button sends a short message using the settings as
  saved — to the address you give it, or to your own account when you leave
  it empty. Whatever the server answers is shown unchanged: a refused
  password, an unreachable host and a rejected sender are different problems
  with different fixes, and guessing between them helps nobody.
- **`SMTP_HOST` and friends** configure the same thing from the environment,
  for installations that prefer their compose file. A host and a sender there
  switch sending on; what is saved on the screen takes precedence from then
  on, without a restart.

### Security

- **The mail password never reaches a browser.** It is stored on the server
  and redacted out of every response; the screen shows an empty field and
  says whether a password exists. Saving with that field empty keeps the
  stored password, so the port can be corrected without retyping it.

Sending is off until it is configured, and nothing is sent through it yet
beyond the test message — what EMCargo mails is a decision per feature,
not something a mail server setting quietly grants itself.

## [1.140.0] — 2026-08-20

Enter "petrol", confirm UN 1203, and the kind of package could only be
"6PC glass receptacle in wooden box". One nonsensical choice, where the
field is supposed to search the whole catalogue.

### Fixed

- **A piece count is no longer mistaken for a packaging.** A cargo line
  without a stated packaging carries `pcs`, the bare piece count the parser
  falls back to. That unit was taken over as the kind of package, and
  because a value was then present the searchable packaging field turned
  into a closed dropdown — filled by a catalogue search that matched "pcs"
  through "pc" to the code 6PC. Piece counts stay out of the package field,
  which is once again a free search over the catalogue.
- **A mass or volume unit never becomes the kind of package either.** "1000
  kg petrol" counts mass, and "kg" was ending up on the transport document
  as the kind of package. Only a unit that names a receptacle is taken
  over — as are words the table does not know, which are the consignor's
  own ("fust", "octabin").

Counted packagings are unaffected: "1000 jerrycans" still offers the six
jerrycan kinds of 5.4.1.1.1 (e), from 3A1 steel to 3H2 plastic.

## [1.139.0] — 2026-08-20

With the image finally pullable, the update got one step further and
stopped at the next one: the daemon refused the updater container with
`400 Duplicate mount point: /var/run/docker.sock`.

### Fixed

- **The Docker socket is no longer mounted twice.** The updater copies the
  application's own bind mounts to the helper container and adds the socket
  if it is not among them — but it compared whole bind strings, and Docker
  writes a bind with its access mode: Unraid records the socket as
  `/var/run/docker.sock:/var/run/docker.sock:rw`. The plain form never
  matched, so the socket was added a second time and the daemon refused two
  mounts on one destination. Binds are now compared by the container path
  they target, in every shape Docker writes them.

### Note for existing installations

This fix lives in the code that *starts* an update, so it only takes effect
once it is running. An installation on v1.135.0 or v1.136.0 still hits the
duplicate mount and needs one more update by hand; from this version on the
button does the work.

## [1.138.0] — 2026-08-20

v1.137.0 promised two tag spellings and delivered one. The alias was added
to the wrong workflow — the release proved it, so this release fixes it
where the naming actually happens.

### Fixed

- **The v-prefixed image tag is published after all.** v1.137.0 added the
  alias to the metadata action in `ci.yml`, but CI does not run on a tag:
  the version tag is put on the existing manifest by `tag-release.yml` with
  `imagetools create`. The added line was inert and `:v1.137.0` was never
  published. The release step now names both `:<version>` and `:v<version>`
  on the same manifest, and the dead line in `ci.yml` is gone. Installations
  running v1.135.0 or v1.136.0 ask for the v-form, cannot update themselves
  out of those versions without it, and can update in-app to this release.

## [1.137.0] — 2026-08-20

The update button reached the registry and asked for an image that was never
published under that name. One character — a `v` — stood between a working
in-app update and an honest 404.

### Fixed

- **The updater pulls the tag that actually exists.** Release images are
  published as `emcargo:1.136.0`; the updater asked for
  `emcargo:v1.136.0` and got HTTP 404 from Docker Hub, reported faithfully
  in the panel. It now asks for the bare version, and a test pins the exact
  tag the pull requests so the prefix cannot creep back.
- **Both tag spellings are published.** Every release image now carries
  `:<version>` and `:v<version>`. Installations running v1.135.0 or v1.136.0
  ask for the `v` form and would otherwise be unable to update themselves out
  of the broken versions — they can now update in-app to this release and
  onwards.
- **The documentation names the real tag.** The Unraid pinning example used a
  `v`-prefixed tag that was never published.

## [1.136.0] — 2026-08-20

The users page grows up. It was a day-one leftover — a create form and a
list, hardcoded strings, no way to change anything after the fact — while
the backend already knew how to update and delete users safely. Now the
page speaks for the whole feature.

### Added

- **Administrators can reset a user's password.** An inline form per user
  sets a new password (minimum eight characters) without knowing the old
  one — the whole point of a reset. The backend hashes it exactly like any
  other password.
- **Roles and activation are managed from the page.** Each user card has a
  role selector, an activate/deactivate button, and a delete button with a
  confirmation that names the account. Deactivated accounts are visibly
  dimmed and badged.
- **The safety rules explain themselves.** You cannot demote, deactivate
  or delete yourself, nor the last active administrator — the server
  already refused, and now the controls are disabled up front with a
  tooltip saying why. Your own account carries a "you" badge.

### Changed

- **The users page is translated.** Every label, hint, confirmation and
  error lives in all four interface languages; the create form gained
  proper labels, validation and a password hint.

## [1.135.0] — 2026-08-20

The first real-world installation to enable in-app updating did everything
right — socket mounted, switch on — and saw no button and no reason. Both
halves of that are fixed.

### Fixed

- **The Docker socket is now usable by the application.** EMCargo runs as
  uid 1000, while the socket the operator mounts belongs to root (Unraid) or
  the docker group (most distributions) — every call was denied and the
  capability silently reported unavailable. The start script now joins the
  app user to the socket's own group id before dropping privileges: exactly
  the access the operator chose to grant this container, and nothing changes
  on the host. No re-mounting needed — pull this version once by hand and
  the button appears.
- **The Updating section names why the button is missing.** A permission
  problem gets its own diagnosis (it used to masquerade as "container not
  found"), and the reasons that existed but were never shown — own container
  not found, socket unusable, a foreign image — are now printed right in the
  panel whenever the switch is on and a socket is mounted. Four languages.

## [1.134.0] — 2026-08-20

The settings screen, tidied. The administrator area had grown into one long
column where action panels sat between form fields, under a save button that
did not govern them — and half the screen was explanatory text.

### Changed

- **Administration and Maintenance are now separate tabs.** Administration
  holds what an administrator *saves*: new-user defaults, the organisation,
  the feature switches, the session length and the outbound connections — one
  form, one save button. Maintenance holds what an administrator *does*:
  updating, the UN card set and the assistant's local model, each panel
  acting immediately. The separate Assistant tab folds into Maintenance.
- **The notes went on a diet.** Long explanations are shortened to the one
  sentence that helps a decision, or moved behind the fold: the
  Watchtower/Unraid guidance and the in-app-update instructions live inside
  the existing "enable updating from here" disclosure, the assistant's
  disk/RAM footprint shows only while the model is not yet installed, and
  the amber administrator banner is replaced by a single line. The Docker
  socket warning stays visible — that one is load-bearing.

## [1.133.0] — 2026-08-20

Updating from inside the application — where the operator allows it. The v1.126.0
stance ("a container cannot update itself") stays true and is now worked around the
only honest way there is: by the operator deliberately handing the container the
Docker API.

### Added

- **Check for updates, on a button.** The settings screen's Updating section asks
  GitHub afresh when clicked, bypassing the six-hour cache the passive check lives
  off, and says plainly: up to date, newer version found, or GitHub unreachable
  (which is not "up to date").
- **Update and restart, opt-in.** With `UPDATE_APPLY_ENABLED=true` **and** the Docker
  socket mounted into the container, an update button appears whenever a newer
  release exists. Pressing it pulls `ghcr.io/jeffreymooiweer/emcargo` at the release's own
  tag — the version is never caller input, the repository is pinned in code and
  verified against the running container's own image — and hands the swap to a
  short-lived helper container started **from the new image**: stop, rename aside,
  recreate with the identical configuration (binds, ports, networks, restart policy),
  start, and only then remove the old container. If the successor will not start, the
  old container is renamed back and restarted: a failed update leaves a working
  installation, and says why on the settings screen.
- **The restart is part of the process.** The page follows the update through
  `<data-dir>/update-state.json` — pulling, restarting — keeps knocking while the
  container is being replaced, and reloads into the new version when it answers; the
  what's-new card then shows what changed. Capability is reported honestly per
  missing prerequisite: switch off, no socket, socket unusable, or a container
  running a foreign image (which is refused).

### Changed

- `docs/configuration.md` documents the two prerequisites and states the trade-off in
  plain words: mounting the Docker socket gives the container administrator rights
  over the host — a deliberate operator decision, off by default, and the manual
  `docker compose pull` route keeps working without it. The outbound-connections list
  in `docs/privacy.md` grows to six: the image pull from Docker Hub, admin-initiated
  and opt-in only.

## [1.132.0] — 2026-08-20

The rail gets its own UN cards. RID table A was the largest measured table this
application still lacked — the cards for rail failed honestly rather than relabel
road data — and it is now read in full, from three editions at once.

### Added

- **RID 3.2.1 table A as a seed** (`backend/seed/dg/rid_table_a.json`): 2,939 rows
  over 2,347 UN numbers, twenty-two columns including the rail's own — the RID tank
  code and its TU/TE provisions, the transport category, the W/VC/CW/CE provisions
  of 7.2.4, 7.3, 7.5.11 and 7.6, the hazard identification number, and the bracketed
  shunting models of column (5). Read geometrically by
  `scripts/extract_rid_table_a.py` (run by **Extract UN card assets**): the Dutch
  and OTIF English editions are parsed as two independent typesettings of the same
  table and compared on every coded column, and the 212 cells where the two
  genuinely disagreed were arbitrated by the OTIF German edition — which sided with
  the English on every one (the Dutch print drops special provision 386 across the
  gas entries, prints MP7 for MP8 four times, and shifts a whole row at UN 2215).
  The reading is cross-checked against the v1.123.0 shunting-label seed (exact
  agreement) and the ADR identity columns (2,345 shared UN numbers).
- **RID UN cards.** The RID adapter now generates from that table: 2,347 UN numbers,
  official label artwork, shunting models named per 5.3.4, and the rail columns on
  the card. An entry the RID prints as CARRIAGE PROHIBITED or NOT SUBJECT TO RID
  becomes a card saying exactly that. Air remains the one modality that fails
  honestly, for want of a freely licensable source.

### Changed

- The full card set grows from three regimes to four (~9,400 cards); the generator
  version moves to 1.1.0. Publishing a new set is the same **Generate UN cards**
  dispatch as before.

## [1.131.0] — 2026-08-20

The UN cards grow more official artwork and more printed law. All three
follow-ups from the v1.129.0 pipeline that could be done without new sources
are done.

### Added

- **The environmentally hazardous substance mark, from the book.** The mark on
  the cards (marine pollutants at sea, environmentally hazardous by road and
  water) is now the artwork of ADR Figure 5.2.1.8.3, cut from the UNECE
  English ADR 2025 like the 22 hazard labels before it. The printed figure
  carries dimension annotations hugging its edges, so the extractor fits the
  mark's own diamond to the render — the upper edges are annotation-free and
  grow one pixel per row, which fixes the geometry — and blanks everything
  outside it. The vector-drawn stand-in is retired.
- **ADN cards print the 7.1.6 requirements in full.** A new extractor
  (`scripts/extract_adn_provision_texts.py`, run by the **Extract UN card
  assets** workflow) reads the VE/LO/HA/CO/ST/RA/IN texts verbatim from the
  UNECE English ADN 2025 into `backend/seed/dg/adn_provision_texts.json`.
  There is no hand-kept expected count: the extraction is validated against
  the codes ADN table A actually assigns — all 25 assigned codes came out
  with their text. The cards print them per code; a code without an extracted
  text keeps its honest article reference.
- **IMDG cards print the code descriptions in full.** The SW/H/SG codes of
  columns 16a and 16b now carry their verbatim descriptions from IMDG 7.1.5,
  7.1.6 and 7.2.8 — already measured into `imdg_codes.json` since v1.22.0 —
  instead of a bare chapter reference. The stowage category keeps its
  reference to 7.1.3.2, whose definitions are not yet extracted.

### Changed

- The label extractor supports per-crop rotation (the mark's page is upright
  where the label table is rotated) and a `--debug-find` measurement mode
  that renders the pages naming a section, so the next crop box can be
  measured the same way this one was.

## [1.130.0] — 2026-08-20

Two complaints from use, both fixed at the root. **Download all** fired one download
per document; it now hands over a single ZIP that also carries the UN cards and the
instructions in writing for the journey. And the instructions in writing offered a
language that could not be downloaded — because the models lived only in a regulations
store nobody's installation had filled. The models now ship with the application.

### Added

- **Download all as ZIP.** A new `/api/documents/export/bundle` endpoint renders every
  ready document through the same code path as the per-document buttons and returns
  one archive, with the shipment's UN cards under `un-cards/` and the instructions in
  writing for the journey's regimes (in the chosen document language) under
  `instructions/`. Anything that cannot be included — a document still incomplete, a
  UN card the server does not hold, an instruction language neither bundled nor in the
  store — is named in a `README.txt` inside the archive rather than silently missing.
- **The prescribed models are bundled.** The **Extract model documents** workflow runs
  `scripts/cut_model_documents.py` on a runner: every source edition is verified
  against the SHA-256 the register pins, the measured page ranges are cut with the
  same library that measured them, and the sixteen models — instructions in writing
  for ADR/RID/ADN in Dutch, English, German and French, plus the ADN 8.6.3 checklist
  in four languages — land in `backend/seed/models/` with their provenance in a
  manifest. Every language button on the export step now delivers a PDF out of the
  box.

### Changed

- The lookup order for a model is now: the operator's regulations store first, the
  bundled cut second, the CI cache last — an installation that collects its own
  editions is served from those, and `instruction_status` reports `bundled` or
  `stored` accordingly. A model in none of those places is still reported missing by
  name, never borrowed from a neighbouring language (5.4.3.2).

## [1.129.0] — 2026-08-19

EMCargo now generates its own UN cards. The third-party card set that filled
`un_cards/` since v1.66.0 is gone — from the repository and from the Docker image — and
in its place stands a pipeline whose every value is measured: one A4 datasheet per UN
number **per regime** (`UN1203_ADR.pdf`, `UN1203_ADN.pdf`, `UN1203_IMDG.pdf`), rendered
from the same seed tables the compliance checks run on, published as a GitHub Release
and imported by an administrator. See the new [docs/un-cards.md](docs/un-cards.md).

### Added

- **The card generator** (`scripts/un_cards/`). Per-modality adapters read only the
  measured seeds — ADR 2025 table A (plus the additions file and the 1.1.3.6 points),
  ADN 2025 table A, IMDG 42-24 Dangerous Goods List — and a modality without a measured
  table **fails honestly**: RID until its table A is column-read beyond column (5), air
  for want of a freely licensable source. No language model and no hand fills in a
  regulatory value; a UN number with several entries becomes several pages of one PDF,
  and printed name variants that share every regulatory value collapse into one page.
- **Official hazard label artwork.** The 22 label models on the cards are cut from the
  UNECE English ADR 2025 Volume II, 5.2.2.2.2, along measured crop boxes pinned in
  `scripts/un_cards/assets/label_crops.json` — the figures there are rotated drawn
  content that neither the image extractor nor the vector reader could see, so the
  boxes were measured from rendered pages and are re-cut deterministically by
  `scripts/extract_adr_label_models.py` (workflow: **Extract UN card assets**).
- **Provisions printed in full.** The V (7.2.4), CV (7.5.11) and S (8.5) provisions
  are extracted verbatim from the same official edition into
  `backend/seed/dg/adr_provision_texts.json` and printed on the ADR cards under their
  codes — the reader gets the obligation itself, not a bare article number. A code
  whose text is not in the seed falls back to the article reference; nothing is ever
  summarised by a model.
- **Generate UN cards workflow.** `workflow_dispatch` with `scope` (single UN for a
  quick look, or all), `modalities` and `publish`. It validates before it publishes —
  filename ↔ UN ↔ modality agreement, `%PDF` header, SHA-256 against the manifest, the
  UN number present in the text, no third-party branding — and a set that fails does
  not ship. Published sets are GitHub Releases tagged `un-cards-YYYY.MM.DD-N` carrying
  `emcargo-un-cards.zip`, `manifest.json` and `generation-report.json`.
- **Settings → UN Cards** (administrators). Shows the installed set — generation date,
  per-regime counts, editions, size — and offers **Check for a new set** (reads the
  pinned EMCargo release feed, only when clicked), **Download & import latest**,
  **Import from ZIP** for installations without outbound access, and **Remove**. Every
  import is atomic: member names must match exactly the shapes the generator produces
  (which rules out Zip Slip outright), sizes are capped, every card is hashed against
  the packaged manifest, and the verified set replaces the old one in a single rename —
  a failed import leaves the working set untouched. New API routes under
  `/api/settings/un-cards/…`, admin-only.
- **Per-regime card selection in the wizard.** The UN card download now sends the
  journey's dangerous goods profiles and receives exactly the cards for those regimes;
  a UN number without a card on a requested regime is named as missing, and no other
  regime's card is substituted — the regimes print different obligations.

### Changed

- The Docker image no longer carries a card library (~575 MB smaller); cards live on
  the data volume under `un-cards/` and installations without a set simply say so.
- `docs/un-cards.md` documents the whole pipeline; `docs/development.md`,
  `docs/user-guide.md`, `docs/dangerous-goods.md`, `docs/data-sources.md` and
  `docs/privacy.md` (outbound connections: four things became five) follow suit.

### Removed

- `un_cards/` (2,849 third-party PDFs) and `scripts/fetch_un_cards.py`. The
  per-substance IMDG data once read from those cards stays in
  `backend/seed/dg/card_data.json` with its provenance recorded, until it is re-read
  from the official IMDG Code.

## [1.128.0] — 2026-08-19

### Added

- **The customs references that come back from a filing get fields of their
  own.** The references section gains the **ENS reference (ICS2)** — goods
  entering the EU customs territory require an entry summary declaration
  lodged in ICS2 before arrival, normally by the carrier on the consignor's
  data; where its MRN is known it travels on the papers — and the **AES
  ITN** — exports from the United States require Electronic Export
  Information filed in AES, and the Internal Transaction Number is the
  proof that belongs on the transport document. Both are conditional
  fields with the rule named in the help text in all four languages, and
  both enforce their format on export (18-character MRN shape; X plus
  fourteen digits), so a mistyped reference is caught before it reaches an
  official form.
- **Paste the booking confirmation; the references find their fields.**
  The carrier's numbers arrive in a confirmation e-mail *after* the
  booking — exactly when the wizard's carrier-provided fields are still
  empty. A paste box at the top of the shipment-details step reads that
  e-mail for the references it can verify by format: the AWB number
  (three-digit prefix plus serial, checked against IATA's mod-7 check
  digit, so a phone number is refused six times out of seven), a booking
  reference (only where the text itself names it one — a bare code could
  be anything), the ENS MRN and the AES ITN. What the text does not carry
  is absent, never invented; only still-empty fields are filled, so
  nothing a user typed is ever overwritten; and the pasted text is read
  once and stored nowhere.

## [1.127.0] — 2026-08-19

### Added

- **The equipment library exports itself, on request.** *Export library* on
  the equipment screen hands back the whole list — active and inactive
  items alike — as a spreadsheet in the import's very own columns
  (`specifications`, `length_cm`, `width_cm`, `height_cm`,
  `wall_thickness_mm`, `weight_kg`, `aliases`, `active`). The file round
  trips: importing it into an empty installation recreates the library,
  which makes it the backup, the hand-over to a colleague who maintains the
  list in Excel, and the seed for a second installation, all in one — and a
  test walks that round trip whole. Numbers print as numbers a person can
  check against reality (never scientific notation), aliases join on the
  comma the import splits on, and an empty library exports its headers,
  which is exactly the template. Nothing is exported unless someone clicks:
  no schedule, no copy kept anywhere.

## [1.126.0] — 2026-08-19

### Added

- **The update check, behind the administrator's switch.** A container
  cannot update itself, so all this feature may do is tell the one person
  who operates it that there is something to pull. `GET /api/update-status`
  asks GitHub's public release listing — the fourth and last outbound
  request the application can make — and answers in three deliberately
  distinct shapes: the check is off, GitHub could not say (which is *not*
  "you are up to date"), or a real comparison against the running version.
  Admin-only on both grounds: nobody else can act on the answer, and a
  signed-in user must not be able to make an installation call GitHub when
  its administrator switched that off. The switch (`UPDATE_CHECK_ENABLED`,
  and on the settings screen under Outbound connections) is read per
  request, so flipping it needs no restart; answers are cached six hours
  when they worked and fifteen minutes when they did not, so an outage
  never turns a settings visit into a timeout wait.
- **A quiet corner note, not a modal.** When a newer release exists an
  administrator gets a small dismissible toast with the version and a link
  to its release notes. Dismissing remembers that release in the browser —
  the same version never nags again, a newer one shows up again. Regular
  users see nothing and trigger nothing.
- **The settings screen says what updating actually is.** A new *Updating*
  section explains, honestly: pull the newer image and restart the
  container — two commands with Docker Compose, automatic under Watchtower,
  one click in Unraid's Docker tab — and that the data volume stays put.
  The check above changes none of it; it only tells you there is something
  to pull. Documented in all four interface languages, with the outbound
  request named in `docs/privacy.md` next to the other three.

## [1.125.0] — 2026-08-19

### Added

- **A what's-new card after an update.** A self-hosted container updates
  silently — the operator pulls a newer image and the next sign-in is a
  different program with nothing said. The first sign-in after an update now
  shows the changelog entries between the version last seen and the version
  running, once: dismissing the card writes the running version into the
  account's preferences, so a second device does not show the same notes
  twice, and an unread card returns next login rather than being lost. A
  fresh account, or one from before the marker existed, sees no card at all —
  a first login is not an update, and 159 releases of history would teach
  everyone to dismiss unread.
- **The changelog serves itself.** `GET /api/changelog?since=<version>`
  parses `CHANGELOG.md` — the same file a release is written into, now
  shipped in the Docker image next to `VERSION` — so the card can never
  disagree with the record. The endpoint reports the *running* version, not
  the newest heading, so a changelog ahead of or behind the binary cannot
  wedge the card open; the response is capped at twenty releases and says so
  when it was cut short. A new test fails the pull request if the newest
  heading and the `VERSION` files disagree, which makes forgetting a release
  note a red build instead of a silent gap.
- **`last_seen_version` in the user preferences.** Stored in the same
  upgrade-proof JSON payload as the rest, validated as a version number or
  empty, absent in payloads written by older versions and therefore
  default-empty. The card's chrome speaks all four interface languages; the
  entries themselves stay in English, the repository's language.

## [1.124.0] — 2026-08-19

### Added

- **The full-load statement, and with it both shunting cases decided.** The
  shunting labels of RID 5.3.4 attach in exactly two cases; since v1.123.0
  the per-substance half is read, and now the per-wagon half is a field.
  Whether the packages make up a **full load of one wagon or large
  container** is a wagon-level fact no table supplies, so it is the
  consignor's own statement — like the containers-only statement of ADN
  7.1.5.0.2 before it, never inferred from quantities. With it: chlorine in
  a declared tank-wagon gets *required* shunting labels by name (the class 2
  case needs no statement — a tank-wagon is a tank-wagon), black powder with
  the full-load statement gets them too, and without the statement the
  class 1 case stays the condition it is.
- **The RID's own instructions in writing, served from the store.** RID
  5.4.3.4 prints a four-page model of its own — INSTRUCTIONS IN WRITING
  ACCORDING TO RID, addressed to the train driver — and 5.4.3.1 requires it
  in the driver's cab. The model is registered in all four languages, page
  ranges measured per edition on a runner (English 856–859, German 916–919,
  French 910–913, Dutch 981–984), and the export step offers it for a rail
  consignment the way it offers the ADR's. 5.4.3.2 keeps providing it the
  carrier's duty, and the register says so.

### Changed

- **What the RID points total governs, read and said.** RID 1.1.3.6.3 opens
  "Where, in accordance with 1.1.3.1 (c), dangerous goods … are carried" —
  and 1.1.3.1 (c), read on page 27 of the English edition and confirmed in
  the German, is the exemption for carriage by enterprises ancillary to
  their main activity, at most 450 litres per packaging, never class 7. RID
  has no general small-load relief the way ADR 1.1.3.6 grants one, so
  staying under 1000 relieves an ordinary rail consignment of nothing. The
  points card's basis note now says exactly that, and the absence of an
  exemption branch in the rail placarding check is a reading rather than
  caution.

## [1.123.0] — 2026-08-19

### Added

- **The shunting models of RID column (5), read per substance.** Since
  v1.121.0 the shunting labels of 5.3.4 were a class-level condition,
  because which substances carry the bracketed model sits in RID's own
  table A — a column the application's ADR table does not have. It is
  extracted now: `scripts/extract_rid_shunting_labels.py` reads the cells
  geometrically from the OTIF English edition and the German edition,
  which agree on every one of the **351 rows** that bracket a model — 335
  carry (+13), 16 carry (+15), all of them class 1 (181 rows) or class 2
  (170 rows), exactly the two cases the column (5) explanation names, and
  the 16 model-15 rows are all division 1.1 explosives. The first probe
  run earned its keep: the plain (13) and (15) it matched were the table's
  own column headers, printed on every page — the cells print (+13) and
  (+15), and the plus sign is the discriminator.
- **The answer is per substance now, in both directions.** A chlorine
  tank-wagon is told its model by name; UN 0331 — class 1, which used to
  get the hedge — is told the absence is real, because neither edition
  brackets a model for it. What stays a condition is the one thing still
  invisible from here: whether a wagon comprises a full load. The seed
  (`rid_shunting_labels.json`) records both workflow runs and the
  cross-check, and the class-level wording remains only as the fallback
  for an installation whose seed is missing.

## [1.122.0] — 2026-08-18

### Added

- **Rail transport is released.** The rail tile comes off the lock over the
  same bar inland waterway cleared in v1.63.0: every check a rail
  consignment gets is cited to RID rather than borrowed — the 1.1.3.6 count
  per wagon or large container, RID's own 7.5.2 tables and the 7.5.3
  protective distance, CW 28 in place of CV28, the hazard identification
  number of 5.4.1.1.1 (j) on the CIM, bulk admission under RID 7.3, and
  since v1.121.0 the placarding of chapter 5.3. What the application cannot
  see is named rather than silent: whether a wagon comprises a full load,
  and which substances carry the bracketed shunting models in RID's own
  column (5).
- **The rail archetypes: the CIM flow verified end to end.** Two
  consignments through the real API on every commit — aniline in drums on a
  wagon (the package wagon placarded for every class, CW 28 cited, no
  CV28, no orange band) and chlorine in a tank-wagon (the numbered plates
  carrying 265 / UN 1017, the number read out of table A rather than
  assumed; the orange band from the liquefied state; the shunting labels as
  the condition they are), each ending in a rendered CIM and RID placarding
  sheet, the sheet in German as well.
- **The Dutch RID is in the document store.** The adoption run mapped the
  operator's "RID 2025.pdf" onto the registered `rid_nl_2025`, hash
  verified — the rail provisions can now be read in four editions.

### Changed

- README, roadmap, user guide, documents page and the coverage assessment
  say the released modes are road, rail and inland waterway; the lock keeps
  guarding sea, air and multimodal in the same three places as before.

## [1.121.0] — 2026-08-18

### Added

- **Placarding for the rail leg: RID 5.3, derived and on paper.** Read in
  the English edition (printed pages 837–845, plus the column (5)
  explanation of 3.2.1 on page 258) and the German edition, which agree.
  Three things make the rail answer its own rather than the road's on loan:
  a **wagon carrying packages is placarded for every class** (5.3.1.5),
  where a road vehicle placards only for classes 1 and 7, both sides and no
  rear; the **orange plates attach only where column (20) gives a hazard
  identification number** (5.3.2.1.1), and then carry the two numbers on
  each side of the tank or bulk wagon — there are no plain front-and-rear
  plates on rail, and printing the road's plate rule on a rail answer would
  prescribe equipment RID does not ask for; and the **shunting labels of
  5.3.4** (model 13, shunt with care; model 15, loose or hump shunting
  forbidden) are only ever affixed in two cases — class 1 on both sides of
  full-load wagons, class 2 on both sides of tank-type wagons. Both cases
  are named as conditions: whether a wagon is a full load is not visible
  from here, and which substances carry the bracketed model sits in RID's
  own column (5), which this application does not hold. The orange band of
  5.3.5 is derived from the state of the gas in the classification code
  (2 liquefied, 3 refrigerated liquefied, 4 dissolved), the environmentally
  hazardous mark of 5.3.6 and the empty-uncleaned rule of 5.3.1.6 come
  with it, and the answer reaches paper as the RID placarding sheet,
  registered for the rail modality under its own document key.
- **The RID in four languages sits in the store.** The operator's Drive
  folder was taken in on a runner: every already-registered book verified
  against its pinned hash, and one new file recognised — the Dutch RID
  edition, now registered as `rid_nl_2025` with the hash the runner
  computed. The rail provisions can be read in the OTIF English, the
  German, the French and the Dutch editions from here on.

## [1.120.0] — 2026-08-18

### Added

- **Placarding for the water leg: ADN 5.3, derived and on paper.** The road
  vehicle has had its 5.3 answer since v1.57.0; the units that come on board
  a dry cargo vessel had nothing. ADN 5.3 is read now — the English edition
  (printed pages 309–321) and sections 5.3.1–5.3.6 of the official Dutch
  edition, which agree — and what shapes the answer is that the application
  cannot see which kind of cargo transport unit the packages travel in,
  while the kind decides everything: a **container** is placarded for any
  class, both sides and each end (5.3.1.2); a **wagon** carrying packages
  likewise, both sides (5.3.1.5.3); a **road vehicle** carrying packages
  only for classes 1 and 7 (5.3.1.5.1/5.3.1.5.2) — except that the note to
  5.3.1.5.2 placards it for every class when the ADN journey precedes a
  voyage by sea. So the label models of columns (5) and (6) are computed
  once — with the class 1 aggregation of 5.3.1.1.2 (most dangerous division
  in the order 1.1, 1.5, 1.2, 1.3, 1.6, 1.4; 1.5 D beside 1.2 escalates to
  1.1; no group letter across groups) and model 9 in place of 9A
  (5.3.1.1.4) — and the placement rules are given per kind, each under its
  own provision. The orange plates of 5.3.2.1.1, the numbered plates of
  5.3.2.1.2 for portable tanks, the sea-chain alternative of 5.3.4.1, the
  environmentally hazardous mark of 5.3.6 and the empty-uncleaned rule of
  5.3.1.6.1 come with it; under a possible 1.1.3.6.1 exemption the note
  says 5.3 is not among the surviving conditions — reported, never granted.
- **The ADN placarding sheet.** The same sheet the road has had since
  v1.83.0, with the water's chapter answering, registered for the inland
  waterway modality under its own document key so an inland consignment is
  never handed the road's answer. A cargo tank consignment is named as
  chapter 7.2's — its vessel shows the cones of 7.2.5.0 — instead of being
  given an empty page.

### Not derived, with the reason recorded

- The elevated temperature mark of 5.3.3 (the application is not told a
  carriage temperature) and the exclusive-use plates of 5.3.2.1.4
  (exclusive use is not a field).

## [1.119.0] — 2026-08-18

### Added

- **The water's own mixed loading prohibitions, complete.** An inland-only
  consignment used to be measured against ADR 7.5.2 — a road chapter the ADN
  does not prescribe — under a note claiming the ADN's own regime was not
  held, while the distances of 7.1.4.3 had been applied since v1.59.0. The
  rest of chapter 7.1.4 is read now, in the English edition (printed pages
  394–399) and the official Dutch edition, which agree: **7.1.4.2** — a
  vessel carrying class 5.1 in bulk carries nothing else; within the
  consignment that is an error, for the rest of the vessel a condition this
  application cannot see. **7.1.4.10** — the foodstuffs precaution, gated by
  special provision 802 in column (6) of the ADN's own table A (652 rows
  carry it) instead of the borrowed CV28, with the ADN's own separation
  measures: full-height partitions, unmarked packages in between, or 0.8 m.
  **7.1.4.4/7.1.4.5** — the container exceptions, on the consignor's own
  containers-only statement and never a packaging type: closed containers
  are outside 7.1.4.3, other containers reduce the 3.00 m to 2.40 m, and a
  vessel carrying only containers may answer the whole prohibition with the
  IMDG Code's stowage and segregation requirements.

### Changed

- **7.5.2 no longer runs for a selection it does not govern.** Inland-only
  gets the ADN findings above under their own numbers; rail-only was already
  evaluated against RID's own table; and a rail-plus-inland selection now
  uses the rail table for the rail leg where it used to be handed the road
  one. Combined selections keep both answers, and the basis note — produced
  since v1.33.0 but never shown — now appears under the findings it
  qualifies, saying which leg the 7.5.2 outcome belongs to and that RID's
  7.5.2.2 carries no compatibility group A.
- **The coverage document tells the truth about the tank vessel document
  again.** It still listed ADN 5.4.1.1.2 as unbuilt and first on the list,
  while v1.91.0 shipped it; the assessment now records that, closes the
  "part of 7.5.2 still borrowed" item, and is maintained up to this release.

## [1.118.0] — 2026-08-18

### Changed

- **Air transport is locked again, the demonstration over.** As agreed when
  it was unlocked in v1.117.0: the demo constant is gone and the released
  modes are road and inland waterway once more. Nothing about the coverage
  changed in between — the IATA quantity tables are still not held, so the
  Q value depends on the M a user enters. That is fine to show while
  somebody stands next to the screen explaining it, and not fine on a
  document somebody signs unattended. README, roadmap, user guide and the
  documents page carry the plain wording again, and the roadmap keeps the
  note that air's declaration and segregation checks are already sound —
  which is why it was the one that could be demonstrated at all.

## [1.117.0] — 2026-08-18

### Changed

- **Air transport is temporarily unlocked, for a demonstration.** On the
  owner's request, and meant to be taken out again. Of the three locked
  modes it is the defensible one to show: the IATA declaration and the
  segregation checks are sound, and where the remaining gap sits — the IATA
  quantity tables are not held, so the Q value depends on the M the user
  enters and the passenger/cargo-aircraft limit is never derived — the
  application already says so on the screen *and* on the document itself.
  Rail, sea and multimodal stay locked. The unlock is one named constant,
  `DEMO_UNLOCKED_MODALITIES` in `ModalitySelectPage.tsx`; removing it locks
  air again, and the roadmap says so beside the air entry. README, roadmap,
  user guide and the documents page state the temporary unlock rather than
  claiming air is released.

## [1.116.0] — 2026-08-18

### Removed

- **The SAP material number (MATNR) left the equipment library.** It came
  from one organisation's old system, meant nothing anywhere else, and yet
  it was the column an item was named by — in the overview, in the search
  results and in the import template. Gone from all of them: the item is
  now named by its description, which is what people actually read. An
  existing library keeps every item; only the column disappears, at the
  first start after the update.

### Added

- **The wall thickness took its place.** A measurement that genuinely
  describes the thing — and without which the weight of an angle or a
  hollow section cannot be worked out at all. It sits in the form, in the
  overview (table and phone cards) and as a column in the import template,
  which reads it under any of its names in the four languages (wanddikte,
  wall thickness, Wandstärke, épaisseur). The template column order changed
  with it, so download the fresh template before the next bulk import.

### Changed

- An equipment table created before this version is brought in line at
  startup: the wall thickness column is added and the retired SAP column
  dropped, both only when needed and safe to repeat on every start. A test
  builds an old table, migrates it, and checks the items survive.

## [1.115.0] — 2026-08-17

### Changed

- **The settings page is grouped into tabs.** It had grown into one long
  scroll where a theme choice sat a few centimetres above the switch that
  decides whether this installation talks to the internet at all — personal
  preferences and instance-wide policy reading as one list. They are now
  separate groups: appearance, shipment defaults, my details (with the
  signature), and, for an administrator only, administration and the AI
  assistant's model. The personal groups keep sharing one draft and
  therefore one save button, so switching between them never loses what was
  typed. On a phone, where a row of tabs would wrap or scroll out of sight,
  the same groups sit in a dropdown at the top; from the medium breakpoint
  the tabs themselves appear. Tab labels in all four languages, and a test
  pins that the administrator's groups exist only for an administrator.

## [1.114.0] — 2026-08-17

### Added

- **Route endpoints from the sentence land as catalogue entries.** "The
  port of Rotterdam" used to be stored as those words, while a manual pick
  in the wizard stores the entry from the offline location catalogue. The
  assistant now resolves the route endpoints it reads against that same
  catalogue: a kind word narrows the search (port, airport, station, in
  the four languages), an exact and unambiguous match resolves —
  "Duisburg" to the one entry of that name, a spoken port to Rotterdam
  (NLRTM), Schiphol to AMS — and a bare city that exists in several
  countries only resolves to the language's own country. An address or a
  plain town stays the consignor's words, because a city is not a port.
  What the assistant stores is byte-for-byte what the wizard's picker
  would have stored.
- **A date picker for the assistant's date questions.** A date question in
  the survey now shows the same native date picker the wizard's date
  fields already have, and sends the picked date as the ISO value the
  backend expects. Typing today-words in the classic wizard keeps working.

## [1.113.0] — 2026-08-17

### Added

- **The owner's own sentence, read completely — with or without a model.**
  A request phrased the way people speak — "tomorrow I want 1800 jerricans
  of petrol of 25 l carried from the port of Rotterdam to Schiphol", said
  in Dutch — used to become a single piece whose description was the
  entire sentence. Three deterministic readers close
  the gap, so the guided mode every installation has out of the box reads
  it too: the intent words around the facts leave first ("ik wil … laten
  vervoeren", and their English forms); a date the sentence states — a
  word like tomorrow, whole-word only, or an explicit figure like
  20-12-2026 — answers the loading date; and the route reader learned the
  remaining openings (vanaf, vanuit, ab). The sentence now yields petrol
  × 1800 jerricans of 25 l (33,525 kg computed), loading date tomorrow,
  route port of Rotterdam → Schiphol, and one question: confirming UN
  1203. Pinned verbatim as a test, together with an explicit-date variant
  and the plant called morgenster staying goods.

## [1.112.3] — 2026-08-17

### Fixed

- **Details dropped from the fields are recovered from the lines.** The
  third measured intake shape: the same sentence, and this run the model
  returned no fields at all — every consignment detail arrived as a goods
  line instead. A line that opens with a route word, a carrier word or an
  order word is a detail: it is recovered into the field it names (still
  guarded by the traceable-to-the-message check) and never becomes a
  package. With that, all three measured shapes of the small model land on
  the same result: one goods line "diesel × 1000 jerricans" and the
  parties, route and reference in their fields — the deterministic floor
  decides, whichever way the model bends.

## [1.112.2] — 2026-08-17

### Fixed

- **Details re-listed as goods never become packages.** The re-measurement
  after v1.112.1 showed the next failure shape: asked to keep the
  consignment details out of the goods descriptions, the model emitted them
  as *extra goods lines* instead — the consignor, the destination, the
  carrier and the reference, each as a "package" of one. A goods line the
  majority of whose substantial words already sit in the extracted field
  values is details, not goods, and is dropped; a count the model repeats
  inside the description ("1000 jerricans diesel", quantity 1000) leaves
  the description too. Both measured shapes are pinned as regression
  tests; the intake prompt now also says the details must not be repeated
  as goods items.

## [1.112.1] — 2026-08-17

### Fixed

- **The intake measured, and repaired where it bent.** The
  `measure-assistant-latency` run on the pinned runtime timed the new
  intake shape at 12.8 s and read the parties, carrier, route and
  reference correctly — but returned the *whole* sentence as one goods
  description with no quantity. The deterministic readers now stand under
  the model's output exactly as they stand under typed input: the route
  phrase is cut from a returned description (and kept when the fields are
  still open), and a leading count without a unit word still counts
  pieces. The measured degradation is pinned as a regression test, and the
  intake prompt now says outright that a goods description names the goods
  only.

## [1.112.0] — 2026-08-17

### Added

- **The intake reads everything the sentence states.** Owner expectation,
  verbatim in spirit: a language model should be smart enough that whatever
  the first message already says — addresses, parties, counts, dates,
  references — is never asked again, while whatever it does not say still
  is. With the local model installed, the first message now goes through
  one intake extraction: goods lines plus every consignment detail the
  sentence explicitly states — consignor, consignee, carrier, loading and
  discharge point, loading date, order and booking references. Each lands
  in the same document fields the wizard writes, only where still empty,
  and the question for it never comes; everything unstated is asked exactly
  as before.
- **The locks hold, extended.** The intake may fill a fixed whitelist of
  party, route and reference fields and nothing else — never a regulatory
  value; UN numbers and classifications still go through the pipeline's own
  recognition. Every value must be traceable to the message itself (at
  least one substantial word of it occurs in the sentence), so an invented
  consignee is refused; a date must parse or it is dropped; nothing typed
  earlier is ever overwritten. All of it pinned by tests with a fake model
  that tries to smuggle in a consignee, a UN number and a non-date.
- **Without a model everything works as before**: the deterministic route
  reading ("from X to Y"), the count and content reading, and the survey
  asking what is open. The `measure-assistant-latency` workflow gained the
  intake shape so its cost on the pinned runtime is measured, not guessed.

## [1.111.0] — 2026-08-17

### Added

- **The consignment note explained at the field.** The owner supplied the sVa
  booklet "De vrachtbrief; goed geregeld" (Stichting Vervoeradres, 2004), the
  box-by-box explanation of the CMR/AVC consignment note. Its teachings now
  sit as short digests behind the info marks of the matching questions, in
  all four languages — in the wizard and in the assistant alike: the
  consignor is the carrier's counterparty and not the loading address, and
  answers for a truthfully completed note; the consignee becomes party to
  the contract on delivery; the carrier's liability starts at the place and
  date of taking over (box 4) and compensation is computed on the value
  there; delivery is as precise as box 3 is; documents handed over travel at
  the consignor's risk when missing and the carrier's when lost (box 5);
  instructions must be timely and are binding (box 13); prepaid against
  collect and who stays debtor (box 14); the COD amount in figures and words
  with its domestic cap (box 15); a successive carrier becomes liable for
  the whole transport (box 17); a written delivery term doubles the
  domestic delay limit (box 19); and the place and date of drawing up can
  start the limitation clock (box 21). Pallets and roll containers are not
  packages — that note now sits on the package-count question too (box 7).
  A test holds the bar: every question the CMR can raise carries help in
  all four languages.

### Fixed

- **The notify party left the CMR.** A notify party is a sea-carriage
  concept: the party the shipping line informs when the cargo reaches the
  discharge port. The field sat in the shared parties section without a
  condition, so every shipment was asked for it — road included — while no
  document printed it. It now lives on the B/L shipping instructions alone,
  with a help text saying what it is and that a CMR has no such box.

## [1.110.0] — 2026-08-17

### Fixed

- **A hundred plates weighed 78.5 kg.** Owner ride: a hundred bundled steel
  plates of 2000x1000x5 mm, from an address in Wezep to the port of
  Rotterdam, described to the assistant in one Dutch sentence and judged on
  the CMR it produced. Three defects, all repaired at the level where they
  showed:
  - A count with no unit word ("100 steel plates") was swallowed whole — the
    sentence became one piece. A leading count followed by an ordinary word
    now counts pieces, and the word stays with the goods: 100 pcs, 7850 kg.
  - The route stayed glued to the goods description. "from X to Y" at the
    end of the sentence — in any of the four languages — now answers the
    loading-point and discharge-point questions before they are asked. Both
    halves must be present, so a phrase naming the contents of a package
    ("of 25 l") is never read as a route.
  - The nature of goods read **"Onbekend 2000x1000x5 mm"**. Twice wrong: the
    plural "platen" was not recognised where "plaat" was (plurals in all
    forms are now), and an unrecognised shape substituted the word "Unknown"
    for the consignor's own words — it now keeps what was typed, which
    always says more than "Onbekend".
- **Numbers on the forms print as numbers.** The goods row read "100.0 ×"
  and the weight "7850.0"; the artificial decimal from the calculation no
  longer reaches the CMR or the CIM. The ride now puts
  "100 × Plaat 2000x1000x5 mm", 7850 kg and 1 m³ on the paper.

## [1.109.1] — 2026-08-17

### Changed

- **Documentation pass against the current release.** The roadmap and the README
  claimed all six transport modes were released while the application releases two:
  both now say plainly that road and inland waterway are out and that rail, sea, air
  and multimodal stay locked until their checks are complete — and the roadmap names
  that unlocking as planned work, mode by mode. The user guide caught up with the
  wizard it describes: documents are advised on the export step rather than chosen up
  front, the name-recognition chips, the contents-per-package reading and the
  open-questions principle are described, and the AI assistant has a section of its
  own. The documents page lists the ADR/ADN sheets and lists the registry actually
  offers; the privacy page names the assistant's one-time model download as the third
  outbound connection, admin-triggered and SHA-256-verified.
- **The roadmap looks further ahead.** Planned: a "what's new" dialog on the first
  start after an update, an automatic update check with an unobtrusive notification
  (behind the outbound-connections switch), and updating from inside the application
  where the installation allows it. And companion modules, each in its own repository,
  talking to EMCargo over its API: a route planner, container handling in 3D, and a
  military transport module kept strictly outside the civilian core.

## [1.109.0] — 2026-08-17

### Added

- **The assistant suggests addresses and locations, like the wizard does.**
  An address question in the survey now carries the same address search the
  wizard's own address fields have (the Photon-compatible API an
  administrator configures, off means off), and a location question
  (loading point, discharge point, place of receipt or delivery, final
  destination) suggests airports ✈, ports ⚓ and stations 🚆 from the
  built-in catalogue — filtered by the transport mode, with street
  addresses offered alongside for road and multimodal. The very same
  components the wizard renders, so the suggestions, their look and the
  administrator's settings are one and the same in both places. Free text
  always remains possible; a picked address lands multi-line in an editable
  box before it is sent.

## [1.108.1] — 2026-08-17

### Fixed

- **A skipped question stayed skipped for exactly one turn.** Owner report:
  "steel plate" asked for its dimensions, then for the consignor — and then
  for the dimensions again, after every following answer, swallowing
  whatever was typed as an answer to a question it re-raised. The server is
  stateless and the modal rebuilds the state from the wizard on every turn;
  the wizard carried everything of that state *except* the skipped
  questions, so every skip was forgotten the moment the next answer was
  sent. The skips now travel with the rest of the state, both ways. The two
  mapping functions moved to their own module (`utils/assistantState.ts`)
  with a round-trip test, so the next field added to the state has one
  obvious place to be carried — and a test that fails when it is not.

## [1.108.0] — 2026-08-17

### Fixed

- **Two kinds of goods in one sentence are two lines.** "1000 jerricans of
  petrol and a pallet of sand-lime brick" became a single line — description
  "petrol and a pallet of sand-lime brick", 1000 jerricans — and the second
  consignment simply disappeared. A sentence is now cut wherever a separating
  word (and, plus, a comma) is followed by a count, a unit the catalogue
  knows and a description of its own, so "of 25 l with petrol" and "at 200
  litres each" still stay part of the item they belong to. An article counts
  as one: "a pallet of sand-lime brick" is a line of one pallet.

### Added

- **The assistant asks about the goods, not only about the regulations.**
  Four pallets of sand-lime brick used to travel from the first sentence to
  the consignor's name without a single question, while the pipeline had
  already reported "dimensions_missing" and the catalogue already held the
  density. The measurements the calculation itself named as missing are now
  a question source of their own — one optional question, in lay language,
  naming which goods it is about — and the answer turns that line into
  6144 kg and 3.84 m³ on the spot. For goods the catalogue does not know,
  the weight per item is asked instead, because no measurement can produce a
  weight without a density.
- **A count of packages with a known content is a weight.** Since v1.107.0
  the contents of one package are read from the sentence; a thousand
  jerricans of 25 litres is 25000 litres, and with the density from the
  catalogue that is 18625 kg of petrol. The same answer given to the
  dangerous goods step ("25 L" per package) now feeds the goods line too, so
  the same fact is never asked twice. The packaging around the contents is
  not known, so the loading volume stays open rather than claiming the
  volume of the liquid — and that is exactly what the optional measurement
  question then completes.
- **The model reads what patterns cannot.** A measurement written as prose
  goes to the language model when one is installed, under a schema of three
  numbers; every number it returns is validated here before it reaches a
  line, and an answer the patterns can read never reaches the model at all.
  As always the model only reads — it decides nothing, and without a model
  every step above works exactly the same.

### Changed

- Derived values never travel back in as answers. A weight per package
  rounded to 18.62 kg, fed in again as an override, turned 18625 kg of
  petrol into 18620; computed weights are now kept apart from the ones the
  consignor stated, and only the latter count as input. Measurements
  answered through the assistant land in the same columns the lines table
  writes, so the classic wizard computes with them too.

## [1.107.0] — 2026-08-16

### Added

- **The content per package is read from the sentence.** "1000 jerricans of
  25 l with petrol" already says what one jerrican holds: the pipeline now
  detects that phrase on any line counted in packages — jerricans, drums,
  IBCs, bags alike — fills the net quantity per package from it, computes
  the 1.1.3.6 total, and keeps the goods description clean ("petrol", not
  "of 25 l with petrol"). The question the assistant used to ask for that
  number is no longer raised, because it is no longer open.
- **The packaging kind becomes a question.** A jerrican is a shape, not a
  specification: where the package is still a bare word, the catalogue's
  kinds of that word (steel 3A1 against plastic 3H1, and so on) are offered
  as an optional choice, and the chosen code supplements the description on
  the document per 5.4.1.1.1 (e).
- **Questions in lay language.** Every question the assistant asks now
  carries a plain-language phrasing a first-time consignor understands
  ("How much is in one package? For example: 25 L"); the formal field name
  and the help text with its article references sit behind an info mark on
  the question screen.
- **Corrections and follow-ups.** A wrong answer is corrected with the
  attempt named ("'by submarine' is not one of the possible answers"); a
  vague amount gets a follow-up with an example of a computable answer
  ("25 L"), a bare number where the unit matters is not accepted, and a
  typed date is understood day-first (16-08-2026) or asked again. Nothing
  is written to the consignment on any of these paths.
- **The survey pursues complete documents.** After the required fields the
  assistant now offers every optional field the selected documents can
  carry — each one skippable — so a consignment can reach "ready" with the
  papers genuinely filled in, not merely valid.

## [1.106.0] — 2026-08-16

### Changed

- **The assistant is a survey now, not a chat.** Owner feedback on v1.105.0:
  no chat transcript, no box on the modality page. The assistant lives in a
  modal, opened and closed with its own AI mark in the wizard header, and
  asks one question per screen — the answers as selectable options, free
  fields as a single input, optional questions with a skip. A *previous*
  button really goes back: the server is stateless, so the modal keeps a
  stack of snapshots and going back restores the wizard state taken before
  that answer was applied — re-answering a question is replaying from an
  earlier state, not editing history. The describe-your-shipment box left
  the modality page with the chat; describing the shipment is now the
  modal's first screen. Everything underneath is unchanged: the same
  stateless `/assistant/step`, the same three question sources, the same
  four locks on the model.

## [1.105.0] — 2026-08-16

### Added

- **Chat-first.** The modality page gains a describe-your-shipment box:
  type "1000 jerrycans of diesel from Rotterdam to Duisburg", pick the
  transport mode, and the wizard opens with the assistant already working
  on that sentence. Typing nothing changes nothing.
- **The latency figures are measured, not guessed.** The
  `measure-assistant-latency` workflow installs the exact pinned runtime on
  a standard 4-vCPU runner and times the assistant's two real extraction
  shapes. First run, with Qwen3's default thinking mode: 31–36 seconds per
  turn, and one paraphrase mapped onto the wrong option. Two fixes came out
  of that measurement: the runtime now starts the server with reasoning
  off, and a deterministic reverse match answers a paraphrase that contains
  an option's own word before the model is consulted at all. Second run, as
  the runtime really starts: model loaded in 2 s, free prose split into two
  correct goods lines in 5.9 s, a paraphrase mapped — correctly — in 2.1 s,
  ~2.4 GB RSS. The README carries the figures and the workflow that
  reproduces them.
- **The assistant's archetypes run over the real API**: the diesel ride and
  a plain steel consignment, end to end through `POST /api/assistant/step`
  in deterministic mode — the mode every installation has.

## [1.104.0] — 2026-08-16

### Added

- **The local model, as an opt-in download.** Nothing ships in the image:
  when an admin enables the assistant in Settings, the llama.cpp server
  binary for this machine's architecture and the Qwen3-1.7B model (official
  publisher, Apache-2.0) download once into `/data/assistant` — each
  verified against a SHA-256 pinned in the repository, and the pins are
  facts: the `pin-assistant-sources` workflow downloaded and hashed the
  artifacts on a runner, both architectures (amd64 and arm64) included. A
  mismatch removes the file; an unpinned source refuses to download at all.
  The server runs as a managed child process on localhost; the download is
  the assistant's only external traffic, and removing the model is one
  button.
- **What the model may do is grammar-bound.** Every model call is
  constrained to a JSON schema by llama.cpp's grammar support — output
  outside the schema cannot exist. The model does exactly two things: split
  free prose into goods rows for the same pipeline the wizard uses, and map
  a paraphrased answer ("it goes in a tank vehicle") onto one of the
  question's own options through an enum whose only escape is "unclear",
  which re-asks. Any model failure falls back to the deterministic chain;
  the assistant can never be taken down by its model, and the model can
  never widen what is asked or answered.
- Footprint with the model installed: ± 2.5 GB extra RAM, ± 2 GB disk. The
  sources and their pins are documented in `docs/data-sources.md`.

## [1.103.0] — 2026-08-16

### Added

- **An assistant on the wizard — deterministic first.** A chat panel
  (toggle in the wizard) that handles the whole consignment in natural
  language: "1000 jerrycans diesel" becomes a goods line through the same
  pipeline the lines step uses, the name recognition's candidates come back
  as a question to confirm, and from there the conversation asks exactly
  what the backend itself has open — the open questions of `dg/prepare`
  (options included, answer chips attached) and the required document
  fields of the registry, one per turn. Answers match the stored value and
  its labels in every language ("colli" answers "packages"), "today"
  answers a drawn-up date, optional questions can be skipped, required ones
  cannot. Everything lands in the same wizard state, so switching between
  chat and form can never lose data.
- **No model, by design — yet.** This phase is the deterministic floor of
  the assistant: parser, name recognition, open questions and four-language
  texts carry a complete conversation from first sentence to "ready to
  download" without any language model. A local model (next phase) will
  only read free text more flexibly; it can never change what is asked or
  answered, because the orchestrator owns both lists. The server stores
  nothing of the conversation: the wizard state travels with each request
  and returns patched.

## [1.102.0] — 2026-08-15

### Added

- **The most applicable name, chosen by the consignor (3.1.2.2).** Where a
  position combines several proper shipping names — UN 1202 is DIESELOLIE or
  GASOLIE or STOOKOLIE, LICHT — the provision, read from page 421 of the
  Dutch edition, says only the most applicable one goes on the transport
  document. The DG step now asks that choice as an open question, offering
  exactly the capital-printed alternatives of the read name columns (3.1.2.1:
  the capitals are the name; the lower-case qualifiers are not). A Dutch
  document asks the English counterpart beside it, the way 5.4.1.4.1 is
  served; German and French names stand alone; an English-only profile asks
  the English choice only. The chosen name replaces the whole column on the
  document — "UN 1202, DIESELOLIE (DIESEL FUEL), 3, III, (D/E)" instead of a
  ~600-character line — and only names this application wrote itself are ever
  replaced; the consignor's own wording stands.
- **The jerrycan exists.** ADR defines it by name (1.2.1) and P001 admits it
  to 60 litres as a single packaging; now the goods step can count in them
  and the DG step carries them to the document. The packaging code joins the
  description the way 5.4.1.1.1 (e) words it — "jerrycan (3H1)", a code only
  as a supplement, never alone.
- **"diesel" finds UN 1202.** The exact-name lexicon stays as it was; a
  fallback now matches a typed word that is the exact first word of a printed
  name ("DIESEL FUEL") or a near-complete single-word name ("DIESELOLIE"),
  only when the exact pass found nothing and with a tighter candidate limit.
  "benzinemotor" still matches nothing.

### Fixed

- **The CMR goods box no longer clips the description.** A line longer than
  the row continues on the following rows, so packing group and tunnel code
  stay on the paper — 5.4.1.1.2 requires the information on a transport
  document to be legible, and a clipped line is not.

## [1.101.0] — 2026-08-15

### Added

- **The tank density comes from where it is already known.** The consignor
  was being asked for the relative density of petrol at 15 °C as if everyone
  knows it — while table C of the read ADN edition prints a density for 329
  of its 678 rows. For a tank consignment the app now pulls that column:
  one clean printed number fills d15 (visible in the summary, editable), a
  printed range or bound ("0,68 - 0,72", "< 0,85") is shown as the book
  gives it and never averaged into an answer. The note names the source and
  the caveat in one breath: the value is the book's, the product is yours —
  check the safety data sheet (section 9), which also gives d50. The density
  field helps now say where to find the figure instead of assuming it is
  known.

### Changed

- **The app speaks of goods, and to the consignor.** The first wizard step
  was called "Colli"; it is now "Goods" in all four languages, and the
  general entry texts follow ("add at least one goods line"). The word
  *package* stays where the regulation itself uses it — the DG quantity
  fields of 5.4.1.1.1 keep their regulatory names. The modality page and the
  coverage documentation now say the role out loud: the person at the
  keyboard is the consignor; the driver and the boatmaster never draw these
  documents up — they receive them, carry them and, where a provision says
  so, sign them on the spot.

## [1.100.0] — 2026-08-15

### Changed

- **The wizard starts with the shipment, not with paperwork.** The forms
  step is gone: the first question used to be "which of eight documents do
  you want?", asked before the application knew what was being shipped —
  while the document choice is the best derivable answer of the whole
  wizard. The steps are now cargo lines → dangerous goods (when there are
  any) → shipment details → documents.
- **The document pack is assembled, in three honest groups.** *Required* is
  reserved for what a read provision carries: with dangerous goods on board,
  5.4.1 requires a transport document with the prescribed particulars, and
  the registry names which document that is per modality (CMR, CIM, IMO
  declaration, ADN transport document, IATA declaration). The DG support
  papers and the customary transport document are *recommended*; the rest is
  *possible*. Required and recommended are pre-selected; the selection
  follows the shipment until the user touches it — a DG line appearing pulls
  the DG papers in — and from that moment it is theirs. One button downloads
  every document that is ready; drafts stay behind, visibly, so an
  incomplete paper is never buried in a bulk download.

### Added

- **Three prefills that end retyping.** "Drawn up on" dates start as today
  (each field defaulted at most once, so a cleared date stays cleared; the
  operational loading and departure dates are never guessed). The previous
  shipment's details can be reused with one button, filling empty fields
  only and never dates. And the discharge point defaults to the consignee's
  own address line when the details step is done — only while the user typed
  nothing else.

## [1.99.0] — 2026-08-15

### Changed

- **The DG step shows answers as answers and questions as questions.** With a
  UN number in place, the twenty-odd fields of the step used to stand open as
  if each were work to do, while the derivation had already answered most of
  them. The step now shows a summary of what was derived — name, class,
  packing group, tunnel code, transport category, quantities — and asks only
  what `dg/prepare` names as genuinely open: facts of the consignment no
  table can supply. Each question carries the reason it is asked ("decides
  admission, tunnel code and placarding"; "special provision 274 — technical
  name required"). The full form did not disappear: it is one button away,
  per product, and it remains the default while the UN number is still the
  question.
- **The special cases live behind one door.** Waste, empty uncleaned,
  salvage, molten, UN 3509 residues, the 2.1.2.8 statement and
  containers-only are one collapsed section, closed by default and
  summarised as "none apply" until one is. The answer is "none" on nearly
  every consignment, and eight always-open selects made the step look like
  eight questions.

### Added

- **`dg/prepare` names the open questions.** Per product, computed after
  everything derivable is in, so a value the cargo line or the table already
  supplied is never asked again: the mode of carriage (it decides what every
  other answer means), the SP 274 technical name, the net explosive mass of
  class 1, where on board for ADN dry cargo, the density for the degree of
  filling of a tank, what the IMDG document and the IATA declaration require,
  and whichever half of count × contents the 1.1.3.6 total still misses.

### Added

- **Dangerous goods are recognised by name.** Whoever types "20 vaten
  benzine" on the lines step has told the application everything it needs to
  find UN 1203 — the four-language name index has known the substance all
  along — yet until now only a literal "UN 1203" in the text was recognised.
  The pipeline now consults its own lexicon, built from the capital-printed
  names of the four language columns: the book prints the name proper in
  capitals and its qualifiers in lower case, and exactly the capital part
  matches, as whole words. So "benzine" finds UN 1203 and "benzinemotor"
  finds nothing, and an aluminium tube stays an aluminium tube — "ALUMINIUM,
  GESMOLTEN" is capital-printed as a whole and matches only as a whole. No
  trade names or synonyms are invented: a word matches only if an edition
  prints it as the name.
- **Recognition is a suggestion, never a decision.** The line shows a chip —
  "Recognised: UN 1203 (class 3)" — and asks. Confirming sets the dangerous
  goods tick *and* carries the UN number through to the DG step, so nothing
  recognised is typed twice; rejecting puts the suggestion away for that
  line. Where the text is ambiguous ("zwavelzuur" is UN 1830 above 51 % acid
  and UN 2796 up to it) the chip offers a button per UN number and decides
  nothing. A silent classification on the strength of a word in free text
  would be answering for the consignor; the consignor stays the one who
  answers.

### Fixed

- **Ticking the dangerous-goods box no longer wipes the calculation.** Any
  change to a line cleared the computed weights, including changes that do
  not affect them; ticking DG (or answering the new suggestion) now keeps
  the result on screen.

## [1.97.0] — 2026-08-15

### Added

- **The fifth archetype: bulk by road.** Sulphur loose in a sheeted vehicle,
  end to end through the API a wizard actually calls — the BK and VC codes on
  the answer and on the paper, the tank checks silent, the refusal for a
  liquid pinned. And the downloads of v1.91.0–v1.96.0 join the e2e: the tank
  vessel line of 5.4.1.1.2, the packing certificate, both on-board lists and
  the equipment sheet, each rendered through the real export route in two
  languages.
- **`docs/dg-coverage.md` carries the final state.** The driver's and
  boatmaster's table now lists nine documents; the on-board documents list is
  named for what it is — the split between "here are your documents" and
  "this part you must bring yourself", itself a document since v1.93.0.

This closes the completion plan (phases 13–15). What stays open stays with
its reason recorded: ADN 8.6.4 until a degassing operation exists, IATA and
IMDG texts until they are freely published, and everything that is the
vehicle, the vessel or the route itself.

## [1.96.0] — 2026-08-15

### Added

- **Bulk admission answers the railway under its own name.** RID 7.3.1.1,
  7.3.2.1 and 7.3.3.1 were read in the OTIF English edition (printed pages
  1092–1095) and the German edition (1176–1179), which agree: the ADR's
  provisions word for word, wagons in place of vehicles, the same BK/VC/AP
  codes. Same answer — but a rail consignment now gets it at all (it got none),
  the CIM cites `RID 7.3.1.1`, and the VC meanings speak of wagons, as that
  edition does. The same split the compatibility table and CW 28 already make.
- **The equipment sheet (ADR 8.1.4/8.1.5).** Derived since v1.53.0 and shown
  on screen since — and the person who needs it is standing at the open door
  of a cab, not at a browser. The list is now paper: one line per item with
  the provision beside it, the hazard labels of the load named as the basis
  (8.1.5.1), the fire extinguisher line carrying the three mass rows of
  8.1.4.1 because the unit's maximum mass is the vehicle's property. A
  checklist with nothing ticked: what actually lies in the cab this
  application cannot see, and the sheet says so.

## [1.95.0] — 2026-08-15

### Added

The description line closes. Read in the UNECE English and French volumes II
and the RID German edition (printed 266–267 / 293 / 909), which agree; the
Dutch words came with the fase-8 reading.

- **Molten substances (5.4.1.1.23).** A substance solid by 1.2.1, offered
  molten, carries the qualifying word as part of the name — GESMOLTEN /
  MOLTEN / GESCHMOLZEN / FONDU, in the document's language, and never doubled
  where the name already says it (UN 2448 SULPHUR, MOLTEN).
- **UN 3509 (5.4.1.1.19).** The name is complemented with "(BEVAT RESTEN VAN
  …)" and the residues' classes in class order, and 5.4.1.1.1 (f) does not
  apply — no total quantity for residues nobody has weighed. The residues
  field shows only for UN 3509.
- **Classified per 2.1.2.8 (5.4.1.1.20).** The prescribed statement, worded as
  each edition sets it — the German in its own capitals.
- **Special provision 274 is enforced.** Column (6) carries it on 816 rows:
  an N.O.S. entry must supplement its name with the technical name (3.1.2.8.1).
  The builder has appended that name since the field existed — for the
  consignor who filled it in; now the one who did not is told, on the panel
  and on the document, that "UN 1993 FLAMMABLE LIQUID, N.O.S." with empty
  brackets is a description the provision calls incomplete.

## [1.94.0] — 2026-08-15

### Added

- **The fourth reading settles the last three cells of the tank hierarchy.**
  The French volume II — the treaty's other authentic language — was read
  verbatim on the three cells no two of the first three readings agreed on
  (printed pages 220–223). It sided with the Dutch on **L10BH's** group: 18
  codes, CF2, CW1 and CW2 included, CT1 with its footnote. It sided with the
  German on **L10DH's** inheritance: the chain runs through L10CH. And on
  **S10AH** it confirmed the nine codes both other editions carried — the
  strays of those readings spell the inheritance sentence (S, G, A, V is SGAV
  leaking into the cell). **All eighteen codes of 4.3.4.1.2 are settled on
  every cell**, and the fit check no longer declines anywhere.
- **ADN 7.1.5.0.2 is applied.** The thresholds were read in v1.64.0 and sat
  recorded until the input the provision itself requires existed: the
  consignor's statement that the goods travel exclusively in containers (the
  new `containers_only` field), never inferred from a packaging type. Chlorine
  below 30,000 kg gross drops from two cones to none; above it keeps both;
  declared without the gross mass the threshold compares against, the full
  signals stand and the answer says why — over-signalling is the safe
  direction.

### Unchanged, on purpose

- **ADN 8.6.4**, the degassing checklist, stays unregistered: it is the same
  kind of printed model as 8.6.3, and there is no degassing operation in the
  application to hang it on. Registering the model without the operation would
  be a document in search of a consignment; the coverage document records the
  reason.

## [1.93.0] — 2026-08-15

### Added

- **The container/vehicle packing certificate (ADR 5.4.2) as a document.**
  Where carriage of dangerous goods in a container precedes a sea voyage, the
  certificate of IMDG 5.4.2 must be provided to the maritime carrier — and the
  ADR prints the IMDG's nine declarations in its own footnote to 5.4.2 (read on
  printed pages 1002–1004 of the Dutch edition), which is what makes this
  buildable from a free official text. The application had it as a single
  checkbox; a checkbox is not a document anyone can hand to a carrier.
  **Nothing on it is pre-ticked**: every declaration concerns what was
  established at packing — the container clean, damaged packages left behind,
  drums upright — and a certificate this application had already ticked would
  claim knowledge it cannot have. Not required for portable tanks, and the
  document says so.
- **The on-board documents lists (ADR 8.1.2 / ADN 8.1.2).** Both regimes list
  the papers that must travel — in the driver's cab, on the vessel — and the
  list is split by who can produce each: what this application drew up
  (transport documents, instructions in writing, the stowage plan), and what
  it never can (the certificate of approval of 9.1.3 or 1.16.1.1, the driver's
  8.2.1 certificate or the ADN expert of 8.2.1.2, photo identification of
  1.10.1.4, the inspection certificates and the measurements log). Naming
  those next to the generated papers is the difference between "here are your
  documents" and "here is everything the regulation asks, and this is the part
  you must bring yourself". Read from printed page 1431 of the Dutch ADR and
  8.1.2 of the Dutch ADN edition.

## [1.92.0] — 2026-08-15

### Added

- **Admission to carriage in bulk (ADR 7.3.1.1).** The columns have been in
  the seed since v1.65.0 — the BK codes inside column (10), the VC and AP codes
  of column (17) — and nothing computed with them: a bulk consignment got no
  admission answer where a tank load has had one since v1.66.0. Read in the
  official Dutch edition (printed pages 1398–1403) and the UNECE English and
  French volumes II, which agree. A **BK code** admits the goods to bulk
  containers under the conditions of 7.3.2; a **VC code** admits them to
  sheeted or closed vehicles and containers with any **AP provisions** of
  7.3.3.2 alongside; **neither means no**, full stop — with 7.3.1.1's own
  exception for empty uncleaned packagings named beside the refusal rather
  than granted, because it turns on what the packagings contained.
- Every code travels with its read meaning, and the equipment conditions of
  7.3.2/7.3.3 travel as conditions — the application cannot see the container
  that turned up at the ramp. Both the refusal and the permission reach the
  document: the codes are what the loader checks the container against. Panel
  card beside the tank admission, four languages, 11 tests.

## [1.91.0] — 2026-08-15

### Added

- **The tank vessel transport document (ADN 5.4.1.1.2).** A cargo tank
  consignment used to get the packages line of 5.4.1.1.1, and the two are
  different document entries. The provision — read on printed page 349 of the
  UNECE English edition — takes its data from **table C**, in the repository
  since v1.73.0: (b) the name of column (2) in the language of the document,
  (c) the data of column (5) with the numbers after the first in brackets, (d)
  the packing group, (e) the mass in tonnes. The composed line is the ADN's own
  example: `UN 1203, MOTOR SPIRIT OR GASOLINE OR PETROL, 3 (N2, CMR, F), II,
  250 t`. No tunnel code and no package count — the one is a road construct,
  the other is the other chapter. Litres do not convert to tonnes without a
  density this application does not presume to apply, so only a mass does.
- **The document remarks of column (20), named (5.4.1.1.2 (h)).** Six numbered
  remarks — 3, 17, 22, 39 (b), 42 and 47 — put information in the transport
  document. Their text lives in 3.2.3.1 and is not held here, so the export
  says which remark asks rather than guessing at what it asks for.
- Where the rows of a substance disagree on column (5), or table C does not
  list it, nothing is invented: the substance's own class stands alone — which
  is what 5.4.1.1.2 (c) itself prescribes for goods not mentioned by name —
  or the packages description remains as the least-bad line while the
  admission check of 3.2.1 refuses the carriage.

## [1.90.0] — 2026-08-15

### Added

The special cases of 5.4.1.1 that change what the description line must say —
read in the official Dutch edition (printed pages 991–996), the UNECE English
and French volumes II, and the RID German edition, which carries the provisions
word for word. None of them can be derived: whether the goods are waste is a
fact about the consignment, not about the UN number, so each is a field.

- **Waste (5.4.1.1.3).** The word precedes the proper shipping name unless the
  name already says it — the provision's own example is
  `UN 1230 AFVAL METHANOL, 3 (6.1), II, (D/E)`. The word follows the language
  of the *document*: AFVAL / WASTE / ABFALL / DÉCHET, and always English at sea
  and in the air.
- **Empty uncleaned (5.4.1.1.6.1).** "LEEG, ONGEREINIGD" joins the description,
  and 5.4.1.1.1 (f) then does not apply — so the total quantity is dropped
  rather than composed for residues nobody has weighed. The fuller
  substitutions of 5.4.1.1.6.2 are permissions, not requirements; the form
  always allowed is the one composed.
- **Salvage packagings (5.4.1.1.5).** Two words for two provisions:
  BERGINGSVERPAKKING (4.1.1.19) and BERGINGSDRUKHOUDER (4.1.1.20), after the
  description. An unknown value is refused at the API edge rather than rounded
  to the packaging word.
- **Environmentally hazardous (5.4.1.1.18).** The additional entry
  MILIEUGEVAARLIJK on the land documents — except UN 3077 and 3082, whose names
  already say it, and except at sea, where the provision itself points at
  "MARINE POLLUTANT" (IMDG 5.4.1.4.3), which the sea line already carries.

## [1.89.0] — 2026-08-15

### Added

- **The English proper shipping names are read from ADR 2025.** English was the
  last of the four languages still coming from an export of ADR **2023** — Dutch,
  German and French had all moved to the 2025 editions — and it is the one that
  goes *beside* the Dutch name on almost every document this application
  produces, and the only one permitted at sea and in the air (IMDG 5.4.1.4.1,
  IATA DGR 8.1.2.1). 2,344 UN numbers, 0.9987 agreement against the Dutch table.
- What the export cost, now measured rather than remembered. **Fourteen entries
  had no English name at all** — UN 3245 genetically modified organisms, UN 3374
  acetylene solvent free, UN 2807 magnetized material among them — and a German
  name went on the document in their place, which satisfies neither 5.4.1.4.1
  nor 8.1.2.1. **UN 1139 was cut off mid-bracket** at "Coating solution (". And
  the export **flattened the alternatives the ADR prints**: UN 1203 was
  "Gasoline" where the book sets "MOTOR SPIRIT or GASOLINE or PETROL". All of
  that is whole now, and the warning that used to fire on fifteen entries fires
  on none.
- One entry goes the other way and is handled rather than shipped: **UN 2857**'s
  name runs past the edge of the column and the 2025 reading comes back as
  "... (UN". A truncated name is not a name, so that one keeps the export's
  complete spelling — preferring the newer edition is not a reason to put half a
  name on a consignment note.

### Fixed

- **The name column was ordered by what a line said, not by where it sat.** Two
  fragments of one printed line — the UN number on the left, the name beside it —
  were sorted as `(y, text)` tuples, so whenever they shared a y they were
  ordered by their text. That is right by accident for most of table A, because a
  four-digit number sorts before a capital letter, and wrong for **every name
  that opens with a locant**: "1-PENTENE (n-AMYLENE)" sorts before "1108"
  because the hyphen is 0x2D and the digit 0x31. The row splitter opens a row at
  a line of four digits, so a name arriving before its own number was attached to
  the row above — **two entries damaged per occurrence**, the one that lost its
  name and disappeared and the one above it that kept the stray.
  The English reading went from 0.9817 to **0.9987** agreement, 2,304 to 2,344
  UN numbers.
- **And it had already shipped in French.** UN 1125 read "n-BUTYLAMINE
  1-BROMOBUTANE" in `adr_names_fr.json`, and 1126, 1702, 3023 and 3371 — exactly
  the four UN numbers that reading was missing — were the four names glued onto
  their predecessors. French is now 0.9996; German, which the defect never
  reached, is unchanged at 0.9996.
- **Hyphens the volume breaks are settled by two other readings.** Where a break
  falls inside one extracted line the end-of-line rule cannot see it: UN 1328
  came back as "HEXAMETHYLENETE-TRAMINE", UN 1239 as "METHYL CHLORO-METHYL
  ETHER". It goes the other way too — "TEAR-PRODUCING" landed on a break and lost
  a hyphen the name owns. Two readings that disagree are not an answer, and there
  is a third English reading in this repository: the IMDG Dangerous Goods List
  sides with the 2023 export on 54 of the 62 names in dispute and with the new
  reading on 3. So where those two agree with each other and the volume differs
  from them in nothing but hyphens, their hyphenation is taken and everything
  else stays as the book sets it. **49 names settle**; the 13 the two do not
  agree on are left as the volume reads them.
- `--explain` printed the first eight lines of the page an entry sits on, which
  is a picture of the table's top and almost never of the entry asked about —
  UN 1108 sits at y 308 and the trace stopped at 206. It now follows the number's
  own y.

## [1.88.0] — 2026-08-15

### Fixed

- **Every subsidiary label model was missing from the transport document.**
  5.4.1.1.1 (c) asks for the label model numbers of column (5), with the ones
  after the first in brackets; the RID's own example is
  `663, UN 1098 ALLYL ALCOHOL, 6.1(3), I`. EMCargo printed `6.1` and dropped
  the `(3)`. The cause was a separator: the 2023 export writes `6.1+3` and the
  Dutch 2025 edition writes `6.1, 3`, and the reader split on the plus alone, so
  the whole cell stayed one token. **718 of the 3,158 rows of that table carry
  more than one label model**, and each of them reached the paper a label short —
  UN 1005 anhydrous ammonia as `2.3` without its corrosive label, UN 0018 as
  `1.2G` without `6.1` and `8`. For class 1 the brackets now follow the text
  rather than the position: the models *other than* 1, 1.4, 1.5 and 1.6 go in
  them, which is a set and not an index. A labels cell that is not a model
  number — twelve rows read "See 5.2.2.1.12" and two spell out the word for
  "none" — falls back to the class of column (3a), as the last indent of (c)
  says.
- **The exporter composed its own description line.** Two renderings of one
  provision drift the moment either is corrected, and this release is the proof:
  the label models and the hazard identification number below would have reached
  the wizard and the stowage plan while the CMR and the CIM went on without them.
  There is one builder now; what stayed with the form is the part that is
  genuinely the form's — a tunnel code typed over the table's, and a description
  column that does not repeat the counts the form has columns for.
- **`ADR 7.5.2.1` was cited on a rail consignment.** The table is the same in
  both regimes — v1.38.0 read RID's 7.5.2.1 and found it identical, footnotes
  included — but the name is not. A code the RID does not have, printed on a
  CIM, is the same category of inaccuracy as the CV28 that used to appear there
  in place of CW 28.

### Added

- **RID 5.4.1.1.1 (j): the hazard identification number on the CIM.** Where a
  marking under 5.3.2.1 is prescribed, the number goes *before* the letters
  "UN", in the sequence (j), (a), (b), (c), (d) with no information interspersed.
  5.3.2.1.1 says when that is — tank-wagons, battery-wagons, wagons with
  demountable tanks, tank-containers, MEGCs, portable tanks and wagons or
  containers for carriage in bulk — read in the English edition and the German.
  For a full load of packages of one and the same substance the plate *may* be
  affixed, and whether a wagon was plated is not something this application can
  see: that case is asked rather than decided. Where the marking is prescribed
  and table A holds no number, the description is incomplete and says so. Rail
  alone: the ADR has no such paragraph — its (k) is the tunnel restriction code.
- **ADN 5.4.1.1.1 (j): the confirmation of stabilisation.** Where column (11) of
  the ADN's own table A carries ST01, the consignor certifies in the transport
  document that the substance was stabilized as the IMSBC Code requires for
  ammonium nitrate fertilizers (7.1.6.11), and in some States the bulk carriage
  needs the competent authority's approval as well. Two UN numbers carry it:
  1942 and 2067. UN 2071's ST02 is a condition on the carriage — a trough test —
  and not on the paper, and is deliberately not raised.
- **RID 7.5.2.4: limited quantities may not be loaded with explosives**, except
  division 1.4 and UN 0161 and 0499. Read on printed page 1103 in the English
  edition and 1187 in the German, which agree; there is no ADR equivalent. It
  needs no new data — which lines are packed in limited quantities is the 3.4
  check's own answer, taken from it rather than computed a second time, so the
  two cannot disagree about the same package.

## [1.87.0] — 2026-08-15

### Added

- **The degree of filling (ADR 4.3.2.2).** Read in the English volume II and the
  printed Dutch edition, which agree word for word. 4.3.2.2.1 gives four maxima
  for a tank carrying a liquid — 100, 98, 97 and 95 — all over `1 + α (50 − tF)`,
  with α = (d15 − d50) / (35 d50) from 4.3.2.2.2.
- **What decides which of the four is half read and half derived, and the seam
  is visible.** The tank's venting is the *fourth letter of the tank code* the
  consignor already types: N is a breather device or safety valves, H is
  hermetically closed without a safety device. That half is read. Whether the
  substance is toxic or corrosive is derived from the class and the subsidiary
  risks — so it is shown as a derivation, with the code and the reasoning, and
  can be overruled instead of believed.
- **Where the numbers are missing the formula is the answer.** Table A carries
  neither density, so α comes from the consignor: three new fields (the filling
  temperature and the densities at 15 °C and 50 °C, or α itself) turn the answer
  into a percentage, and without them the formula stands as a condition. A
  calculation whose inputs nobody has must not come back as a number.
- Above 50 °C the application says 4.3.2.2.3 has taken over — a flat 95 % ceiling
  and its own formula on two different densities — and does not compute with a
  formula that no longer applies. Classes 1, 5.2 and 7 go to 4.3.4.1.3, as the
  provision's own footnote does.

### Fixed

- **The tank fit check reached the panel and not the paper.** It shipped in
  v1.82.0 answering on screen only, which is the exact failure the tank
  admission check had before v1.66.0: a tank that does not fit, a fit the books
  could not settle and a fit that carries a condition now all appear as document
  warnings, with column (13) beside them. A plain fit does not — every document
  would otherwise grow a line saying nothing happened.

## [1.86.0] — 2026-08-15

### Changed

- **The tank hierarchy is read from three books, and now answers.** The German
  volume II joined the English and the printed Dutch edition, and a third
  reading did exactly what it is for: **seventeen cells** that no two readings
  had agreed on were settled by the two that agree, and the codes settled on
  every cell went from **seven of eighteen to fifteen**. Three are left —
  L10BH's group, L10DH's inheritance and S10AH's group — and those still make
  the check decline rather than guess.
- What that means at the desk: a tank the check could only shrug at now gets an
  answer. **SGAN, a tank for solids, refuses petrol** where before its group
  held a cell no two readings settled. And **petrol in an L1,5BN tank is a
  condition, not a refusal**: the plan for this check expected "does not fit",
  and the book says L1,5BN's group holds class 3 F1 packing group II *where the
  vapour pressure at 50 °C is at most 1.1 bar*. Whether this petrol meets that
  is not in table A, so the answer is the condition, named.

### Fixed

- **The German reading of 4.3.4.1.2 was empty, and the cause was a heading.**
  That edition heads the columns of *table A* with "Tankcodierung" and
  "Klassifizierungscode" too, so a reader looking for those started three
  hundred pages early and read table A instead. English and Dutch were saved
  only by the accident that their headings are unique to 4.3.4.1.2. The table
  is found by the provision's own number now — the one anchor that is not a
  phrase — with the headings kept as the fallback.
- A reader that comes back with nothing used to say only that. It can now
  report, per page carrying either heading, how many tank codes are on it and
  how many of its lines read as rows, which is the whole of what the page
  selection decides on.

## [1.85.0] — 2026-08-15

### Added

- **The four archetypes are a test, not an anecdote.** The plan for the dangerous
  goods work ended on a closing step: walk packaged goods by road, a road tank, a
  dry cargo vessel and a tank vessel from the goods to the last download, and see
  what comes out. Doing that by hand proves the day it was done; `test_archetypes.py`
  proves it on every commit. Each archetype asserts the checks that mode is
  entitled to *and* the ones it must not get — a tank vessel is not answered with
  the dry cargo vessel's chapter 7.1, a packages consignment is not asked about a
  tank — that the documents it needs render, and that what the application cannot
  say is said.
- The model verifier takes a provision, so the checklist of 8.6.3 could be cut and
  looked at rather than assumed. It confirms all four editions, the German one
  included: its range was measured but never seen, because that edition sets a
  running head on every line and the finder's content check had nothing to say
  about it. Every page is in range, and 8.6.2 and 8.6.4 are outside it.

### Changed

- **`docs/dg-coverage.md` says what the application does now.** It still claimed
  the ADN tank vessel regime was "entirely absent" and that tank codes were
  "outside the application", both untrue since v1.80.0 and v1.82.0. It now carries
  what the driver and the boatmaster actually get on paper, the two rules that
  govern it — a model the regulation prints is never rebuilt, and nothing
  prescribed is filled in for you — and what still has to be on board and cannot
  come from here.
- A new entry in the gaps table, ranked where it belongs: **the tank hierarchy
  declines on eleven of eighteen codes**. That is the honest cost of the
  two-reading rule, and a check that declines is safe but not useful.

### Fixed

- The page-range finder looked for 8.6.4's successor as a numbered provision and
  found the contents pages, reporting a twenty-page model. What follows the last
  provision of a part is the next part, and the part's own heading is what ends
  the model.

## [1.84.0] — 2026-08-15

### Added

- **The stowage plan (ADN 7.1.4.11.1).** Two readings of the provision, the
  printed Dutch edition and the English one, say the same short thing: the
  boatmaster sets down in a stowage plan which goods are placed in the
  individual holds or on deck, described there as 5.4.1.1.1 (a) to (d)
  describes them in the transport document. So the plan lists each hold and the
  deck with what is in it, and the descriptions come from the same function the
  transport document uses — "as in the transport document" is a requirement
  about sameness, and two renderings of one consignment that drift apart are
  worse than one rendering used twice.
- **7.1.4.11.2 for containers**: the container number stands in the plan, and
  the annex the provision requires — every container with its number and the
  description of what is in it — is drawn up with it.
- A position with no hold yet is not silently left out. It is listed last,
  where it cannot be missed, with the provision that asks for one.
- The plan says it is **not a drawing**. A vessel's holds have a geometry this
  application knows nothing about, and a picture of a ship that does not exist
  would be believed.
- Two fields on the dangerous goods step carry it: the hold (or deck) and the
  container number, shown for ADN and not for a cargo tank — 7.1.4.11 is a
  chapter 7.1 provision, and a tank vessel has no hold to be in.

### Changed

- **7.1.4.3.2 is applied now, not merely stated.** The prohibition on
  two-blue-cone goods sharing a hold with one-cone flammable goods needs a hold
  to compare, and until this release there was none: the finding could only say
  both kinds were on board. Where the holds are written down the provision is
  applied to what the boatmaster wrote, and the hold it is breached in is
  named. Where they are in different holds the finding says that too — and
  where nothing was typed it claims nothing.
- "dek" and "deck" are one deck, in all four languages the field might be
  filled in. A prohibition that a keystroke defeats is not a check.

## [1.83.0] — 2026-08-15

### Added

- **The placarding sheet (ADR 5.3).** EMCargo has derived chapter 5.3 since
  v1.53.0 and shown the answer on screen, which is where it stayed. The person
  who needs it is standing at the back of a trailer with plates in his hand,
  and a browser panel is not a thing you hold while doing that. The sheet lists
  the placards and the orange plates, each against the provision that asked for
  it, with the numbers already worked out — "33 / UN 1203" rather than a
  description of where to find them. It appears for road and multimodal
  consignments with dangerous goods, in all four document languages.
- The sheet says out loud that it is **not** a placard: a diamond off a laser
  printer is not one, and a sheet that looked like one would invite exactly
  that mistake. The placards and plates themselves have to meet 5.3.1.7 and
  5.3.2.2.

- **The ADN checklist of 8.6.3.** Before a tank vessel is loaded or unloaded,
  7.2.4.10 requires that checklist to be filled in and signed by the boatmaster
  and the shore facility, and the regulation *prints* it rather than describing
  it. So it is handed over the way the instructions in writing are: the model
  itself, cut from the edition in the document store, in the language asked
  for, or an honest "not here" naming the edition that would produce it. The
  card appears on the export step only for an ADN shipment that actually
  travels in cargo tanks — a dry cargo vessel does not fill this list in.
- EMCargo fills in nothing on that checklist. Every answer on it is agreed
  between the vessel and the shore at the moment of loading, and a form this
  application had already ticked would be a claim about a conversation that has
  not happened.

### Changed

- **A model is now addressed by its provision.** The instructions in writing
  were the only document the store served this way; 8.6.3 is the second and
  8.6.4, the degassing checklist, will be the third. The store's model lookup,
  the endpoint and the page-range finder all take a provision alongside regime
  and language, with each model's own title in the four languages the editions
  are published in. The 5.4.3 endpoint is untouched.
- The page ranges of the checklist were measured, one run per edition, and the
  register carries what measured them: English 491–495, French 513–517, Dutch
  858–863, German 941–945.

### Fixed

- **A tank load was told it needed no placards.** 5.3.1.5 picks placards by
  class and those findings carry one; 5.3.1.4.1 picks them because the load is
  in a tank, and that finding says so in `required` instead. The summary
  counted only the classed ones, so a tank of petrol reported "no placards
  required" directly underneath the finding that required them.
- **The environmentally hazardous mark inherited that error.** 5.3.6.1 hangs
  the mark on a placard being required under 5.3.1, so the miscount made the
  mark wrong for the same tank load.
- The placarding answer described itself as "computed for carriage in packages"
  whatever the mode of carriage was; it now says which it was computed for.

## [1.82.0] — 2026-08-14

### Added

- **The tank on the yard is now part of the question.** EMCargo showed the
  tank code column (12) *requires*; it could not say whether the tank actually
  standing there may carry the goods. That is the consignor's question, and ADR
  answers it in two provisions that share nothing but their purpose:

  - **4.3.3.1.2**, gases, is a hierarchy of *codes*: a substance under C\*BN may
    also travel in C#BN, C#CN, C#DN, C#BH, C#CH and C#DH, where the figure for
    \# is at least the figure for \*.
  - **4.3.4.1.2**, classes 3 to 9, is the rationalized approach and is not a
    hierarchy of codes at all: each tank code names the *group of substances* it
    may carry — class, classification code and packing group — and inherits the
    groups of the codes below it. The required code is never compared with the
    offered one; the substance is looked up in the offered code's group.

  A new field on the dangerous goods step takes the tank's own code, and shows
  only once the mode of carriage says a tank is involved. Petrol in an L4BN
  semi-trailer now comes back as a fit with the hierarchy step shown; an
  ammonia tank of the wrong family comes back as one that does not.

- **"Cannot be assessed" is an answer.** Where the reading of the regulation did
  not settle a cell the answer would rest on, the check says so instead of
  guessing in either direction — and it names which codes in the inheritance
  chain are unsettled. The same applies to a tank code the regulation does not
  name at all, which is what a typo on an approval document looks like.

- **The two hierarchies are in the repository, read from three books**: the
  English volume II, the printed Dutch edition and the German volume II. 15 of
  the 16 rows of the gas hierarchy are settled by more than one reading; of the
  18 tank codes of the rationalized approach, 7 are settled on every cell and 11
  carry a cell no two readings agree on, stored with every value read. Those 11
  are shortfalls of the readers, not disagreements between the books, and each
  one makes the check decline rather than answer.

- The regulation's own note travels with every answer: the hierarchy takes no
  account of the special provisions of 4.3.5 and 6.8.4 — column (13) — so where
  the substance carries any, they are named. One of them can require equipment
  the hierarchy knows nothing about, and another can switch the hierarchy off.

- A condition inside the packing group cell is part of the permission and is
  shown as one: LGBF admits packing group II of class 3 F1 only where the
  vapour pressure at 50 °C is at most 1.1 bar. For gases the required test
  pressure is usually printed as **x** in column (12) — it comes from the table
  of 4.3.3.2.5, which this application does not hold, and the answer says so
  rather than comparing a figure that is not there.

## [1.81.0] — 2026-08-14

### Added

- **A reader for the two tank hierarchies of ADR 4.3.** Table A column (12)
  says which tank code a substance requires; it does not say whether the tank
  standing on the yard may carry it, which is the question a consignor actually
  has. ADR answers it twice, and the two answers share nothing but their
  purpose: 4.3.3.1.2 is a hierarchy of *codes* for gases, while 4.3.4.1.2 is
  the rationalized approach, where each code names the *group of substances* it
  may carry — by class, classification code and packing group — and inherits
  the groups of the codes below it. They are read and stored apart, because
  reading them as one thing is the mistake that would make the answer wrong.
- The reader takes the English volume II, the printed Dutch edition and the
  German volume II, and compares two readings cell by cell. Nothing is
  committed from a run: a cell two editions disagree on is kept with both
  values and settles nothing, the rule every regulatory table in this
  repository follows.

### Changed

- **The regulation reader can quote the books in the store.** Chapter 4.3 is
  not in the assembled Dutch edition the container holds — it prints part 4 as
  far as 4.1 and no further — so the provision had to come from the printed
  edition, which the reader could not name: it knew only the five volumes it
  can download itself. The store register is now merged into its source list, a
  document supplied by the operator is never fetched (it is in the store, or
  the run says so and names the file it expected), and the workflow takes
  several documents at once, passes every input as an argument instead of
  splicing it into the script, and can be asked to quote no group at all.

## [1.80.0] — 2026-08-14

### Changed

- **Table C is read from three books.** The Dutch reading no longer comes from
  an HTML export but from the printed Dutch ADN, and the difference is the
  whole point of reading a table twice:

  | | export as second reading | printed book as second reading |
  |---|---|---|
  | rows settled on every cell | 673 | **677** |
  | rows with a disputed cell | 5 | **1** |
  | rows of an edition left unplaced | 5 | **0** |
  | rows resting on one reading | 0 | 0 |

  The one cell left is UN 2789's density, where all three editions print 1,05
  and then qualify it in their own language. The application withholds it, as
  it withholds any cell no two readings agree on.

- The export's four measured defects are simply absent now: no row split per
  alternative name (UN 1268 keeps its "of" inside the name, in 26 rows), no
  swapped columns (7) and (9), no missing UN 1977 and UN 1999 — both now carry
  three readings and a name in every language — and no remark column glued four
  languages deep. `adn_nl_index` stays in the register as the source the first
  reading came from; it decides no cell any more.

- The French reading settled 27 stand-offs and, for the first time, sided with
  the Dutch against the English: UN 2672's density. That is what a third
  reading is for.

## [1.79.3] — 2026-08-14

### Changed

- **The reading of table C from the printed Dutch ADN stands up.** 653 rows off
  35 pages, 25 cells it still will not guess at, and — the number that matters
  — **628 of the 678 rows of the English edition match a Dutch row on every
  compared cell**, with 39 differing and 11 having no Dutch row at all. The
  export it would replace needed four documented repairs before it could be
  compared at all and still left 153 cells disputed.

  What it took, each measured on a run and none of it guessed: the boundary
  between two columns is the empty corridor the typesetter left, not the
  midpoint between two column numbers — a number is centred over its column and
  the cells under it are not, so the equipment codes of column (18) began a
  point left of the midpoint and "PP," landed in the explosion protection.
  Where a page's widest row bridges that corridor there is none to measure, and
  then what the column *holds* decides: (1) a UN number, (4) a packing group,
  (3a) a class. And the danger cell is the one code written in words, so the
  Dutch "F of S" is the English "F or S" — that alone accounted for 95 of the
  first 118 differences.

- The reading is **not yet adopted**: swapping it in means re-emitting the seed
  the application answers from and re-pinning the bookkeeping its tests hold to,
  and that is a step to take with a full test pass in front of it rather than at
  the end of a long session. The three readings in `adn_table_c.json` are
  untouched.

## [1.79.2] — 2026-08-14

### Fixed

- **Three of the four things the Dutch table C reader reported are gone.**
  Column (1) holds a UN number and nothing else — the boundary taken from the
  column numbers falls inside the name, because a number is centred over its
  column and the name column is far wider. A footnote reference is set above
  its line, so a cell sorted on y alone read "12) T1" for "T1 12)"; words
  within a few points of each other are one line whatever their height in it.
  And the row boundary is now read from the rules the typesetter drew: this
  edition sets the UN number level with the middle of its row, so a band from
  one number to the next took the top of the following row with it and ACETON
  came back carrying the next substance's equipment codes.

- What is left is one class of report: text that runs a little past a column
  boundary ("R 115) 2" for the class, "ja PP," for the explosion protection).
  The boundary is still the midpoint between two column numbers where it should
  be the empty corridor between two columns, measured on the content. The
  reading remains **not adopted** until it is.

## [1.79.1] — 2026-08-14

### Changed

- **A reader for table C as the printed Dutch ADN sets it**, across the page
  rather than down it: a page's columns from the band of column numbers over
  it, a row from one UN number to the next, a cell the crossing of the two.
  Its first run found the 35 table C pages and read 33 rows past every shape
  check, and reported 645 cells it would not guess at. The reading is **not
  adopted**; what the reports say, in their own words, is that the boundary
  between columns (1) and (2) sits wrong for a column that wide
  ("1010 BUTADIENEN BUTADIENEN" came back as a UN number), that a footnote
  reference set above its line sorts before the cell it belongs to
  ("12) T1" for "T1 12)"), and that a name running over two lines still splits
  its row. Each is a measurement to act on rather than a mystery.

## [1.79.0] — 2026-08-14

### Added

- **German proper shipping names from the 2025 edition.** The last field still
  coming from a 2023 export. It stood because UNECE publishes the ADR in
  English and French only — the operator's national edition of the Bundesamt
  für Strassen closed it. 2,346 UN numbers at 0.9996 agreement against the UN
  numbers of the Dutch table A, and **2,210 of the names read exactly as the
  export had them**; the rest is what two years of ADR did to them, plus a
  handful the export had truncated (UN 0219 ended mid-word at
  "Alkohol/Wasser-"). A German road document now carries the name the current
  edition prints, and the manifest's erratum about it is closed.

### Fixed

- **A row cut is tried, not believed.** The German edition's line gaps offered
  a step at 31.2 points that is no boundary at all: it merged about twenty
  printed rows into one, so UN 0004 came back with the twenty-one entries after
  it inside its own name and 145 table pages gave 531 rows instead of 2,938. A
  page's rows and its UN numbers are the same thing counted twice, so a
  candidate cut is now measured against that count before it is used.

- **A word break is not a hyphen.** The German edition breaks words across the
  column constantly — CHLORWASSERSTOFF-SÄURE, DIETHYLENGLYCOLDINI-TRAT — and a
  name a driver hands over may not carry the typesetter's hyphen. Position was
  tried first and does not hold (a break is not always set hard against the
  margin); what does is where the hyphen sits in the word: the hyphens a name
  owns follow a locant or a lower-case prefix (2,2'-, alpha-, n-), a break
  falls inside a run of capitals. The second reading settled it — the 2023
  export spells all of them without the hyphen.

- **A sentence is not a row.** "1000 ml/m3 und einer gesättigten
  Dampfkonzentration" came back as a UN 1000 the ADR does not have. A name
  opens with a capital, a bracket, or a locant or prefix before a hyphen —
  1H-TETRAZOL, 2,2'-DICHLORDIETHYLETHER, alpha-NAPHTHYLAMIN — never with a unit
  of volume.

## [1.78.1] — 2026-08-14

### Changed

- The two readers can now be pointed at the editions the operator supplied: the
  proper-shipping-name reader at the German ADR (the only source there has ever
  been for the German names of column (2)) and the table C reader at the printed
  Dutch ADN (the book behind the export whose damage this repository has been
  undoing since v1.73.0). Both are operator-supplied, so they are read from the
  store rather than through the download ladder.

- Neither reading is adopted yet, and the first measurements say why. The German
  edition is a different typesetting: its table pages are recognised — rows come
  through as `2037 GEFÄSSE, KLEIN, MIT GAS` — but the reading reaches 0.2235
  against the UN numbers of the Dutch table A, which is a band-recognition
  problem and not a row one. The Dutch ADN prints table C as an ordinary
  landscape table, one substance per line with the columns spread across x,
  where the UNECE volumes print it rotated; that needs a reader of its own, and
  a simpler one than the rotated pages needed.

## [1.78.0] — 2026-08-14

### Added

- **All eight models of the instructions in writing now come out of the
  store.** The operator supplied the ADN in Dutch and in German — the two
  editions UNECE does not publish, and the last two combinations the
  application had to report as missing. The German model sits on pages 818-821
  and was verified page by page against its own title; the Dutch edition begins
  the model partway down the sheet that carries 5.4.3's own paragraphs, so the
  range is the wider one deliberately, as it is for the Dutch ADR.

- The Dutch ADN also enters the register as a **printed edition of the book
  whose HTML export this repository has been undoing cell by cell** since
  v1.73.0 — the export that splits rows per alternative name, swaps columns (7)
  and (9) against its own header and omits UN 1977 and UN 1999. Nothing is read
  from it yet; it is registered and pinned, and a reading of table C from the
  book itself is now possible where before there was only the export.

## [1.77.0] — 2026-08-14

### Added

- **The German model of the instructions in writing, and a printed Dutch
  edition to cut the Dutch one from.** UNECE publishes the ADR in English and
  French only, so the German model of 5.4.3 was the one the application had to
  report as missing. The operator's own volumes closed it: the German ADR of
  the Bundesamt für Strassen sets the model on four pages (345-348 of volume
  II), and a printed Dutch ADR 2025 replaces the assembly the Dutch model was
  cut from — that file reflows the model over ten pages and runs 5.4.4 onto the
  last of them. **Six of the eight models now come out of the store**; what is
  left is the ADN in Dutch and in German, which no edition here prints.

- Five documents joined the register with them: the German ADR in two volumes,
  the Dutch ADR 2025, and the RID in German and French. Twenty source documents
  now, each with its hash.

### Fixed

- **A model was cut one page off.** The new verification run — cut every
  registered model and print what came out — earned its keep immediately: the
  English ADN model arrived with 5.4.3.5 on the driver's first sheet and the
  equipment list missing from the last. Not the range: pypdf counts one page
  more from the front of the ADN volumes than PyMuPDF does, and the ranges were
  measured with one library and cut with the other. Measuring and cutting now
  use the same one, and all six cuts are verified page by page against the
  model's own title.

- A kept cut is named after the edition and the page range it came from, so a
  register that comes to point at another edition asks for a file that does not
  exist yet instead of being handed yesterday's pages under today's name.

## [1.76.1] — 2026-08-14

### Changed

- The instructions in writing are now reached the way a driver reaches them:
  four checks through the API itself, so the list, the honest refusal for a
  model no edition here prints, and the PDF that comes back are held to their
  behaviour and not only to the service that produces them.

## [1.76.0] — 2026-08-14

### Added

- **The documents have their own language now.** ADR 5.4.1.4.1 — and RID and
  ADN in the same words — asks for an official language of the *forwarding
  country*, and where that is not German, English or French, additionally one
  of those three. That is a fact about the consignment, not about who is
  typing, so the export step asks for it instead of following the screen. It
  defaults to the language of the screen, states the article underneath, and
  carries into the transport document, the description line of 5.4.1.1.1 and
  the UN cards.

- A proper shipping name the application derived is re-derived in that
  language: a consignment entered in Dutch and exported in French leaves with
  ESSENCE, and the export reports the replacement as it already did for a sea
  leg. Wording of the user's own is never touched, and a sea or air profile
  still wins over the choice — 5.4.1.4.1 at sea and 8.1.2.1 in the air leave no
  room for a preference.

## [1.75.0] — 2026-08-14

### Added

- **The instructions in writing (5.4.3), from the document store.** ADR and ADN
  5.4.3.4 do not describe the instructions, they print them: the document a
  crew carries has to correspond "in form and content" to a four-page model the
  book sets out. So this is the one regulatory document EMCargo does not
  compose. The export step now offers the model per regime and per language,
  cut out of the edition in the document store — page ranges measured per
  edition with the new `scripts/find_instructions_pages.py` and written into
  the register, never guessed. Four are measured and registered: the ADR model
  in Dutch (from the official Dutch edition), in English and in French (from
  UNECE volume II), and the ADN model in English and in French. A combination
  no edition in the store prints is reported as missing and names the document
  that would produce it; it is never filled in from a neighbouring language,
  because instructions in a language the crew cannot read are exactly what
  5.4.3.2 exists to prevent. There is no free official German ADR or ADN, so
  German waits for an operator to supply it.

- **French proper shipping names.** The ADR is authentic in English *and* in
  French and table A prints both columns; until now a French reader was handed
  the English name. Reading the French volume now clears its agreement gate at
  0.9983 against the UN numbers of the Dutch table A, so UN 1203 reads ESSENCE
  where it read GASOLINE. 5.4.1.4.1 lets French stand on its own, so it does —
  unless a sea or air profile is in play, which takes the name back to English
  as it always did.

### Changed

- **Table C of the ADN is read three times, and five rows still disagree where
  153 did.** The French edition — the treaty's other authentic language — reads
  with the same geometry as the English one: 677 of 678 rows. Paired against
  the English row set it decides a cell wherever two of the three readings
  agree. What that settles: **673 of 678 rows now settle on every cell** (it
  was 491), **five carry a disputed cell** (it was 153), and **no row rests on
  a single reading any more** (it was 34) — the rows the Dutch export omits,
  UN 1977 and UN 1999 among them, are corroborated by the French edition. The
  French reading decided 180 cells and sided with the English edition in every
  one of them, which is the Dutch export's measured damage showing up a third
  time. The two cells it alone reads differently are recorded on their rows and
  do not re-open a cell the first two agreed on.

- The comparison learned one thing about language first: the danger cell is the
  only code in table C written in words, so "unst." and "F or S" are "inst."
  and "F ou S" in French — and the reading order of a rotated cell breaks the
  word itself, which is why the mapping happens after the spaces are gone.

### Fixed

- **The name reader lost the first row of nearly every table page.** Traced on
  page 300 of the French ADR: the column-number line ends at y 114.6 and UN
  0004's number begins at y 114.6. The body's top is now the middle of the
  marker line, which no line of print can straddle, instead of a constant
  borrowed from another document. It took the French reading from 0.9633 to
  0.9983 and the English from 0.9475 to 0.9821.

### Known

- The English 2025 reading of the names is **not** adopted at 0.9821: it still
  loses rows and turns a page number into a UN 1000. The English names stay
  where they were, in the 2023 export, because an edition-old official name
  beats a fresh damaged one.

## [1.74.0] — 2026-08-14

### Added

- **The store takes in what the operator brings.** The publishers' servers are
  not the only source of the books: the operator has their own downloads. The
  store tool gains `adopt` — a file whose sha256 matches a pinned hash is
  recognised and stored under its canonical name whatever it arrived as, a
  mapped file is stored and pinned, and the rest is reported with name, size
  and hash so the next mapping is written from the report. The fetch workflow
  drains a public Google Drive folder into the store with `gdown`, and can
  probe any URL from the runner, whose network is open where the development
  container's is not.

- **The register grows to fifteen documents, and the French ADR mystery is
  solved.** The operator's folder held the UNECE originals: three volumes
  verified byte-identical against their pinned hashes, and the French ADR
  Volume I — whose file is numbered `2412006_F`, not the `2412007_F` the
  published links carried, which explains every 404 it ever answered. The
  corrected URL is recorded. Newly registered and pinned: the French ADR
  Volume II, the French ADN — a third edition of that treaty, available for
  settling cells the English and Dutch readings dispute — and three
  ADN Administrative Committee session documents, honestly marked unread.

### Known

- The French proper-shipping-name extraction now reads the true French Volume
  I and reaches 0.9633 agreement — up from 0.9475, still under the 0.98 gate,
  and nothing is written below the gate. The diagnostic points at the first
  row of nearly every table page going missing in this edition's layout; that
  is an extractor iteration of its own.

## [1.73.0] — 2026-08-14

### Added

- **Table C of the ADN — the tank vessel table — is in the repository, read
  twice.** The English UNECE 2025 PDF supplied the row set and every cell: its
  pages print the table rotated, substances as page columns and the twenty
  column numbers as bands down the left edge, and the extractor measured that
  layout with probe runs rather than assuming it. The Dutch mindef export
  supplied the corroboration and the Dutch names. 678 printed rows.

  The comparison is a record the seed carries, not a gate it passed: 491 rows
  agree on every cell; 153 carry a `disputed` cell with both readings' values,
  and a disputed cell is never presented as an answer; 34 rows exist only in
  the English edition — the Dutch export omits UN 1977 and UN 1999 entirely,
  along with single variant rows of several N.O.S. entries — and each says
  `readings: 1`. The export's other damage is measured and documented in
  place: it splits a printed row per alternative name (52 rows for the 26
  printed rows of UN 1268), swaps the data cells of columns (7) and (9)
  against its own header, sets nine row names with a lower-case prefix the
  list grammar had to learn, and glues its remark column four languages deep.

  What the application answers from it, for a cargo tank consignment:

  - **The tank vessel type of column (6).** Anhydrous ammonia sails a type G
    vessel and the admission card says so; petrol's six variant rows split
    between types N and C, and the card presents the variants instead of
    picking one.
  - **The signals of column (19), under 7.2.5.0.1** — the provision the page
    itself points at — with 7.2.5.0.2 ranking two blue cones before one where
    several apply. Petrol settles at one cone across all six variants; a
    substance whose variants disagree, or whose cell the two readings dispute,
    is named as not settled rather than averaged.

  Both reach the document warnings. What is still not checked is the vessel
  itself: cargo tank design, type and equipment, opening pressure and filling
  degree are shown as conditions to verify against the vessel that sails.

## [1.72.1] — 2026-08-14

### Changed

- **Five hashes pinned, measured on a runner.** The first run of the fetch
  workflow filled the store from an empty cache: ADR volumes I and II and the
  ADN via the web archive (the publisher answers 403 to runners), RID and the
  IMDG 42-24 amendment directly. Their sha256 values are now pinned in the
  register — including, for the first time, the **English ADN**, whose absence
  was what kept table C waiting on its second reading.

  The one that got away is recorded too: ADR Volume I in French answers 403 at
  the publisher and 404 in the archive at both known addresses. The register
  says so instead of leaving the next person to rediscover it.

## [1.72.0] — 2026-08-14

### Added

- **The regulatory database has a durable foundation.** Every dangerous-goods
  fact in this repository was read out of a book, and the books were the fragile
  half: UNECE refuses non-browser requests, the web archive rate-limits by mood,
  and the Dutch editions lived as uploads in a container that forgets. Session
  after session, the work started with getting at the sources again.

  Three pieces close that:

  - **A document store outside the repository** — `/data/regulations`, a volume
    that outlives the container (override with `EMCARGO_REGULATIONS_DIR`; the
    CI cache path is read as a twin). The books stay out of git, as
    `docs/data-sources.md` has always promised.
  - **A register in the repository** — `backend/seed/dg/sources.json`, one entry
    per document with publisher, edition, URLs and the sha256 of the exact file
    the facts were read from. Ten documents: the five free land-mode texts, the
    four operator-supplied Dutch sources behind the first readings, and the IMDG
    42-24 amendment. The four Dutch files are stored and their hashes pinned;
    they cannot be re-downloaded, so the pin is the proof of provenance.
  - **One tool connecting the two** — `scripts/regulations_store.py` with
    `status`, `fetch`, `add` and `verify`. A pinned hash is never silently
    rewritten: a file that contradicts it is refused, because a new printing and
    a damaged download need different answers. A new *Fetch regulations into the
    store* workflow does the downloading where the network allows it and prints
    the hash to pin.

  `read_land_regulations.py` now reads from the store first, and the procedure
  for a new edition — register, fetch, re-extract with two readings, diff the
  seeds, update the validity dates — is written down in
  `docs/regulatory-database.md` instead of living in one session's memory.

## [1.71.1] — 2026-08-14

### Fixed

- **The field emptied itself under the cursor.** `dg/prepare` fills in what
  follows from the UN number. It is debounced by 250 ms, then takes a round trip,
  and it only runs again when the UN number, the counts or the packaging change.
  That leaves a window: anything else typed while a request is out — a total by
  hand, a technical name — is typed into a form the reply knows nothing about, and
  the reply was taken as the new truth. The value went back to what it had been
  when the request left, a beat after the typing.

  The reply is no longer taken whole. The difference between what the request was
  built from and what came back is exactly what the backend contributed; only that
  is applied, and only where the form still holds nothing of its own — the rule
  the derivation already followed, now applied against the form as it stands
  rather than as it stood. If a position or a product was added or removed while
  the request was out the reply is dropped, because the indices no longer line up
  and a fresh derivation is on its way regardless.

  Reported in PR #148 and left unfixed through three releases.

## [1.71.0] — 2026-08-14

### Fixed

- **Chapter 7.1 of the ADN is for dry cargo vessels, and every inland check in
  this application implements it.** A consignment declared as a cargo tank was
  measured against that chapter anyway: the separation in the holds (7.1.4.3),
  the blue cones off table A (7.1.5.0) and the exemption of 1.1.3.6.1 all came
  back with answers, and none of them applied. That is the same shape of wrong
  the road side had before v1.66.0 — not a gap, which looks like a gap, but an
  answer.

  **Column (8)** is where the ADN says which way is open, and it is a short
  list: empty means carriage in packages only, `B` adds bulk and points at
  7.1.1.11, `T` adds tank vessels and points at 7.2.1.21, where table C takes
  over. The value has been in the substance database since v1.61.0 and nothing
  read it. A new check does, and it refuses gas oil in bulk (no `B`) and
  ammonium picrate in a cargo tank (no `T`) while admitting ammonium nitrate in
  bulk and petrol in a tank vessel.

  Two provisions fix what the modes mean here, and they point opposite ways.
  **7.1.1.21** forbids carriage in cargo tanks on a dry cargo vessel, so a cargo
  tank load is a tank vessel and chapter 7.1 has nothing to say about it; the
  three checks above now name chapter 7.2 instead of answering. **7.1.1.18** puts
  tank containers and portable tanks under the requirements for carriage of
  packages, so they sail on a dry cargo vessel and keep every answer — which is
  the more expensive half to get wrong, and most of the new tests are about it.

- **1.1.3.6.1 is granted for carriage in packages.** The note printed under that
  result has said "carriage in tanks is never exempt" since v1.32.0 while the
  arithmetic granted the exemption anyway. A sentence to the reader is not a
  rule.

- **A tank prohibition reached the panel and not the paper.** v1.66.0 works out
  whether goods may travel in a tank at all and showed the answer on screen only.
  Both the road and the water admission findings now go into the document
  warnings, where the person filling in the document meets them.

### Added

- Where column (8) permits a tank vessel, the answer says plainly that **table C**
  is not in this repository — the vessel type, the cargo tank type and the
  conditions that go with them are in it and have not been read. Silence there
  would be read as "nothing further applies".

## [1.70.3] — 2026-08-14

### Fixed

- **The API is not a way round it either, so the workflow says what is missing.**
  v1.70.2 fell back to the tag object API when the push of a tag on an older
  commit was refused. Measured: `git/tags` accepts the tag object, and `git/refs`
  then answers `403 Resource not accessible by integration`. The same restriction
  is enforced there, so that fallback was a path that could never work — and a
  fallback that cannot work is worse than none, because the failure it leaves
  behind names the wrong thing.

  It is gone. The only credential that can make such a tag is one carrying
  workflow scope of its own, which has to be a secret; if `RELEASE_TOKEN` is set
  the push uses it, and if it is not, the step ends with a message naming what is
  missing instead of a line about App permissions. Tagging the head of main needs
  none of this and is untouched.

## [1.70.2] — 2026-08-14

### Fixed

- **The tag for an older commit could be resolved, and then not pushed.** v1.70.1
  let the release workflow name the commit to tag, and it got as far as the push:

      ! [remote rejected] v1.67.0 -> v1.67.0 (refusing to allow a GitHub App to
        create or update workflow `.github/workflows/tag-release.yml` without
        `workflows` permission)

  `GITHUB_TOKEN` belongs to a GitHub App, and a ref carrying a different
  `.github/workflows/` tree than the default branch counts to the remote as
  creating a workflow. Tagging the head of main never trips this — the trees are
  the same — which is why every release so far went through. A tag on an older
  commit does trip it, and the permission it asks for cannot be granted: the
  `permissions:` block of a workflow has no `workflows` key.

  The tag object API does not go through that check. The push stays the primary
  path, because that is the one every release has proven; when it is refused, the
  workflow now creates the annotated tag through `git/tags` and `git/refs`
  instead. The existence check also moved from the local repository to
  `git ls-remote`, since a checkout by commit does not fetch the tags.

## [1.70.1] — 2026-08-14

### Fixed

- **A tag that was missed can now still be made.** The release workflow always
  checked out the head of main and demanded that the version given match the
  `VERSION` file there. That is right when a release is tagged straight after the
  merge, and wrong the moment the dispatch is forgotten: main moves on, `VERSION`
  moves with it, and the tag for the commit that was actually released can never
  be created — while that commit is still sitting in the history, unchanged. It
  happened here to v1.67.0 and v1.68.0.

  The workflow now takes an optional `commit`. Everything downstream already read
  from the checked-out tree, so naming a commit makes `VERSION`, the changelog
  section and the image SHA all come from that commit rather than from today's
  main; the version check then compares against the right file. Left empty, the
  workflow behaves exactly as before. The one thing added is a guard that the
  commit is an ancestor of main — a tag on a stray branch would claim a release
  that never happened.

- The workflow's own log lines and the fallback release note were still Dutch.
  They are English now, like the rest of the repository.

## [1.70.0] — 2026-08-13

### Fixed

- **A tank needs placards, and this check used to say it needed none.** For
  carriage in packages 5.3.1.5 puts a placard on the vehicle only for class 1 and
  class 7. That reading is right, and it is the finding v1.57.0 was built around:
  a full load of packaged petrol needs no placard at all, and telling a driver to
  placard anyway teaches that the placard is decoration.

  A tank does not work that way. **5.3.1.4.1** requires a placard of *every label
  model of the load* on both long sides and on the rear of the vehicle;
  **5.3.1.2** requires the same on both long sides and at each end of a tank
  container or portable tank. Where a tank has several compartments carrying
  different goods, the placards go on the relevant compartments plus one of each
  model on each side at the rear.

  So the answer inverts with the mode: the same petrol that needs no placard in
  packages needs a class 3 placard on three faces in a tank. Answering the second
  with the first turns a requirement into an absence, which is the worst
  direction for a placard to be wrong in.

  Bulk is placarded like a tank here — 5.3.1.4 is headed carriage in bulk and in
  tanks alike, and this is the one rule in the tank work where the two share an
  answer. Where table A gives no label in column (5) the check says the provision
  turns on one, rather than reporting placards it cannot name.

  Read from ADR 2025, Dutch edition, 5.3.1.2 and 5.3.1.4.1, printed pages
  975-976.

## [1.69.0] — 2026-08-13

### Fixed

- **The 1.1.3.6 exemption is for carriage in packages, and a tank load can no
  longer claim it.** The operative sentence of 1.1.3.6.2 grants the exemption
  for goods carried *in packages* in one transport unit. A tank or a bulk load is
  not carriage in packages, so the exemption is not available to it however small
  the quantity — and the points arithmetic, which exists only to test that
  exemption, is answering a question that does not arise.

  The panel now says so in place of a total: neither green nor red, because the
  exemption is not failed, it is not on offer. One litre in a tank does not buy
  it back; the provision turns on the form of carriage and not on the amount.

  **This reaches the tunnel too.** 8.6.3.3 takes goods carried under 1.1.3 out of
  the tunnel determination altogether, and until now a tank load could be dropped
  out of it on the strength of a points total it was never entitled to. Its code
  now stands — and with v1.67.0 that code is read from the stricter column.

  Withholding an exemption is the safe direction to be wrong in; granting one is
  not. Read from ADR 2025, Dutch edition, 1.1.3.6.2, printed page 77.

## [1.68.0] — 2026-08-13

### Fixed

- **A road tanker of petrol is high consequence dangerous goods, and this check
  used to say it was not.** Table 1.10.3.1.2 has three quantity columns — tank,
  bulk and packages — and only the packages one was ever answered.

  For packages the answer is mostly footnote b): whatever the quantity, 1.10.3
  does not apply. That reading is right and it is why v1.58.0 could answer
  packages with a membership test and no arithmetic at all. **Seven rows are
  footnote b) in packages and 3,000 litres in a tank**, so they had no reason to
  exist in this configuration until the application knew about tanks: flammable
  non-toxic gases, flammable liquids of packing groups I and II, packing group I
  substances of classes 4.2, 4.3, 5.1 and 8, and the perchlorate and ammonium
  nitrate entries.

  Above 3,000 litres in a tank, those now qualify — and with them comes the
  security plan of 1.10.3.2 and the identity documents of 1.10.1. Not every tank
  row is a threshold: a toxic gas carries 0, meaning any quantity at all.

  **Footnotes c) and d) are applied with the figures.** A tank or bulk value
  counts only where table A admits that form of carriage, which the columns
  carried since v1.65.0 settle — so an explosive, which has no tank code, is not
  dragged into the tank column by a mode somebody set in error.

  A threshold needs a quantity. Where none is entered the row is reported as
  **unanswered** rather than read as under the figure: the difference between not
  knowing and knowing it is safe.

  Read from ADR 2025, Dutch edition, table 1.10.3.1.2 and its four footnotes,
  printed pages 184-185.

## [1.67.0] — 2026-08-13

### Fixed

- **The tunnel code applies the stricter side for tanks and bulk.** Five of the
  twelve codes of 8.6.4 carry two answers: B/D, B/E, C/D, C/E and D/E bar more
  tunnel categories for carriage in tanks and in bulk than for packages. **Both
  lists have been in this repository's configuration since v1.50.0** and only the
  packages one was ever read, because nothing knew how the goods travelled. The
  note under the tunnel card said as much — and a note is not a check.

  A tank of petrol under code D/E is now barred from categories D **and** E,
  where the same petrol in packages is barred from E alone. One tank position
  decides for the whole load, because 8.6.3.2 assigns one code to the load and
  not one per substance.

- **The orange plates tell a tank load what it must do, not what it may.** For
  packages 5.3.2.1.6 *permits* the hazard identification number above the UN
  number on the front and rear plates, and only where a single substance is on
  board. For a tank vehicle 5.3.2.1.2 *requires* an orange plate on both sides of
  every tank and every compartment, bearing the numbers of the substance that
  compartment holds. Permitted and required are not the same finding, and a tank
  load was being shown the permitted one.

  Where column (20) gives no hazard identification number the check says that
  5.3.2.1.2 turns on one, rather than printing a plate with a gap in it.

  Read from ADR 2025, Dutch edition, 5.3.2.1.2 and 5.3.2.1.6.

## [1.66.0] — 2026-08-13

### Added

- **The application knows how the goods travel.** Every check in the compliance
  layer was written for **packages**, and said so nowhere. A consignor filling in
  a tank load got the packages answer with nothing to mark it as the wrong one —
  the most expensive shape of wrong this application can produce, because it does
  not look like a gap, it looks like an answer.

  A per-substance **mode of carriage** now says which it is: in packages, in an
  ADR tank, in a portable tank, or in bulk. It is a list and not a text box —
  free text there would fall through every check that branches on it and the
  consignment would quietly be judged as packages again. An unknown value is
  refused at the API edge for the same reason. Absent means packages, which is
  what every consignment drawn up before this release was.

- **ADR 3.2.1: may these goods travel in a tank at all?** The first check to use
  the mode, and it only speaks once somebody has said the goods travel in one.
  UN 1203 petrol is admitted with tank code LGBF on an FL vehicle; UN 0004
  ammonium picrate is refused, because it has no tank code.

  **The two tank columns do not say the same thing, and the check keeps them
  apart.** Column (12) is absolute: where no code is given, carriage in ADR tanks
  is not permitted, and the provision carries no exception. Column (10) is not:
  where no portable tank instruction is given, carriage is not permitted *unless
  the competent authority allows it* under 6.7.1.3. Rounding those two to one
  answer would either invent a prohibition or hide one, so an item can be "not
  permitted" and still say that approval is open — and only column (12) blocks.

  v1.65.0 carried the tank columns and refused to read an empty column (12) as a
  prohibition until the text had been read. It has now been read: ADR 2025, Dutch
  edition, 3.2.1, printed pages 546-547.

## [1.65.0] — 2026-08-13

### Added

- **The ADR tank columns are in the substance database.** Columns (10) to (14) of
  table A — the portable tank instruction and its provisions, the ADR tank code,
  its provisions, and the vehicle the substance then requires (FL, AT, EX/III) —
  now reach the seed and the substance lookup. UN 1203 petrol reads LGBF and FL;
  UN 1017 chlorine reads P22DH(M) and AT; UN 0004 ammonium picrate leaves every
  tank column empty.

  Nothing new had to be read to get them. The extractor has read and
  cross-checked these five columns since v1.56.0 and dropped them on the way to
  the seed, with the reason written down: nothing in the application computed
  with them, and a field nobody reads is a field nobody notices going stale.
  Tank carriage changes that, so the reason expired.

  Both readings agree: the portable tank instruction, its provisions, the tank
  code and the tank provisions match on all 2,345 shared UN numbers between
  table A and the alphabetical index. Column (14) reaches 0.9966 — the eight
  disagreements are the same eight rows where the *index* also loses the
  transport category, because the digit lands one column over in that reading.
  Table A is the reading the application computes with, and a test pins the
  column to the three vehicle types so a boundary that moves is caught.

### Not yet

- **No check acts on the tank columns.** In particular nothing reads an empty
  column (12) as "not accepted in an ADR tank", however plainly the pattern
  suggests it — UN 0004 and every other class 1 entry leaves it blank. That is a
  statement about what the regulation permits, not an observation about a table,
  and it gets read out of the text before anything acts on it. This release
  carries the data; the checks come with the carriage mode.

## [1.64.0] — 2026-08-13

### Added

- **ADN 7.1.4.3.4, the class 1 compatibility table, is applied.** Twelve
  compatibility groups, four numbered conditions, and until now the one part of
  7.1.4.3 that was named as untranscribed. Two explosives may share a hold only
  where the table says so; where it says so *on a condition* the condition is
  named, because neither "permitted" nor "forbidden" would be the truth. The
  answer does not depend on the order the two were entered — the table mirrors,
  and a test holds it to that.

  **Getting it is why this repository insists on two readings.** The Dutch HTML
  edition is *damaged* at this table: row N carries thirteen cells where twelve
  belong, and the D/B cell lost its footnote marker so the table read "1)" one
  way and "(*)" the other. A compatibility table must mirror across its
  diagonal — that is a property of the thing itself, not of a typesetting — and
  checking it caught both defects. The English UNECE edition mirrors in all 144
  cells and is what the application computes with; the Dutch confirms ten of the
  twelve rows cell for cell. The symmetry check is kept as a test.

### Fixed

- **ADN 7.1.5.0.2: the thresholds are read rather than guessed.** The Dutch
  edition lost the comparison sign, so both rows of each pair read "> 130,000 kg"
  and "> 30,000 kg" — the same rule twice, which decides nothing. v1.61.0
  therefore left the reduction out and said so. The English edition has the
  signs: above 130,000 kg keeps one cone and at or below shows none; above
  30,000 kg keeps two and at or below none; other classes and packing groups II
  and III show none at any mass; three cones stay three.

  The figures were what one would have guessed, and that is exactly why guessing
  would not have done. They are recorded with their provision so nobody reads
  them a second time.

  The reduction is still **not applied**: doing so needs the consignor to state
  that the load travels exclusively in containers, and there is nowhere to say
  that yet. Inferring it from a packaging type would be guessing at the very
  fact the provision turns on. Its absence can only overstate the signals, and
  the panel now names both thresholds instead of gesturing at them.

- **The reading workflow uses the volumes that are already fetched.** The
  extraction workflow has kept them between runs since v1.61.0; this one did
  not, so quoting three lines of the ADN re-fetched 19 MB from the Internet
  Archive — which had already cost three runs to 503 and 498 answers. It now
  restores the same cache.

## [1.63.0] — 2026-08-13

### Added

- **The inland waterway outcomes reach the screen and the document.** v1.59.0 gave
  the ADN its own separation rule and v1.61.0 the blue cones out of its own table
  A. Both computed correctly for every consignment and appeared **nowhere**: the
  compliance panel showed only the 1.1.3.6.1 exemption, and no ADN warning had
  ever been written to a document. Two provisions were answered into the void.

  The panel now carries two more cards. **Separation in the holds (7.1.4.3)**
  lists each finding with the distance it prescribes — 3.00 m between classes,
  12 m around class 1 and the three-cone goods of 4.1 and 5.2 — and the
  shared-hold prohibition of 7.1.4.3.2 with the two substances it stands
  between. **Signals (7.1.5.0)** shows the number of blue cones or blue lights,
  which substance sets it under 7.1.5.0.4, and the container reduction of
  7.1.5.0.2 that EMCargo deliberately does not apply.

  A cone count of **nought is displayed as prominently as two**. It is the
  commonest answer and means the vessel shows no signal; a card that appeared
  only when cones were needed would teach a consignor that an absent card means
  safe.

  The same outcomes now travel with the papers: the signals, the tie-break and
  every separation finding are warnings on the ADN transport document, through
  the channel opened in v1.62.0.

### Changed

- **Inland waterway is off the lock.** It went on in v1.60.0 because it answered
  its separation question with the *road* table and held no cone data at all.
  The exemption of 1.1.3.6.1, the separation of 7.1.4.3 and the signals of
  7.1.5.0 now all come out of the ADN itself, and all three are visible.

  What is still missing is the tank vessel regime — and a tank vessel
  consignment cannot be entered here in the first place, because this wizard
  models packages. So what a user can draw up is exactly the part that is
  covered, which is the condition the lock existed to enforce. Rail, sea, air
  and multimodal stay locked, with their gaps listed in `docs/dg-coverage.md`.

## [1.62.0] — 2026-08-13

### Fixed

- **The document warnings reach the person about to download.** `validate_document`
  has always returned two lists: blocking errors and warnings. The errors worked.
  The warnings were computed and went nowhere, along two routes at once — the
  export route discarded them (`errors, _warnings = ...`; a file response has no
  body to carry them), and the endpoint that does return them,
  `POST /documents/validate`, had **no caller anywhere in the frontend**.
  `api.validateDocument` sat in `client.ts` unused.

  Fourteen warning sites fed that dead channel: the missing-unit notice of
  v1.61.1 (ADR 5.4.1.1.1 (f)), the missing English proper shipping name, the
  name-language substitution, the lost 1.1.3.6 exemption and its "incomplete"
  counterpart, the mixed-loading findings, the LQ/EQ notes, the IATA Q-check
  notes, the 8.6.3 tunnel message for the whole load, and the VGM mass check —
  that last one has nothing to do with dangerous goods, which is why the fix is
  not gated on a consignment carrying any.

  The warnings now stand on each document's card on the export step, **before**
  the download button — a warning shown after the file is on disk is a warning
  shown too late. They never disable the button: that distinction from errors is
  the point of having two lists. One payload builder now serves validation and
  export both, so what is validated is what is exported by construction. The
  texts arrive from the backend already in the document's language; the frontend
  translates nothing.

### Known limitation, found while proving the fix in the browser

- **A total quantity typed at the wrong moment is silently reverted.** The
  dangerous-goods step re-derives its data 250 ms after every change to the
  fields its signature watches — and `adr_total_quantity` is not one of them, by
  design, because it is a computed value. A user who types a total while such a
  derivation round-trip is in flight gets it overwritten by the response's
  snapshot, which was taken before they typed. Reproduced live: the first "100"
  vanished, the retry stuck. This predates this release and sits in a delicate
  two-way sync; it is reported here rather than patched in passing, and wants a
  change of its own.

## [1.61.1] — 2026-08-13

### Fixed

- **The unit on the transport document followed an empty field.** A consignor who
  entered a total quantity of "100 L" got **"100 kg"** — on the signed consignment
  note, in the total per transport category of 5.4.1.1.1.1, and written back over
  what they had typed. 100 litres of acetone is about 79 kg, and 1.1.3.6.3 counts
  litres and kilograms differently, so this was a wrong quantity on a document
  somebody signs.

  `total_quantity` sniffed the unit out of the *per package* field only. While
  that field is filled the reading is right; the moment it is empty the number
  falls back to the total-quantity field and the unit stayed on its "kg" default.
  That is not a corner of the application: the wizard requires only UN number,
  proper shipping name and class for ADR, RID and ADN, so anyone who fills in
  nothing but the total the 1.1.3.6 points count needs took this path every time.

  The unit is now read from **the same field the number came from**, and a unit
  glued to its number ("100L") counts — a word boundary does not fire between a
  digit and a letter, which is exactly how the old rule would have missed it.

- **A missing unit is now named rather than invented.** Where the input carries no
  unit at all the document shows the bare number, and the export reports it
  against ADR 5.4.1.1.1 (f) in all four languages. Defaulting to kilograms was the
  original mistake in miniature: whether a substance travels by mass or by volume
  is not reliably derivable from table A, and this application does not guess at a
  regulatory fact. Class 1 is unaffected — its quantity is the net explosive mass,
  which 5.4.1.2.1 (a) states in kilograms by definition.

- **The ADR provenance label credited the wrong source.** The rule set was
  reported as "Table A via rkstgr/adr-substances". Table A has been read out of
  the official Dutch ADR 2025 edition since v1.56.0, with the 2023 export reduced
  to the one thing that edition cannot supply — the English and German proper
  shipping names. The regulatory manifest already said so; this label had lagged
  it for five releases. A claim about where a regulatory fact came from is exactly
  the claim that must not go stale.

## [1.61.0] — 2026-08-13

### Added

- **The ADN's own table A, and with it the blue cones.** The inland waterway regime has a
  substance table of its own and EMCargo has never held it. Its first columns identify
  the goods exactly as the ADR's do, and then it asks a vessel's questions instead of a
  vehicle's: whether the goods may go in packages, in bulk or in a tank vessel, what
  equipment must be aboard, how the holds are ventilated — and **column (12), the number of
  blue cones by day or blue lights by night**.

  That column decides two things the application could not answer.

  **ADN 7.1.4.3 was half a check.** Since v1.59.0 it has applied its class rules and named
  its two cone rules as unassessed, which is honest and not much use. Both are answered now:
  7.1.4.3.2, which forbids two-cone goods a hold with one-cone flammable goods whatever the
  quantity; and the three-cone extension of 7.1.4.3.3, which sends organic peroxides and
  self-reactive substances 12 m from everything else — a provision that previously reached
  class 1 and nothing more.

  **ADN 7.1.5.0.1 had no answer at all.** Which signals a vessel must show is not a nuance
  or a warning; it is a plain fact about the voyage, and the question had nowhere to be
  asked. It is answered now, together with 7.1.5.0.4: where the load disagrees with itself
  the heaviest signal wins, so a single package of a two-cone substance sets the signals for
  everything else on board.

### Verified

- **The table was read twice and checked against a third.** The Dutch edition publishes it
  in two renderings and they do not agree in usefulness: the list pages print every row, the
  per-substance pages print one row per UN number. Where both exist, all 378 rows assembled
  from the per-substance pages appear verbatim in the list pages, all fourteen fields, with
  nothing contradicted. Then the identifying columns were checked against the **ADR** table
  A already in the repository — a different book, read from a PDF by different code in
  v1.56.0 — and the class and the name agree on every one of the 2,343 substances the two
  regimes share.

  Nine substances are in the ADN table and not the ADR's, and all nine are explained: 1499
  and 1999 are the two the 2025 edition withdrew, and 9000 to 9006 are ADN substance numbers
  that exist only for tank vessels.

  One cell disagrees. UN 2071 ammonium nitrate based fertiliser carries classification code
  M11 in the ADN and a dash in the Dutch ADR 2025, whose row for it is blank throughout. Both
  readings match their own book — checked character by character against the page — so the
  disagreement is recorded rather than resolved.

### Known limitation

- **439 of 2,352 substances get no cone count.** The table is available one row per UN
  number and the book prints several for 452 of them. Several rows is not by itself a reason
  to withhold an answer — UN 0015 smoke ammunition has three and all three carry three cones,
  because they differ only in the labels. UN 1203 petrol has three and they do not agree.
  Which kind a substance is was measured from the printed rows rather than assumed, and where
  it could not be settled the substance is **named** rather than silently guessed at. A
  consignor can act on "not settled for UN 1203"; nobody can act on "the cone rules were not
  assessed".

- **ADN 7.1.5.0.2 is not applied.** It lowers the signal count for goods carried exclusively
  in containers against a gross mass threshold, and the comparison operator on one row of
  that table is not legible in the text available here. A threshold read wrong is worse than
  one not read. Leaving it out can only overstate the signals, which is the safe direction,
  and the panel says so instead of leaving it to be discovered.

### Fixed

- **A download is asked for once, not once per run.** UNECE refuses a CI runner outright and
  the Internet Archive, which is the way round, rate-limits: the same ADN address served
  19 MB in the morning, 503 twice in the afternoon and then 498. Three runs were spent
  discovering that the internet was briefly crowded. A temporary status is now retried with
  a widening wait, and the volumes are kept between runs — including when the run fails,
  because the run that fetched one book and then tripped over the next is precisely the one
  whose first download must survive.

## [1.60.0] — 2026-08-13

### Changed

- **Only carriage by road may be used to draw up documents.** Rail, sea, inland waterway
  and air are locked: the tiles are greyed out and say why, and the wizard refuses the
  route.

  They were built, reachable, and **wrong in ways that do not announce themselves.** Inland
  waterway answered its separation question with the *road* table until v1.59.0, and it
  still has no table C — so a tank vessel consignment gets nothing at all, silently. Rail
  and sea carry known gaps of their own, listed in `docs/dg-coverage.md`.

  A half-right document is worse than no document. It gets signed and handed over, and the
  consignor has no way to see which half was right. That is the whole reason for this
  release: the application was perfectly willing to produce one.

  **The lock is checked in three places, because the tile is not the only way in.** A
  bookmark reaches `/wizard/rail` without touching a tile, and a `default_modality` set
  while a modality was open navigates there on its own, on load, before anything is
  clicked. Guarding the tiles alone would guard the honest route and leave the other two
  open — the shape of lock that is found out in production rather than in review.

  The tiles are locked rather than hidden. Hiding them raises the wrong question — *where
  did rail go?* — where the true answer is *not yet, and here is why*, in all four
  languages.

### Added

- **`frontend/src/pages/ModalitySelectPage.test.tsx`** — six tests, three of them on the
  ways in that are not the tile.

## [1.59.0] — 2026-08-12

### Fixed

- **Inland waterway consignments were being answered with a road table, and the two do not
  ask the same question.** `docs/dg-coverage.md` has ranked "mixed loading for ADN answered
  with ADR's 7.5.2" as a gap for several releases, and that wording undersold it. It was
  labelled as borrowed, which sounds like an approximation. It is not.

  **ADR 7.5.2 asks whether two packages may share a vehicle, and answers yes or no. ADN
  7.1.4.3 asks how many metres must lie between them, and whether they may share a hold.**
  A distance was not an answer this application could give at all, so a consignor reading
  "permitted" on an inland waterway shipment was reading a yes to a question nobody had
  asked.

  Two of the three rules have no counterpart in the road regime at all:

  - **7.1.4.3.1** — goods of different classes at least **3.00 m** apart horizontally, and
    never stacked on one another.
  - **7.1.4.3.3** — class 1, and the three-blue-cone goods of 4.1 and 5.2, at least
    **12 m** from goods of every other class.
  - **7.1.4.3.2** — two blue cones may not share a hold with one-blue-cone flammable goods,
    whatever the quantity.

  Read from the official Dutch edition of ADN 2025, which is a text and not a recollection.

### Changed

- **What the check did *not* assess is named in its own output.** The blue cone provisions
  come out of column (12) of the ADN's own table A, and the application holds the road
  table, which has no column (12). So the class rules are applied and the cone rules are
  reported as unassessed. A check that silently drops half a provision is worse than one
  that says which half it kept — the first reads as a clean bill of health.

  The compatibility group table of 7.1.4.3.4 is not transcribed either, and says so:
  twelve groups, four numbered conditions, and footnotes that differ from the road table's.
  A regulatory table gets two independent readings in this repository or none.

  Both wait on the same thing: the ADN's own table A and table C, which come from UNECE.

## [1.58.0] — 2026-08-12

### Added

- **High consequence dangerous goods, ADR 1.10.3.** The last heading in
  `docs/dg-coverage.md` with nothing behind it: chapter 1.10 was named in the 1.1.3.6
  exemption text and nowhere else.

  Table 1.10.3.1.2 turns out to be *easier* than it looks — but only once it has been read.
  For carriage in packages its column holds two values and no others: **0**, meaning any
  quantity at all, and footnote **b)**, "whatever the quantity, the provisions of 1.10.3 do
  not apply". There is no threshold to compare against and no arithmetic to get wrong. It
  is a membership test.

  It is worth having because **the intuition it corrects runs the other way.** Flammable
  liquids, corrosives and packing group I oxidisers all look like the dangerous end of a
  load, and in packages every one of them is footnote b): a full truck of packaged petrol
  is not high consequence dangerous goods and does not become so at a larger quantity. What
  the table catches instead is class 1 — divisions 1.1, 1.2, 1.5, 1.6, division 1.3
  compatibility group C and fifteen named 1.4 entries — the toxic gases with aerosols
  excepted in the table's own words, the desensitised explosives, packing group I toxics and
  category A infectious substances. A single kilogram of any of those qualifies.

  Where a line qualifies, the finding asks for the security plan of 1.10.3.2 and the
  photographic identification of 1.10.1.4, and names the line that caused it.

  Two things are not answered and say so rather than defaulting to "ok": **class 7**, which
  1.10.3.1.3 measures in activity against 3,000 A2 with its own limits per radionuclide, and
  the **tank and bulk columns**, whose 3,000 litre and 3,000 kg thresholds are made relevant
  by footnotes c) and d) only where table A column (10), (12) or (17) permits that form of
  carriage.

- **`backend/tests/test_adr_security.py`** — 23 tests, again weighted towards the
  refusals, because a check that answers "no" to petrol and "yes" to chlorine is only
  useful if the "no" is trustworthy.

### Fixed

- **The language guard caught a verbatim Dutch quotation in the configuration**, which is
  the guard working rather than failing. Reshaping it as an `{nl, en}` pair then tripped the
  *translation* guard, which requires all four languages — also correct, since a two-language
  block is an incomplete translation to anything that cannot see intent. Both were right and
  the field was wrong: this repository does not redistribute regulatory text, only the facts
  read out of it, so the footnote is carried in rendering with its provision number and the
  original stays in the book.

## [1.57.0] — 2026-08-12

### Added

- **Placarding and marking of the vehicle, ADR 5.3.** The last of the seven gaps in
  `docs/dg-coverage.md`, and the one carrying the note that it is "the most common
  real-world failure". The application named chapter 5.3 in its 1.1.3.6 output — *orange
  plates and placards on the transport unit* — and derived nothing.

  **That sentence was also wrong, in the direction that matters.** 5.3.1.5 gives a vehicle
  carrying packages exactly two reasons to placard: 5.3.1.5.1 for class 1 other than
  division 1.4 compatibility group S, and 5.3.1.5.2 for class 7 other than excepted
  packages. A load of packaged petrol, nitric acid or toxic liquid needs **no placard at
  all** — the orange plates of 5.3.2.1.1 are the whole of it.

  Telling a driver to placard anyway is not a harmless excess. It teaches that the placard
  is decoration, and the next load where it *is* class 1 on board is the one where that
  lesson has already been learnt. So the refusal is a stated finding with its provision
  beside it, and not an empty list — an empty list reads as a check that did not run, and
  whoever cannot tell those apart will placard to be safe.

  Three things come with it:

  - **The two numbers, printed.** Where the consignment holds one dangerous substance and
    nothing else, 5.3.2.1.6 lets the front and rear plates carry the hazard identification
    number over the UN number instead of being blank. Both come out of table A — columns
    (20) and (1) — so the check prints them rather than describing them: `33 / UN 1203`.
  - **The environmentally hazardous mark hangs on the placard, not on the substance.**
    5.3.6.1 opens *"When a placard is required to be displayed in accordance with the
    provisions of section 5.3.1"*. So packaged environmentally hazardous class 9 puts no
    mark on the truck, while the same substance beside a class 1 line does. Reading 5.3.6
    without its opening clause would mark every vehicle carrying a marine pollutant. The
    finding says in the same breath that the mark on the *package* (5.2.1.8.3) is a
    separate question, so "not the case" cannot be read as relieving it.
  - **1.1.3.6.2 relieves the unit of the plates and the placards together.** Inside the
    exemption the section says so and stops.

  What is not answered is said rather than assumed: this is **carriage in packages**. Tanks
  and bulk have their own subsections of 5.3 — numbered plates on the sides under 5.3.2.1.2
  and 5.3.2.1.4, placards for every class rather than two — and the elevated temperature
  mark of 5.3.3 turns on a carriage temperature of 100 °C liquid or 240 °C solid, which
  nobody tells the application.

- **`scripts/read_land_regulations.py` can be asked for chapter 5.3 and chapter 1.10.** The
  provisions above were quoted from ADR 2025 Volume II on a runner and implemented from
  that text, not from memory of it — the rule this repository set for itself in v1.33.0.
  The Dutch edition was read alongside as a second reading; its complete-volume PDF turns
  out to have a text layer clipped at the right margin on about 5% of its lines, which is
  worth knowing before anyone quotes from it.

- **`backend/tests/test_adr_placarding.py`** — 18 tests, weighted towards the refusals,
  because those are the findings that are easy to get wrong in the safe-looking direction.

## [1.56.0] — 2026-08-12

### Changed

- **The classification table is ADR 2025, read out of the book.** It was an export of ADR
  **2023**. That was written down honestly — the manifest has said so since v1.49.0 — and
  patched where the gap showed: v1.52.0 carried the eleven rows 2025 added in by hand and
  flagged the two it withdrew.

  A patch covers what an edition *added*. It cannot cover what an edition *changed*, and
  2025 changes a field on **316 of the 2,334** UN numbers the two editions share. Three of
  those were answers the application was giving with confidence:

  - **UN 3423 tetramethylammonium hydroxide, solid** is class **6.1**, not class 8. Labels
    6.1 + 8 instead of 8, transport category 1 instead of 2, and hazard identification
    number **668** instead of 80 — the number that goes on the orange plate.
  - **The three UN 0015 rows** have their own subsidiary hazard back: 1, 1 + 8 and 1 + 6.1.
    The export gave all three the same labels column, so the corrosive and the toxic
    variant lost their second label on the way to the document, and nothing distinguished
    the rows well enough to warn about it.
  - **UN 1950 aerosols** now stand in the ADR's own order, which opens at 5F — the
    flammable spray can, and the overwhelmingly common case. The export was sorted
    alphabetically by classification code, so an aerosol whose code the user had not given
    was filled in as 5A, the *non-flammable* row. That is the exact reading v1.51.0
    measured as costing a factor of three in 1.1.3.6 points.

  All twenty-three columns are read by the new `scripts/extract_adr_table_a.py`: **3,158
  rows over 2,345 UN numbers, no unreadable page**. Four columns the application did not
  hold before come with it — the carriage provisions of (16) to (19), the V, VC/AP, CV and
  S codes.

- **The alphabetical index turns out to be the whole of table A, set a second time.** 325
  pages against 294, different column widths, different line breaks — an independent
  typesetting of the same data. So every field is read twice and the two readings are laid
  against each other, which is the discipline this repository already applies to a machine
  reading and which could previously only be applied to the names.

  | | |
  |---|---|
  | classification code, packing group, labels, special provisions, LQ, EQ, packing instructions, all four carriage columns, hazard number, tunnel code | agree on **every** one of the 2,345 UN numbers |
  | class, transport category | agree on all but eight |

  The sixteen that differ are named rather than rounded away. Eight are the *index* failing
  over one run of its own pages — every iodine entry, which the alphabetical order puts
  together — and three are classes the table dropped that the index supplied, which is what
  a second reading is for.

- **The eleven rows transcribed by hand in v1.52.0 have become the check on the machine.**
  `adr_2025_additions.json` has stopped being a source the application reads and is now a
  fixture: a reading made by eye, off the page, of the hardest rows in the book, for the
  machine reading to be compared against. Two methods, one page, and they agree.

- **Which UN numbers ADR 2025 no longer knows is derived, not listed.** It is the
  difference between the two tables — UN 1499 and UN 1999 — and a difference cannot be
  forgotten at the next edition the way a hand-kept list can.

### Fixed

- **`is_transport_forbidden` was reading a German sentence out of a Dutch table.** The 2023
  export wrote `BEFÖRDERUNG VERBOTEN` across the row of a substance not admitted for
  carriage, and the check looked for that word in the labels column. The Dutch edition
  writes nothing at all — the row is simply empty.

  Reading the emptiness instead would have been worse than the bug: **it is also how "not
  subject to ADR" is written.** UN 1798 nitrohydrochloric acid may not be carried and UN
  1845 dry ice travels freely, and their rows are equally blank. So the prohibition is
  taken from the export, which names it in words, and the manifest errata says that is
  where it comes from. Nineteen entries that travel freely would have been refused
  otherwise.

- **The packing instruction was cut at the first space.** Table A separates the
  instructions with commas — `P001, IBC02, R001` — where the export used spaces, so the
  field came back as `P001,` with the comma attached.

### Added

- **`scripts/extract_adr_table_a.py`.** What the reading had to survive is in its module
  docstring, because none of it is guessable from the output: there are no column rules
  anywhere in the table, the layout is made anew on every page, the column numbers are
  centred over cells whose content is left-aligned, a wrapped name leaves an indent that is
  every bit as sharp a mode as a real column, the UN number is set vertically centred so a
  row does not begin where its number is, and two cells can abut with nothing between them
  so that the text layer hands over `(B1000C)V2` as a single word.

- **`backend/tests/test_adr_table_a.py`** — 24 tests over both halves of the claim: that
  the reading is sound, and that the change reached the checks that compute with it.

## [1.55.1] — 2026-08-11

### Changed

- **The repository speaks English again, including where the guard could not
  look.** v1.46.0 translated some 3,000 lines of comment and left
  `test_source_language.py` behind to keep them that way. That guard throws away
  every quoted string before it looks, on purpose — the import format really is
  `Stalen hoekprofiel 80x80x8x6000 | 8 | stuks` and a guard that fired on it
  would be switched off within the week. The exemption turned out to be a hole,
  and four kinds of prose fell through it:

  - **The changelog.** English until v1.49.0, when ten releases' worth of Dutch
    entries went in — mine, because the person I write to writes Dutch. Nobody
    reading the repository does. All ten are translated, along with v1.34.1,
    which had been Dutch since it was written. The one Dutch fragment that stays
    is the quoted error message in v1.24.1: it is an example of what the app
    actually renders.
  - **Provenance metadata in the seeds.** The `_comment`, `source` and
    `cross_check` fields say where a table came from and how it was checked —
    the closest thing this project has to a chain of custody, and written for a
    reader rather than for the code.
  - **What the scripts print.** `--help` and the self-check output of
    `scripts/extract_*.py` are the interface of a tool a contributor runs, and
    they answered in Dutch.
  - **The workflow inputs.** What `commit`, `min_agreement` and `show_un` mean
    is read from the Actions tab, and `tag-release.yml` refused a mismatched
    version in Dutch.

  The `{nl, en, de, fr}` blocks, the goods names, the Dutch proper shipping
  names out of ADR Table A and `DISCLAIMER.nl.md` are untouched. Those are the
  product.

- **The rule set manifest reads in English.** It is provenance rather than
  interface, but one line of it reaches the screen: the compliance panel shows
  the editions the result was computed with. That line now says
  `2025, with a Table A from the 2023 edition` and `67th edition (2026)`.

### Fixed

- **The comment guard could not see a JSX comment.** It read `//` and a `/*` at
  the start of a line, which is not how a comment is written inside JSX — that
  is `{/* … */}`, and it is the form the panels use. Six Dutch comments had sat
  in `DgCompliancePanel`, `DangerousGoodsStep`, `ImportColumnMapping` and
  `ResponsiveRecords` since v1.46.0 without the guard ever looking at them. It
  looks now, and found them on the first run.

- **A workflow's own prose was never scanned at all** — only its `#` comments
  were. Input descriptions, `::error::` and `::warning::` output and `echo`
  lines are what a person reading the Actions tab sees, so they are read now
  too.

### Added

- **`test_repository_language.py`**, covering the three places the older guard
  cannot reach by design: the changelog with its code spans removed, the
  provenance metadata in `backend/seed` and `backend/app/config`, and — read out
  of the syntax tree rather than with a regular expression — everything the
  scripts print. Each has a companion assertion that the scan reaches the files
  it claims to, because a scan of nothing passes just as well as a scan of
  something clean. The translation exemption is asserted rather than assumed:
  the day someone tightens this, `"nl": "Gescheiden van (separated from)"` must
  not start failing, because the fix for that would be to delete Dutch a user is
  meant to read.

## [1.55.0] — 2026-08-11

### Changed

- **The lines table now shows only the columns that genuinely fit; the rest are in the
  detail panel.** The panel of v1.54.0 gave the line the full width, but the table itself
  went on showing all thirteen columns and therefore scrolling sideways. Now the columns
  that no longer fit fall away, and that is allowed because nothing is lost: what falls
  away is in the panel, and the table says underneath how many that is.

  **Measured on the table itself and not on the window,** because here the two are not the
  same thing: the side menu can be folded open during the wizard and costs 224px. A
  breakpoint on the window width would then go on showing thirteen columns in the room for
  six. A `ResizeObserver` on the table is right in both cases.

  The columns are ranked by what you need while entering lines:

  | | Columns |
  |---|---|
  | Always stay | Description, Quantity |
  | Then | Total mass, Status, Dangerous goods package |
  | Then | Length, Width, Height |
  | Then | Mass each, Cargo form |
  | Last | Volume, Wall thickness |

  What that yields, measured in the browser, in every case **without scrolling sideways**:
  1920px all thirteen columns, 1536px eleven, 1280px nine, 1024px six.

  Two things go wrong otherwise, and both are pinned separately: length, width and height
  are treated as one — showing two of the three because the third happened to fall over the
  edge reads as a fault — and as soon as a column no longer fits it stops, rather than
  skipping that one and trying the next. The latter made the volume appear at 700px while
  the total mass fell away, and a table that leaves out the figure the whole step is for
  but does show the volume looks broken.

- **The detail icon is now a document with a magnifying glass**, instead of the list.

## [1.54.0] — 2026-08-11

### Added

- **A detail button per line, sliding a panel in from the right with every column under
  each other.** The lines table has thirteen columns of input fields and wants 1,620px; on
  anything narrower something has to give — the table scrolls sideways or the fields get
  squeezed. This is the third way out: the line you are working on gets the full width of a
  panel, one field per row, and the table may stay as wide or as narrow as it likes.

  The panel holds the **same fields** as the row behind it, not a readable copy. A panel you
  can only read would send you back to the cramped table to change anything. The line's
  actions come along at the bottom.

  The panel belongs to `ResponsiveRecords` and not to the lines table, because it has the
  same shape as the mobile card: label and value under each other. That component already
  knew how. Desktop only, because on a phone the card *is* that view.

  Further: Escape and the cross close it, focus moves into the panel and back to the button
  on closing, the page behind it is locked while it is open, and a line that disappears from
  under the panel takes the panel with it — the panel holds the line by its key and not by
  its place in the list.

- **The action buttons sit side by side and stay on the right.** They used to stack because
  the cell was too narrow for two 36px buttons; with the panel there is room for three. And
  the column is pinned to the right-hand edge, because the very button that makes the
  sideways scrolling unnecessary was itself behind that scrolling.

### Fixed

- **The description could revert itself.** The description box keeps the typed text in its
  own hands — it needs it for searching the catalogue — and never looked at the value it
  was given from outside again after the first render. With one box on screen that is
  invisible. The detail panel puts a second one on the same line: type in one and the other
  still showed the old text, and the moment you touched it, it wrote that old text back over
  what you had just entered.

## [1.53.1] — 2026-08-11

### Fixed

- **The lines table did not fit on the screen, and the input fields were too narrow to type
  anything into.** Three things worked against each other, and only all three together
  produced a usable table. Measured in the browser: the table *wants* 1,620px and was given
  1,214.

  - **The side menu folds away as soon as the modality is chosen**, with an animation to the
    left, and the button at the top left always folds it back. That is 224px. The menu
    follows the route once — on the way into the wizard and on the way out — and after that
    the user decides; otherwise it folds itself shut again the moment you open it.
  - **The shell may use the screen while the menu is away.** Folding alone was not enough:
    the app is capped at 80rem, so on a wide monitor those 224px went into the margin and
    the table was no better off. With the menu away the cap moves to 1,800px, header and
    content together so that they stay in line.
  - **The table has been given a floor.** A `w-full` table can never be wider than its
    container, so the `overflow-x-auto` around it never engaged and the browser took the
    missing width out of the cells. On a table you *read* that is fine — text wraps. On a
    table you *type* in it is not: the quantity field became 30px and the unit select 28px.
    Now the table keeps the width its fields need and scrolls horizontally when the screen
    is too small for it.

  At 1920px everything now fits without scrolling, with the quantity field and the unit
  select each a good 100px. At 1440px only the table scrolls, not the page.

## [1.53.0] — 2026-08-10

### Added

- **The transport unit's equipment is derived from the load (ADR 8.1.4 and 8.1.5).**
  Equipment was the one heading in `docs/dg-coverage.md` that called itself "the most common
  real-world failure" and was absent from every mode. That had a reason worth naming:
  EMCargo cannot see a vehicle and can therefore never establish *that* a wheel chock is
  in the cab.

  What the app *can* do is derive the list — and 8.1.5.1 asks for exactly that: the
  equipment is chosen *according to the hazard label numbers of the goods loaded*, and the
  article points at the transport document to identify those numbers. That is precisely the
  document this app draws up.

  - **8.1.5.2** — wheel chock, two warning signs, and per crew member a warning vest, a
    portable lighting apparatus, gloves and eye protection.
  - **The eye-rinsing liquid is an exemption, not a requirement.** The footnote says it is
    *not* prescribed for label numbers 1, 1.4, 1.5, 1.6, 2.1, 2.2 and 2.3. A load of propane
    cylinders is therefore not asked for one — but ammonia (2.3 *with* subsidiary hazard 8)
    is, because that one label 8 is not on the list.
  - **8.1.5.3** — an escape mask per crew member for label numbers 2.3 or 6.1, and a shovel,
    a drain seal and a collecting container for label numbers 3, 4.1, 4.3, 8 and 9 — but for
    solids and liquids only. A gas cylinder with a subsidiary label 8 has no use for a
    shovel.
  - **8.1.4.1** comes with the whole table instead of one answer, because the extinguishers
    hang on the maximum permissible mass of the transport unit and the app does not know it.
    If the consignment stays within 1.1.3.6, **8.1.4.2** replaces that table with a single
    2 kg extinguisher — one of the few places where the exemption makes a visible difference
    to what belongs in the cab.

  The label number is not the class, and that is exactly what it turns on: class 2 is "2" in
  the class column and 2.1, 2.2 or 2.3 on the label, and the footnote names the divisions.
  Read the class column and the exemption never applies to gases at all.

  The panel says what it is: a list to check against, not a finding.

## [1.52.0] — 2026-08-10

### Added

- **The eleven rows ADR 2025 added are now in, with their road transport data.**
  The classification table the app is built on is a **2023** export. UN 0514 and
  UN 3551 through 3560 — sodium-ion batteries, the new vehicle entries, disilane,
  gallium in manufactured articles and tetramethylammonium hydroxide — did reach the
  app through the IMDG 42-24 layer, but with **sea data**: no transport category, no
  tunnel code, no Kemler number. Those three columns exist only in ADR Table A.

  So anyone shipping sodium-ion batteries by road got no points factor, and the
  1.1.3.6 table reported the line as incomplete without being able to say *what* was
  missing.

  Eleven rows is few enough to transcribe by hand, and that is also how this repository
  deals with a regulatory table. What makes it defensible is the same discipline as
  everywhere else: every row was **read twice**, from Table A and from the alphabetical
  index of the same edition — two independent typesettings — and the page it appears on
  was recorded with it.

  | UN | Transport category | Tunnel code | Kemler |
  |---|---|---|---|
  | 0514 | 4 | E | — |
  | 3551 / 3552 | 2 | E | — |
  | 3553 | 2 | B/D | 23 |
  | 3554 | 3 | E | — |
  | 3555 | 2 | B | — |
  | 3556 / 3557 / 3558 | — | — | — |
  | 3559 | 4 | E | — |
  | 3560 | 1 | C/E | 668 |

  That the vehicle entries get no transport category and no tunnel code is not a
  misreading: UN 3166 and UN 3171 do not have them in the existing table either.

### Changed

- **UN 1499 and UN 1999 now say for themselves that ADR 2025 no longer knows them.** They
  remain findable — an older transport document may refer to them, and a lookup that
  returns nothing reads as "this UN number does not exist" — but they no longer pass for a
  current entry.

## [1.51.0] — 2026-08-10

### Fixed

- **One UN number, several Table A rows — and the app silently picked one.** This is the
  most expensive thing the pass over the ADR side turned up.

  The row was chosen on **packing group**, and a warning appeared as soon as a UN number
  had more than one. That covers UN 1263 paint and UN 1993 N.O.S. and it reads like the
  whole problem. It is not.

  **UN 1950, aerosols, has twelve rows in Table A and not one of them has a packing
  group.** They are told apart by the classification code in column (3b):

  | Code | Labels | Transport category | Tunnel code |
  |---|---|---|---|
  | 5A | 2.2 | 3 | E |
  | 5F | 2.1 | 2 | D |
  | 5T | 2.2 + 6.1 | 1 | D |

  Anyone shipping ordinary flammable aerosols — by far the most common case — got the
  non-flammable row. Transport category 3 instead of 2 is a points factor of 1 where the
  ADR prescribes 3, so a load of aerosols scored a third of what it should and could keep
  an exemption it had actually lost. The tunnel code came out as E instead of D, and the
  flammable label was missing from the document. Without a word, because every row has the
  same (empty) packing group.

  UN 2037 gas cartridges has nine such rows. UN 0015, 0016 and 0303 have three each that
  differ only in whether the ammunition carries a corrosive or a toxic label — a subsidiary
  hazard that dropped silently off the description line. And even choosing a packing group
  does not always settle it: UN 1263 has three PG III rows, one with tunnel code D/E and
  Kemler 30 and two with tunnel code E and neither.

  Fifteen UN numbers were resolved this quietly. The row is now chosen on classification
  code first, and what remains open is named: how many rows, what they differ in, and which
  field decides it. Where no field the user fills in tells them apart — the three ammunition
  rows are all 1.2G — the note says so, instead of naming a field that cannot work.

- **Fourteen UN numbers have no usable English proper shipping name, and the German one was
  substituted without notice.** UN 3245 genetically modified organisms, UN 3374 acetylene
  solvent free, UN 2807 magnetized material and eleven others have an empty `name_en` in
  the Table A export; UN 1139 has the truncated "Coating solution (". The fallback to
  German stays — an empty field is worse — but the export now warns: IMDG 5.4.1.4.1 and
  IATA DGR 8.1.2.1 require English, and ADR 5.4.1.4.1 asks for English, French or German
  alongside the Dutch.

## [1.50.0] — 2026-08-10

### Added

- **The tunnel code is now worked out as well, not just printed.** The code from column (15)
  was already on the transport document — 5.4.1.1.1 (k) asks for it — and was assessed
  nowhere else. That is the more dangerous half of the two: anyone reading `(D/E)` on a CMR
  may assume someone thought about what that means for *this* load. They had not.

  Read from ADR 2025 and applied:

  - **8.6.3.2** — the most restrictive code in the load applies to the **whole** load. A
    driver picks one route and needs one code, not a list to weigh up. The order of
    restrictiveness is nowhere written out in words; it is the order of the table in 8.6.4,
    and that is where it comes from.
  - **8.6.3.3** — goods carried in accordance with 1.1.3 are not subject to tunnel
    restrictions **and do not count** towards establishing the code. So for a consignment
    within the 1.1.3.6 exemption there is no code to assign at all. The one exception the
    article names: a transport unit that must carry the LQ marking of 3.4.13 is barred from
    category E tunnels, however mild the codes of the goods themselves are.
  - **The table in 8.6.4** — which tunnel categories are prohibited per code. `B1000C` and
    `C5000D` split on the total net explosive mass per transport unit, and that is summed
    over the whole unit rather than read per line. The worked example from the ADR itself —
    UN 0161, 3,000 kg, prohibited by D and E — is fixed as a test.

  The outcome appears in the compliance panel and with the export. What EMCargo does not
  know is stated alongside it: which tunnels lie on the route and what category they fall
  in (that is the carrier's, 1.9.5), and whether carriage is in bulk or in tanks — which is
  stricter for five of the twelve codes.

- **ADR 3.5.1.3 and 3.5.1.4 are applied.** Two provisions that are only visible across
  lines, and that went wrong in opposite directions:

  - **3.5.1.3** — excepted quantities with different E codes packed together in one outer
    packaging are bounded by the most restrictive code. 400 g of an E1 substance next to
    200 g of an E3 substance is above the 300 g that then applies, while each line on its
    own sits well within its own code. Exactly the package the line-by-line check let
    through.
  - **3.5.1.4** — the smallest quantities under E1, E2, E4 and E5 (at most 1 g/ml per inner
    packaging and 100 g/ml per package) are subject only to 3.5.2 and 3.5.3. The mark of
    3.5.4 and the limit of 1000 packages in 3.5.5 then do not apply — so those packages no
    longer count towards that limit. The app was refusing a load the ADR allows.

### Changed

- **The 8.6.3 outcome goes onto the document.** The code per substance was already on it;
  the code for the whole load — the one 8.6.3.2 asks for and the one the driver acts on —
  had never been.

## [1.49.0] — 2026-08-10

### Added

- **The Dutch proper shipping names from the ADR are now in.** Until now the app knew every
  UN number only by its English and German name, because the Table A export it is built on
  has only those two columns. In four places in the source and the documentation it
  therefore said the ADR has no Dutch name. That is not true. The ADR appears in an
  official Dutch edition and column (2) of Table A reads BENZINE, ZOUTZUUR,
  LITHIUM-ION-BATTERIJEN there. Only the export did not have it.

  That column has now been read out: **2,345 UN numbers, 3,158 rows, 294 pages**. There is
  no open source for it — this column is nowhere on the internet — so it was read from the
  book itself by the new `scripts/extract_adr_names.py`. The book itself does not go into
  the repository; only the derived fact, exactly as `docs/data-sources.md` promises for
  every other regulatory source.

- **Searching on a Dutch substance name works.** Typing "zoutzuur" returned nothing,
  because the search index held only English and German. UN 1789 is now top of the list,
  "benzine" finds UN 1203 and "lithium-ion" finds UN 3480.

### Changed

- **A Dutch road document carries both names.** ADR 5.4.1.4.1 asks for an official language
  of the country of dispatch and, if that is not English, French or German, **in addition**
  for one of those three. Dutch is the only language that therefore cannot stand alone. The
  description line now reads `UN 1203, BENZINE OF MOTORBRANDSTOF (GASOLINE), 3, II, (D/E),
  10 jerrycan, 200 L` — on the CMR, on the AVC consignment note and in the field itself.
  For sea and air it stays the English name alone, because IMDG 5.4.1.4.1 and IATA DGR
  8.1.2.1 want one. Draw up a Dutch road document first and add a sea leg afterwards and
  the IMO DGD gets `GASOLINE` by itself, just as with the German name.

- **The regulatory manifest now says what is really in there.** While reading out the Dutch
  names the classification table turned out to be an **ADR 2023** export, not a 2025 one,
  while the manifest reported "2025". That is now stated, along with what it costs: UN 0514
  and UN 3551 through 3560 are missing from that table — they are in the app, but with sea
  data from IMDG 42-24 and without transport category, tunnel code and Kemler number — and
  UN 1499 and UN 1999 are still in it while ADR 2025 no longer knows them.

### Fixed

- **Clicking a search suggestion undid what the list had got right.** The suggestion showed
  the name in the language the chosen profile allows, but clicking it put the English
  column in the field. The field now gets what was in the list.

## [1.48.0] — 2026-08-09

### Fixed

- **The error messages spoke Dutch, and only Dutch.** Everything on screen was translated
  into four languages and the errors were not: they were written straight into the `raise`
  as Dutch sentences. A German user who uploaded an empty file was told so in Dutch; so was
  a French one who asked after a UN number the ADR table does not hold. Nineteen messages
  in all — ten HTTP errors, six import limits, two quantity validators and the per-row
  message of the equipment import.

  It is the kind of gap nobody reports, because it only appears once something has already
  gone wrong — the moment the user is least able to work out what happened.

- **The equipment import reported its per-row problems in Dutch too**, in a list shown
  verbatim on screen. Those are now structured the same way and translated per row.

- **An upload error read "Upload failed" where the server had said exactly what was
  wrong.** `uploadFile` assumed `detail` was a string and fell back to a generic sentence
  for anything else. It now goes through the same reader as every other error.

### Changed

- **The server no longer writes sentences; it writes codes.** It cannot translate: an
  error is raised deep in a service that has no idea who is asking, and the language
  belongs to the screen. So the API sends `{"code", "message", "params"}` — the interface
  looks the code up in its own language files and falls back to the English `message` when
  it does not know it.

  That fallback is what makes it safe to deploy: a backend newer than the frontend in
  front of it can send a code the language files do not have yet, and the user still reads
  a sentence rather than a dotted key.

  Schema validators use `PydanticCustomError`, which puts the code in the `type` field of
  the 422 body and the parameters in `ctx` — the mechanism FastAPI already had, rather than
  a convention invented on top of the message text.

- **The operator log speaks English**, along with the rest of the source. The startup
  messages about `APP_SECRET_KEY`, CORS and the admin password were the last Dutch text
  outside the language files.

- Tests that matched on a Dutch sentence now assert on the code. Pinning the wording of a
  message is what makes it painful to translate — and these had to be changed by hand for
  exactly that reason.

### Added

- **`test_error_messages.py`.** Every code has a translation in all four languages; the
  interpolation names survive that translation, because a sentence that loses its
  `{{limit_mb}}` loses the number it was about; the Dutch file is not the English one
  copied; and — the guard that matters most — no message to the user is written in Dutch
  at the raise site any more. That last one reads the `raise` calls rather than the
  catalogue, because a sentence typed straight into `HTTPException` never passes through
  the catalogue at all.

  Both guards were verified by breaking the code on purpose and watching them fail.

### Documentation

- `AGENTS.md` and `docs/development.md` state the rule, so the next message added goes
  through the catalogue instead of round it.
- `docs/user-guide.md` adds error messages to the list of what follows your language.

## [1.47.0] — 2026-08-09

### Fixed

- **`MAX_PASTE_BYTES` was a setting that did nothing.** It sat in `Settings` with a
  default of 512000 and in `docs/configuration.md` as "maximum size of a pasted import",
  and no line of the application ever read it. The upload cap has always come from
  `MAX_IMPORT_BYTES` in `spreadsheet_io.py` — 10 MB, alongside caps on rows, columns and
  uncompressed `.xlsx` size that are safety limits against a malformed file, not
  preferences. The variable is gone and the real limits are documented instead.

  A documented setting that does nothing is worse than an undocumented one: it invites
  somebody to tune it and then conclude the app ignores them.

- **`APP_NAME` was documented as "the name shown in the interface".** It is the FastAPI
  title and the `app` field of `GET /api/health`; the interface takes its name from its
  own language files and always has.

- **`ROADMAP.md` still advertised 400 goods**, three releases after the catalogue reached
  1,093 — and Dutch, English and German, two releases after French. Nothing breaks; the
  number was simply a lie in the shop window.

- **`docs/getting-started.md` pinned v1.33.0** as the example version to pull and to keep
  when cleaning up Docker Hub tags.

- **`2,928 UN numbers` was never right.** `un_numbers.json` holds 2,928 ADR Table A
  **rows** over **2,336 UN numbers** — a substance with several packing groups has a row
  per group. Three documents stated the row count as a UN-number count. Every other figure
  on those pages was re-measured against the seed files and is correct: 2,338 EmS
  schedules, 2,860 DGL rows over 2,347 UN numbers, 629 segregation assignments over 539 UN
  numbers, 110 stowage/handling/segregation codes, 2,849 UN cards.

- Missing entries in three tables of contents, including the **Settings** section added in
  v1.45.0.

### Added

- **`test_documentation_matches_the_app.py`.** Three guards, each pinning a defect this
  pass actually found: every `Settings` field is documented and every documented variable
  is still a setting; the goods count claimed anywhere in the documentation is the count
  in `materials.json`; and every internal link resolves to a file *and* an anchor that
  exists. Prose and regulatory reasoning are deliberately not guarded — those cannot be
  checked mechanically and the suite should not pretend otherwise.

- **`docs/development.md` explains that there is no migration runner.** `create_all`
  creates missing tables and never adds a column to an existing one, which is why the
  settings tables hold JSON and why `startup.SETTINGS_TABLES` exists. That was load-bearing
  knowledge living only in a test docstring.

### Documentation

- The **Settings** screen now appears where a reader would look for it: the transport-mode
  step of the user guide, the signature section of `docs/documents.md`, the first-admin and
  troubleshooting sections of `docs/getting-started.md` — the last of those because
  "address search returns nothing" now has a legitimate cause that is not a fault.
- `docs/dg-coverage.md` is stamped v1.47.0 with a note that nothing in it has changed since
  v1.41.0: v1.42.0 to v1.46.0 touched the catalogue, the interface language, the settings
  and the source comments, and not one regulatory check.
- `.env.example` speaks English along with the rest of the source.

## [1.46.0] — 2026-08-09

### Changed

- **The source speaks English.** Roughly **3,000 lines of comment and docstring**
  across `backend/app`, `backend/tests`, `scripts/`, `frontend/src`, the workflows and
  `.env.example` were Dutch. That was defensible while one person wrote all of it and
  stopped being defensible the moment anyone else read it — because this project puts a
  great deal of its reasoning *in* those docstrings. A test that explains which defect
  provoked it is worth nothing to a reader who cannot read the explanation.

  Nothing a **user** reads changed. The interface files, the seed labels, the field
  names and the regulatory texts stay in four languages; only what a developer reads was
  translated. The test docstrings kept their length and their voice — they still name the
  defect, the measurement and the trade-off, in English now.

- **A new package line starts in `pcs`.** Left over from v1.45.0: `WizardPage` still had
  the Dutch string in two more places.

### Added

- **`test_source_language.py` keeps it that way.** Without a guard, the next change adds
  one Dutch comment, the one after it adds three, and in a year the work has to be done
  again. It scans every comment and docstring in those five trees.

  Two things it does *not* do, both deliberate. It ignores text inside string literals,
  because Dutch in a string is data — the import format is
  `Stalen hoekprofiel 80x80x8x6000 | 8 | stuks` and the AVC form's own column is called
  `gewicht in kg`. And its word list holds only function words, leaving out anything that
  collides with English: "door" is a Dutch preposition and an English noun, and this
  repository really does write about the back door of a CI pipeline. A guard that cries
  wolf gets switched off.

### Documentation

- `AGENTS.md`, `CONTRIBUTING.md` and `docs/development.md` state the rule, so it is a
  convention rather than a one-off sweep. `AGENTS.md` also still said "three interface
  languages"; French arrived in v1.44.0.

### Internal

- The translation ran through a line-based extract/splice tool rather than an AST pass.
  The previous bulk edit in this repository used `ast` column offsets, which count UTF-8
  **bytes**, and dropped text outside the braces of every dict containing a word like
  "Träger". Whole lines have no such trap. The tool also refuses to replace a block that
  contains code — a string constant's closing `"""` looks exactly like a docstring
  opening, and three such blocks were caught that way instead of deleting the code
  between them.

## [1.45.0] — 2026-08-09

### Added

- **Settings that belong to you, and settings that belong to the installation.** Until now
  the settings screen offered two things: a theme and a language. Both lived in
  `localStorage`, which is to say in one browser — sign in from a second device and the app
  was back in Dutch on a white background. Neither was ever really *yours*.

  They are stored with the account now, and they brought company. Per user: the transport
  mode to open straight into, the unit a new package line starts with, and the details that
  are the same on every consignment and were retyped on every consignment — consignor name,
  address and contact, the usual carrier, the loading point, the 24-hour emergency number
  that IMDG 5.4.1.5.11 and the IATA DGR shipper's declaration both ask for, and a signature
  drawn once instead of once per shipment. They are filled in only where the field is still
  empty: a prefill that overwrites what somebody just typed is worse than no prefill.

- **An administrator section.** Instance-wide, behind `require_admin`, and it exists mainly
  for one question: *does this installation talk to the internet?* Address autocomplete and
  the startup catalogue sync are the only two requests EMCargo makes outward, and they
  now have switches next to each other. Also there: the language and theme new users start
  with, the organisation name and address offered as a consignor to anyone who has not
  filled in their own, whether the UN card download is offered, and how long a session
  lasts.

  Each switch was checked through the endpoint it governs rather than only through the
  store. A toggle that saves but changes nothing is worse than no toggle — the
  administrator believes address lookups are off.

- **The environment variables still decide when nothing is saved.** `GEO_ADDRESS_API_URL`,
  `CATALOG_AUTO_SYNC` and `ACCESS_TOKEN_EXPIRE_MINUTES` were the only way to configure
  these until now and are documented as such. A stored setting is an *overlay* on top of
  them, so an installation that never opens this screen behaves exactly as its `.env` says.
  What it gains is that a change no longer needs a container restart.

### Changed

- **A new package line starts in `pcs`, not `stuks`.** The default unit was the literal
  Dutch string, hard-coded in the wizard, and it reached German and French screens too.

### Fixed

- **The French translation was never actually compared.** `translations.test.ts` checks
  that every language file carries the same keys, in a loop that read
  `for (const language of ["en", "de"])`. French was added in v1.44.0 and fell outside it —
  the language with the most room for gaps was the one language not being checked. The loop
  is derived from `SUPPORTED_LANGUAGES` now, so a fifth language cannot slip past it either.

### Internal

- **The settings tables hold one JSON document each, and that is deliberate.** This
  application has no migration runner: `init_app` calls `Base.metadata.create_all`, which
  creates *missing tables* but never adds a column to a table that already exists. A
  column-per-setting schema would have worked perfectly on a fresh install and broken every
  upgrade with "no such column". With a JSON payload the schema never changes again —
  adding a preference is a field on a Pydantic model, and a database written by an older
  version simply lacks the key and falls back to its default. `test_settings.py` pins that
  in both directions, along with what a corrupt or no-longer-valid payload must do: fall
  back, not take the app down.

- Removed a dead `Field` component and its style constant from `WizardPage.tsx`.

### Documentation

- `docs/configuration.md` opens with which of the two places wins, and a table of the
  environment variables that now have a screen counterpart — including when each takes
  effect, because the catalogue sync is read at startup and cannot take effect sooner.
- `docs/user-guide.md` has a **Settings** section, with the administrator part separate.
- `docs/privacy.md` names the stored signature explicitly. It is the only image EMCargo
  keeps, it is opt-in, and a document about what is *not* stored has to be exact about what
  now is.

## [1.44.0] — 2026-08-09

### Added

- **French, as a fourth language.** Not for reach — for the regulations. ADR, RID and ADN
  are published by UNECE and OTIF in English, **French** and Russian; the CMR and the CIM
  are French documents by origin, abbreviations included. Anyone preparing a waybill for a
  Belgian, French, Luxembourgish or Swiss leg needs the French wording because the
  authority at the roadside reads it, not as a courtesy.

  Complete on arrival, because a half language is worse than none: **1,706 translated
  blocks** in the data files, **161 dictionaries in the source code**, **335 interface keys**
  and the **1,093 goods** of the catalogue.

  The vocabulary is the one the French editions use, not a dictionary rendering: *fût* and
  *jerricane* rather than "tonneau", **GRV** for an IBC, *désignation officielle de
  transport* for the proper shipping name, *séparation* against *arrimage*, *disposition
  spéciale* for a special provision, and for the CMR the terms of the convention itself —
  *expéditeur*, *destinataire*, *prescriptions d'affranchissement*.

  A missing French text falls back to English before Dutch: that reader gets further with
  English. It should rarely fire — `test_languages.py` refuses an incomplete language — but
  it does apply to goods a user adds or renames themselves.

### Changed

- **The language guards no longer name a language.** `test_languages.py`,
  `test_catalog_search_language.py` and the frontend's `translations.test.ts` had `"de"`
  written into them. That is fine until a fourth language arrives, and then the guard does
  not guard it: the tests kept passing while French was missing everywhere, and two of them
  actually *failed* on French being present because they asserted the set was exactly
  `{nl, en, de}`. A guard that treats a new language as an error is not a guard.

  They all read `SUPPORTED` now and require every language in it beyond the two source
  languages. Switching on a fifth is one line in `app/core/languages.py`, and the tests
  immediately say what is missing.

### Fixed

- **The French for boxwood is *buis*, which is Dutch for a pipe.** The catalogue search
  deliberately matches across all languages — someone typing "Stahl" while reading Dutch
  should still find steel — so a bare `Buis` on boxwood outranked every Dutch search for a
  tube. Boxwood is now `Bois de buis`, which is equally correct and does not collide. Found
  by two existing tests, which is what they are for.

### Documentation

- README, `CONTRIBUTING.md`, `docs/user-guide.md`, `docs/data-sources.md` and
  `docs/development.md` name the fourth language.

- **`docs/dangerous-goods.md` states what French does *not* get.** The interface, the
  labels, the compliance findings and the goods database are French; the proper shipping
  name is not. The ADR Table A export this application is built on carries an English and a
  German name column and no French one, so a French user preparing a road document gets the
  English name rather than `ESSENCE`. That is a gap in the data, not in the translation, and
  it is written down rather than papered over with a name no table prescribes.

## [1.43.0] — 2026-08-09

A clearing-out. Nothing here changes what the application answers; it changes how much of
it there is.

### Removed

- **Two scripts that had finished their work.** `purge-history.sh` says so itself — *"Status:
  reeds uitgevoerd (juli 2026)"* — and `cleanup-dockerhub-tags.sh` was never wired to
  anything: the Cleanup Docker Hub tags workflow carries its own copy of that logic inline.
  Both remain in the git history if they are ever wanted back.

- **Four functions with no callers anywhere**: `decode_access_token` (a compatibility
  helper for callers that never arrived), `stowage_code_text`, `manifest_summary`, and the
  four schema classes `MaterialBase`, `MaterialOut`, `ProfileBase`, `ProfileOut`.

- **Twelve unused imports** across the backend, the tests and the scripts.

### Changed

- **The pipeline computes the solid block through `calc_solid_block` instead of writing the
  formula out again.** This is the one item here that is more than tidying. The calculation
  engine holds a function for it, and the pipeline computed `w * h * length_m` and then
  `* density` in two separate branches — the same formula in three places, two of them out
  of reach of the tests that check the engine. It is the pattern this project has paid for
  four times: `calc_round_bar` and `calc_round_tube` also sat there uncalled until v1.37.1,
  and a round bar weighed 27% too much for as long as they did.

  `test_no_dead_code.py` now asserts the general form of it: every `calc_` function in the
  engine has a caller outside the engine.

- **A `.dockerignore`.** There was none, so the whole working tree went to the daemon as
  build context on every build, `.git` included. Measured: **637 MB before, 586 MB after**.

### Documentation

- **`un_cards/` is not empty, and the cost is now written down.** Both `docs/data-sources.md`
  and the `Dockerfile` said the folder is empty in a fresh checkout and gets filled by a
  workflow. That was the design. What the repository actually contains is **2,849 PDFs,
  575 MB**, and the `Dockerfile` copies them into the image — roughly nine tenths of what a
  `docker pull` transfers, paid by every installation on every update, including the ones
  that never open a UN card.

  They are not dead weight: the UN card export serves exactly those files. But 575 MB per
  pull is a decision rather than a default, and nothing in the repository said so. Nothing
  is removed here; the number is now visible, with the two ways out named.

### Note on the method

While clearing out, a deletion without an end boundary truncated
`app/services/dg/amendment_42_24.py` and took `not_covered()` with it. 117 tests went red
and the cause was clear within a minute. Worth recording, because the risk in a clearing-out
is never what you meant to remove.

## [1.42.0] — 2026-08-09

### Added

- **The goods database grows from 400 to 1,093 entries**, each with a density, a min/max
  band, search aliases and a name in Dutch, English and German. What came in is what
  actually moves: 173 more agricultural commodities (grains and their by-products, oilseeds
  and meals, pulses, nuts, vegetables, fruit, spices), 68 more timbers including the
  tropical hardwoods a shipper meets on a packing list, 56 more steel and non-ferrous
  products in the form they travel in — coils, plate, rebar, billets, cathodes, turnings —
  76 more liquids and 43 more chemicals, 67 more construction materials, 39 more ores and
  minerals, and the rest spread over food, plastics, paper, textile, packaged general
  cargo, waste and insulation.

  Eighteen candidates were dropped during the merge because they turned out to repeat a
  good that was already there. That is worth saying out loud: a second entry for the same
  goods is worse than no entry, because the user picks one of the two and which one he
  picks decides his weight.

- **`test_materials_catalog.py` holds the invariants** that at 400 entries you could still
  check by eye and at 1,093 you cannot: no good appears twice, no alias belongs to two
  goods, all three languages are present on every good, every category is one `units.py`
  knows — an unknown one would silently fall back to the default density basis — and every
  density lies inside its own min/max band.

### Fixed

- **Searching for a good could return a different good entirely.** Before a query is
  matched it is normalised against a synonym table, and that table is not the small
  hand-written file it looks like: every alias of every good is added to it, so it holds
  some 4,400 keys. The replacement worked on character sequences rather than words. What
  that did, measured on the old 400-entry database:

  | typed | rewritten to | top hit |
  |---|---|---|
  | `broccoli` | `meel / bloem / bloemsteenkool (kisten)` | Flour |
  | `cashew` | `cessenew` | Ash *(the wood)* |
  | `Kupferkathoden` | `koperkathoden` | Copper |

  "cashew" contains "as", which is an alias of ash wood. The query was rewritten into
  something else and the good the user had literally typed did not even make the list. This
  predates the expansion — but more goods means more short aliases, so it was going to get
  worse, not better. A synonym now has to match a whole word, accents included: `\b` does
  not count ü or é as word characters, so "kupfer" inside "Kupferkathoden" needed its own
  boundary.

- **A good's own name now outranks another good's alias.** Cauliflower carried `broccoli`
  as an alias, so typing "broccoli" landed on cauliflower even though broccoli is itself in
  the database. Two things were wrong: the synonym table let a stray alias claim a name
  before its owner could, and the scoring left the two tied so the order of the rows
  decided. Names are registered before aliases now, and an exact match on a good's own name
  scores higher than a match on someone else's alias.

- **The stray `broccoli` alias is removed from cauliflower** in the seed. Note what that
  does and does not reach: the catalogue sync deliberately folds locally present aliases
  back in so that anything added by hand survives an update, which means a *deletion* never
  propagates. A fresh install is clean; an existing one keeps the alias but is no longer
  misled by it, thanks to the ranking fix above.

### Performance

- The first version of the word-boundary fix dropped the cheap substring pre-check and ran
  a regular expression over all 4,400 synonyms. That was correct and unusable: **1,446 ms
  per search**, against roughly 20 ms before. The pre-check is back in front of the regex.
  Measured end to end on the full 1,093-entry database: **median 63 ms per search, 115 ms
  at the slowest**, against 20–53 ms on the old 400-entry database. Search does get slower
  when the catalogue is 2.7× larger; it does not get slower per good.

### Documentation

- `docs/data-sources.md` now carries the count per category and states how a new good
  reaches an installation that is already running. The page implied it could not:
  `seed_catalogs` fills the table only when it is empty. That is true of `seed_catalogs`
  and false of the application — the startup catalogue sync reads the same seed file and
  upserts. Measured rather than assumed: seeding an old database, adding one good and
  restarting, `seed_catalogs` added nothing and the sync added it.

## [1.41.0] — 2026-08-08

### Added

- **Table 7.5.2.2 is read instead of pointed at.** When a consignment held class 1 packages
  of more than one compatibility group, EMCargo counted the groups and handed the
  question back: *check the compatibility groups.* That is honest, and it is also the one
  question the user cannot answer — they do not have the book. The table is now in the
  configuration and gets read: an empty cell is a refusal, an X passes without a word, and
  the four footnotes come back as the condition they actually state.

  So detonators (group B) beside a blasting explosive (group D) no longer produce "check the
  table" but footnote (a): permitted, provided the two are effectively segregated by separate
  compartments or a special containment system, in a manner the competent authority has
  approved. Group N beside C, D or E returns both footnotes printed in that cell, because
  both apply. Two packages of group L return footnote (d): only with the same type of
  substance.

- **Rail gets its own table, and it is not the same table.** RID 7.5.2.2 was read on page
  1102 and compared cell by cell with ADR's on printed page 593. The tables are identical
  except for one thing: **RID has no compatibility group A.** Road runs A to S, rail B to S,
  and neither text lists group K. That is a difference in what the table answers rather than
  in an answer, so a rail leg is evaluated against the rail table, and a group A package on
  rail is told the table does not cover it — instead of quietly being handed ADR's row. The
  four footnotes are word for word the same in both texts.

  How the reading of the grid was checked: both tables are symmetric, and
  `test_compatibility_table_7522.py` asserts it. A table of crosses arrives from a PDF as a
  column of loose characters, and miscounting one column produces something that still looks
  plausible — but loading together is reciprocal, so a shifted column almost certainly breaks
  the symmetry somewhere.

- **RID 7.5.3, the protective distance.** The provision listed as the most concrete open item
  for three releases, read from page 1103 and implemented. A unit placarded 1, 1.5 or 1.6
  must be separated on the same train from one placarded 2.1, 3, 4.1, 4.2, 4.3, 5.1 or 5.2
  by 18 m, or by two 2-axle wagons or one wagon with four or more axles.

  Two things the text says precisely and that are easy to read past. **Model 1.4 is not among
  the triggers** — it has its own placard model — so a wagon carrying only division 1.4 goods
  falls outside. And **the counterpart list is short**: classes 6.1, 8 and 9 are not on it,
  however dangerous they are otherwise.

  This is the one provision where borrowing the ADR chapter would not have produced a rougher
  answer but no answer at all: 7.5.3 is about how a train is made up, and a road transport
  unit travels alone. Since EMCargo cannot see the rest of the train, a consignment with a
  class 1 wagon and no counterpart of its own still gets the provision, addressed to the
  carrier, rather than silence.

### Fixed

- **1.4S counted for the compatibility table after all.** Footnote (a) to 7.5.2.1 takes 1.4S
  out of the comparison with *other classes*, and the code carried that exception into
  7.5.2.2 as well. But 7.5.2.2 is about explosives among themselves and has a row S, and that
  row is not all crosses: S against group L is empty, so prohibited. Carrying an exception
  from one provision into another had been silently approving that combination.

- **Rail cited a code the RID does not have.** RID column (18) names the foodstuffs provision
  **CW 28**; EMCargo quoted ADR's CV28 on rail too. The text of 7.5.4 is identical in both
  regimes so nothing changes about the requirement, but a CIM quoting a code that does not
  exist in its own regime is the same category of defect as the tunnel code that used to be
  printed on it: information the application added itself.

### Documentation

- `docs/dg-coverage.md`: rail is no longer described as mostly road on loan. Its quantity
  calculation, mixed-loading table, compatibility groups and protective distance are now all
  cited to RID. Recorded in passing and deliberately not implemented: **RID 7.5.2.4**, which
  prohibits loading limited quantities together with any explosive except division 1.4 and
  UN 0161 and 0499. It needs nothing the application does not already compute, and it is
  named as the next rail item.

## [1.40.1] — 2026-08-08

### Fixed

- **Two explosives in one consignment produced a server error instead of an answer.**
  Detonators of compatibility group B next to a blasting explosive of group D — an
  everyday combination — made the compliance check raise `TypeError` rather than return a
  result. Both the panel in the wizard and the export run through `check_compliance`, so
  no document came out either.

  The fault was on the seam. v1.38.0 turned `class1_products` from a list of labels into a
  list of `(label, UN number)` pairs, because the footnotes of table 7.5.2.1 need the UN
  number. The 7.5.2.2 message a few lines below still called `", ".join(class1_products)`
  and has been handed tuples ever since.

- **And the reason nobody noticed is the second defect.** The compatibility group was read
  from the *class* field with a tight anchor, and ADR Table A puts only "1" in the class
  column for explosives — the division and its compatibility group live in the
  classification code. So on every row that comes straight out of the seed data, the check
  found no group, 7.5.2.2 never fired, and the broken line was never reached. A check that
  never ran looked exactly like a check with nothing to report. The group is now read the
  way the IMDG side has always read it: classification code first, then class.

  Two defects that covered for each other — the silent one masked the loud one. Measured
  on the real data before the fix: 344 of 4,000 random consignments of two to five UN
  numbers ended in an exception, 8.6%.

- **A class 1 package with a subsidiary risk beside another class 1 package took the sea
  check down.** In the IMDG 7.2.4 class table, class 1 against class 1 is `*`, which refers
  on to 7.2.7 rather than stating a distance itself. The search for the strictest cell
  compared `int(value) > int(worst)` as soon as anything had been found, so a `*` followed
  by a number was `int("*")`. A number now always beats a `*`, which is what the code
  intended all along.

### Added

- **A sweep that no single provision owns.** Both defects above were found by running the
  compliance check over consignments assembled from the seed data along the same path the
  wizard takes, not by reading code — and they were only findable that way, because a bare
  seed row carries "1" in the class column and it is `derive_product` that fills in the
  division. `test_class1_compatibility_groups.py` keeps a seeded version of that sweep:
  300 consignments per rule set, asserting nothing about any particular rule, only that no
  consignment can make the check fall over.

## [1.40.0] — 2026-08-08

### Changed

- **A release no longer builds anything.** The tag used to recompile the identical commit
  from scratch — four to six minutes for bits that already existed — and run both test
  suites over them a second time. The image `main` built, tested and pushed under its short
  SHA was sitting there the whole time.

  A tag is a name, not a build. `tag-release.yml` now puts the version on that existing
  manifest with `docker buildx imagetools create`: server-side, both architectures, in
  seconds. It is also stricter than a rebuild — what gets released is bit for bit what went
  green through CI, instead of a second compilation that could differ from the first.

  Nothing changes about what is published or when. `latest` still follows `main`, every
  merge still produces a testable image, and `:<version>` still appears on Docker Hub with
  both architectures. Only the second compilation is gone.

  If `main`'s build has not finished, the release waits for the SHA tag to appear and gives
  up after twenty minutes rather than putting a version number on an older image.

- **`ci.yml` no longer triggers on `v*` tags.** With the retagging above there is exactly
  one way a version image comes into existence. Two routes to one outcome is how they drift
  apart.

## [1.39.0] — 2026-08-08

### Changed

- **The same work was being done twice on every push.** `ci.yml` and `dockerhub.yml` were
  both named `CI` and both triggered by pushes to `main` and by every pull request, so
  `pytest` ran twice and `npm ci` ran twice per commit — five checks, two of them a copy of
  two others. A release with three commits on the branch spent fifteen jobs before anything
  was merged. They are now one workflow with three jobs: Backend tests, Frontend build,
  Docker build. The more thorough of the two frontend jobs was kept, so the audit and the
  Vitest run survive.

- **arm64 is built only when an image is actually published.** It is emulated through QEMU
  on an amd64 runner, and that emulation was most of the wall clock. A pull request pushes
  nothing, so its Docker build is a smoke test of the Dockerfile and `linux/amd64` answers
  that. Pushes to `main` and tags still build both architectures. A pull request also no
  longer writes buildx cache — an amd64-only layer overwriting `main`'s scope made the next
  publishing build slower, not faster.

- **Superseded pull request runs are cancelled.** Pushing three times in a row no longer
  leaves two runs burning for a result nobody will read. Runs on `main` and on tags are
  never cancelled; a publication hangs off those.

- **Reading a regulation is something you ask for.** `read-land-regulations.yml` ran on
  every push that touched it, fetching four PDFs of some 40 MB and quoting all six groups,
  on a branch where nobody was reading the log. It is `workflow_dispatch` only now.

### Removed

- **`dockerhub.yml`**, whose remaining job moved into `ci.yml`, and **`release.yml`**, a
  second and unused path to creating the same GitHub Release — `tag-release.yml` has done
  the tag, the release and the image since it was written. Two mechanisms for one outcome
  is how they drift apart.

  The five remaining workflows (`cleanup-dockerhub`, the two `probe-*`, the two
  `extract-imdg-*`) all wait to be asked and cost nothing until then. The number of files in
  `.github/workflows/` was never the cost; the number of jobs per push was.

## [1.38.0] — 2026-08-08

### Fixed

- **Blasting explosives with ammonium nitrate were refused, though footnote (d) permits
  them.** The message EMCargo showed even named the exception — and then blocked the
  load anyway. The check asked whether the consignment contained any class 1 package and
  any package of another class, and raised one error over the whole consignment. Table
  7.5.2.1 does not work that way: it sets label against label, and three of its cells hold
  a footnote letter instead of a prohibition.

  Footnotes (b), (c) and (d) are now applied, per pair of packages. One forbidden
  combination no longer condemns a permitted one, and one permitted combination no longer
  excuses the rest — load a blasting explosive with both ammonium nitrate and paint and you
  get the permission for the first and the prohibition for the second, each naming only the
  packages it concerns.

  Footnote (d) carries a condition that changes the rest of the load, so the panel and the
  document both state it: the aggregate must be treated as blasting explosives of class 1
  for placarding, segregation, stowage and the maximum permissible load of 7.5.5.2.1. UN
  0083 is excluded by the footnote itself and stays refused.

### Added

- **The regulation reader can print a page verbatim** (`--page 602`, or a range of at most
  twelve). ADR 7.5.2.1 came back "not found" for weeks: the finder scores each occurrence of
  a clause number by how much prose follows it, which is right for a rule made of sentences
  and wrong for one that is almost entirely a grid of crosses. It scored near zero and lost
  to every cross-reference in the volume. When the number will not resolve, the page still
  will.

- **The reader searches through a hyphen.** RID breaks words at the line end —
  `com-\npatibility`, `alka-\nline` — so a phrase search against it found nothing at all.
  "No occurrence" then reads as an answer about the regulation when it is only an answer
  about the typesetting, which for a tool whose job is checking what a text says is the
  worst way to be wrong.

### Fixed (the reader)

- **A table is no longer mistaken for a contents page.** One of the three contents signals
  counted bare clause numbers, and a table like 7.5.2.1 *is* a column of bare numbers —
  "1.4", "5.1", "6.2". So the finder skipped exactly the pages the locator could not reach
  either: both escape hatches failed on the same kind of page, which is how RID's 7.5.2.1
  came back as "no occurrence" for a footnote plainly printed on page 1101. A page carrying
  real sentences is now never a contents page, however many numbers stand in its margin.

### Verified

- **Rail was checked before these permissions were extended to it.** EMCargo answers RID
  and ADN mixed loading with ADR's table under a stated basis note. Borrowing another
  regime's prohibitions is conservative; borrowing its permissions is not, and this release
  turns three cells from refusals into permissions. RID 2025, table 7.5.2.1 on page 1101,
  carries footnotes (a) to (d) in the same words and with the same UN numbers — so for rail
  this is RID's own rule, not a road rule on loan. ADN is a different regime for stowage and
  its borrowing stays labelled as such.

### Documentation

- The footnote text and its source — ADR 2025 Volume II (ECE/TRANS/352 Vol. II), table
  7.5.2.1, printed page 592 — are recorded in the configuration and in `docs/dangerous-goods.md`,
  because these UN numbers come from a text that is not in the repository.

- Corrected in passing: the footnote (d) that extracts most readily from ADR belongs to
  **7.5.2.2** and concerns compatibility group L. The ammonium nitrate footnote is (d) to
  **7.5.2.1**. Two different tables, two different (d)s.

## [1.37.1] — 2026-08-08

### Fixed

- **A round bar was weighed as a square block, 27% too heavy.** There was no calculation
  path for `round_bar` at all, so a bar fell through to the generic branch and became a
  block of d × d. A 50 mm bar over 6 m came out at 117.75 kg instead of 92.48 — the ratio is
  exactly 4/π. `calc_round_bar` had been sitting unused in the engine the whole time, next to
  `calc_round_tube`; neither had a caller.

- **A round tube produced no weight at all.** v1.37.0 gave it the wall thickness field but no
  branch to use it, so it reported `wall_thickness_missing` however much you filled in. A
  pipe of 108 mm outside diameter with a 4 mm wall over 6 m is now 61.56 kg, against the
  10.26 kg/m in the steel tables.

### Changed

- **A round section is described by a diameter, a length and a wall — no height.** The width
  column *is* the diameter and the inner diameter follows from the wall thickness, so the
  height field shows a dash and is labelled accordingly. Asking for a measurement that adds
  nothing is only an opportunity to enter something wrong.

- **A wall thicker than the radius is refused** rather than producing a negative
  cross-section, because a negative weight looks exactly as confident as a positive one.

## [1.37.0] — 2026-08-08

### Fixed

- **A steel angle profile was weighed as a solid bar, five times too heavy.** Ten angle
  profiles of 6 m, 80 × 80, came back at 301.44 kg each. An L 80×80×8 is 9.63 kg per metre,
  so about 57 kg for six metres. The cross-section *was* recognised — the detector returns
  `angle_profile` — but the calculation path for it demanded four measurements out of the
  *description*. Enter three in the columns and the line fell through to the generic branch
  and became a solid block of 600 × 8 × 8 cm.

  Reported from use, and the worst kind of defect this application can have: a confident
  wrong number on a transport document, with nothing on screen suggesting a measurement was
  missing.

### Added

- **Wall thickness, the fourth measurement.** For an angle profile, a square tube or a round
  tube the line carries a wall thickness in millimetres, and the engine's existing
  cross-section formulas finally receive it. L 80×80×8 over 6 m is now 57.27 kg against the
  9.63 kg/m in the steel tables.

  **The field only appears where it means something.** A plate, a beam, a plank or a block is
  fully described by three measurements, so no fourth field is shown — as you pointed out
  about wooden planks.

  **And it is required where it applies.** A shape with a wall and no thickness produces no
  weight at all: the line reports `wall_thickness_missing` and asks. Falling through to a
  solid block is exactly what caused this, and no number is better than that number. The
  transport volume is still given, because that depends only on the outer measurements.

### Changed

- **The recalculate button is gone; the calculation follows the input.** A button you have to
  press to see a correct figure is a button that gets forgotten, leaving a stale weight on
  screen. Changing a quantity, unit, form or dimension now recalculates shortly after typing
  stops. Manual weight corrections deliberately do not trigger it — those are an answer to a
  calculation, and would otherwise restart it.

## [1.36.1] — 2026-08-08

### Fixed

- **Releasing no longer moves `main` out from under the next branch.** The version lives in
  five places, and `frontend/package-lock.json` — which holds it twice — was not being
  checked. So it drifted at every release, and the **Tag release** workflow repaired it by
  committing to `main` after the merge. The repair worked. It also meant every branch created
  before that commit conflicted on `VERSION` and `CHANGELOG.md` and could not be merged until
  it was rebased; that happened twice in one day, over four lines of JSON.

  The check now covers all five values and runs on every pull request, so the mistake fails
  where it is made. The release workflow verifies and stops rather than repairing, and writes
  nothing to `main`.

### Added

- **`scripts/bump_version.py`** sets all five at once, because nobody edits a lock file by
  hand and forgetting it was the whole problem. It leaves the rest of the lock file
  byte-identical, so a version bump stays readable in a diff.

### Removed

- `scripts/finalize_release_metadata.py`. Half of it was dead — the changelog archive it
  merged was consumed long ago and cannot recur — and the other half is now a check instead
  of a write.

## [1.36.0] — 2026-08-08

### Changed

- **The form a good travels in is now a choice on the line, not an average in the code.**
  v1.35.0 weighed all timber at a stacking factor of 0.65. That is a reasonable figure for
  neatly stacked sawn timber and a poor one for everything else: loose-tipped firewood is
  nearer 0.45 and a tight package nearer 0.75. One average describes nobody's load.

  Each line now carries a **form** — solid, sheets, bundled, stacked or loose bulk — and the
  form carries the factor. So 20 m³ of oak is 14,400 kg solid, 10,800 bundled, 9,360 stacked
  or 6,480 loose, and the shipper says which. The same choice applies wherever it matters:
  steel plate against steel scrap, plastic granulate against regrind, baled paper against
  loose.

  The default still fits the goods — sawn timber starts stacked, sheet material flat, metal
  solid — so nothing needs choosing to get a sensible answer.

- **The form does not apply where the density already describes the shipped state.** For
  gravel, grain and ore the stored figure *is* a bulk density; laying a loose factor over it
  would subtract the air twice. Same for liquids and for the per-pallet averages. Those
  lines show a dash instead of a dropdown, and the API returns an empty list of forms for
  them.

- **The result says what it used.** The compliance of a number matters as much as the
  number: a line reports the form it was weighed in and the density that produced it, so
  9,360 kg can be traced to 468 kg/m³ rather than 720.

## [1.35.0] — 2026-08-08

### Added

- **Timber is weighed as it travels: stacked, not solid.** Oak's 720 kg/m³ is the density
  of the wood, and between the boards of a stack there is air. Entering 20 m³ of oak
  returned 14,400 kg — the weight of 20 m³ of solid oak, which almost nobody carries. A
  volume entered for timber now uses a **stacking factor of 0.65**, so the same 20 m³ is
  9,360 kg at 468 kg/m³. Sheet material — plywood, OSB, MDF, HDF, chipboard, hardboard,
  softboard, cork, CLT and glulam — stacks flat and keeps its own density.

  Two things this deliberately does not do. It does not touch a line with explicit
  dimensions: a beam of 0.2 × 0.2 × 3 m is 0.12 m³ of actual wood and is weighed solid.
  And it does not present the factor as a measurement — it is a nominal packing figure,
  stated as such, and entering the weight by hand overrides it.

- **Length, width and height are fields on the line.** A description no longer has to read
  `balk 200x200x3000` for its measurements to count. Anything recognised in the text still
  appears as a placeholder; what you type wins. On a phone the three sit behind "view more",
  with quantity and unit on the collapsed card.

### Fixed

- **Dimensions typed into the table were ignored by the calculation.** They were carried
  into the displayed length, width and height, but every calculation path went on reading
  what had been parsed out of the *description*. So the columns looked editable and changed
  nothing. They now feed the calculation, and a length on its own is enough for a catalogue
  profile. Two of the three measurements is still not a block: nothing is computed rather
  than a third being invented.

### Changed

- `docs/data-sources.md` records the stacking factor and why it lives in `units.py` rather
  than in the goods database: `seed_catalogs` only fills that database when it is empty, so
  new seed values never reach an existing installation, and a calculation that is only right
  for new users is worse than none.

## [1.34.1] — 2026-08-08

### Fixed

- **"1500 litres of petrol" is enough to compute with, and was rejected anyway.** The line
  reported `dimensions_missing` and left weight and volume empty, while everything needed
  to work it out was on the screen: the unit gives the volume, the density of petrol
  (745 kg/m³) gives the mass. 1500 L is now 1,117.5 kg and 1.5 m³.

  The cause is the kind worth recording. v1.34.0 delivered a units module, a dropdown that
  used it and an API to compute with it — but the pipeline that determines the weight never
  asked for any of it and went on demanding dimensions. Half connected is not connected.

  The conversion only steps in when there are no dimensions and no profile, and only for a
  **recognised** goods item: `match_material` falls back on the density of steel, and 1500
  litres times 7850 would look every bit as confident as the answer that is right. So an
  unknown substance stays reported as unknown, and fifteen pallets without a weight per
  pallet stay unknown — a count carries no physics in it.

## [1.34.0] — 2026-08-08

The goods step becomes a table on desktop and cards on a phone, and a quantity finally
carries a unit.

### Added

- **A unit instead of a word.** The unit of a goods line was a free text field with
  "stuks" as its default, so entering 1,200 litres of diesel gave you 1,200 *pieces* of
  diesel and left the weight to you. It is now a dropdown, and every unit knows what it
  measures — mass, volume, length or a count. Density bridges mass and volume, so 1,200 L
  of diesel is 1,002 kg, and 20 tonnes of gravel is 12.5 m³.

- **The list suggests, it does not fence you in.** The category of the recognised goods
  decides what appears first: litres and m³ for liquids, tonnes and m³ for bulk, pieces and
  pallets for general cargo, m³ for timber. Every other unit stays one click away, because
  400 goods in 16 categories always hold exceptions and being stuck on one is worse than an
  unusual unit. What people actually type — `liter`, `cbm`, `kubieke meter`, `MT`, `Stück`,
  `big bag` — still resolves, so shipments saved under the old free-text field keep working.

- **Where it cannot calculate, it says so.** Forty pallets without a weight per pallet weigh
  an unknown number of kilos. The conversion reports that rather than returning zero: a
  total that looks right and means nothing is the same failure as a check that never ran
  looking like a check that passed.

- **`ResponsiveRecords`** — one set of data in two shapes. A real table on desktop, where
  rows can be compared; the card pattern on a phone, where they cannot. Built from
  *Designing User-Friendly Data Tables for Mobile Devices* (Zahra Mohammadi, Bootcamp,
  July 2025): each row becomes a card with the identifying field in a tinted header and the
  actions as icons beside it, the body a list of label–value pairs, and only the priority
  fields shown until "view more" opens the rest. The unit sits small behind its value —
  `1 200 L` — instead of claiming a column of its own.

### Changed

- **The goods step uses it.** On a phone each line is a card headed by its description, with
  quantity and unit as the one visible field and weight, volume, the dangerous goods flag
  and the status behind "view more". On desktop the same lines are a table with a column per
  field. Nothing is dropped on the small screen; it is only folded away.

### Fixed

- **`docs/data-sources.md` claimed something the data does not say.** It stated that each
  goods entry records whether its density is bulk, solid, liquid or an effective pallet
  figure. There is no such field — only the category. The distinction is real (20 m³ of
  gravel, of steel and of stacked timber are three different masses), so the basis is now
  derived from the category and reported as derived, and the page says so.

## [1.33.0] — 2026-08-07

The land regulations are read instead of recalled, and reading them found two things the
application had wrong.

Every rule about road, rail and inland waterway in EMCargo came from an ADR Table A data
export plus general knowledge of how the three regimes are structured. The documentation
said the regulatory texts were out of reach and marked every such rule as unverified. That
premise was false: **ADR and ADN are published free of charge by UNECE and RID by OTIF.**
Only the IMDG Code and the IATA DGR are sold. What was missing was a network route from the
development container, not the documents.

### Added

- **`scripts/read_land_regulations.py` and a workflow to run it.** It fetches ADR 2025
  (both volumes), RID 2025 and ADN 2025 from their publishers on a CI runner and prints the
  provisions the application implements, addressed by the number they carry in the text. It
  commits nothing — the quoted text stays in the run log, and only the values read out of it
  are stored, each with its provision.

- **ADN gets its own exemption rule, because it has one.** ADN 1.1.3.6.1 has no points
  calculation at all: it exempts a consignment in packages when the gross mass of everything
  together stays under 3,000 kg *and* no class exceeds its own figure — 0, 300 or 3,000 kg
  depending on packing group, class 2 group, or whether a model No. 1 label is required.
  Carriage in tanks is never exempt. Until now an inland waterway shipment was shown the ADR
  points table, which is not an approximation of that answer but an answer to a different
  question, and the two can point opposite ways: 1,200 litres of a packing group III liquid
  loses the ADR exemption at 1,200 points and keeps the ADN one. The panel now carries an
  ADN card with its own status, the per-class figures and the conditions of 1.1.3.6.2 that
  survive the exemption.

### Fixed

- **Nine substances were counted at more than twice their proper weight.** Note (a) to the
  table in ADR/RID 1.1.3.6.3 allows UN 0081, 0082, 0084, 0241, 0331, 0332, 0482, 1005 and
  1017 up to 50 kg rather than the 20 kg of transport category 1, and RID 1.1.3.6.4 gives
  the matching multiplier: times 20, not times 50. EMCargo applied times 50 to all of
  category 1, so 50 kg of chlorine or anhydrous ammonia scored 2,500 points and lost an
  exemption the text grants at exactly 1,000 — the application demanded orange plates, a
  driver certificate, written instructions and an ADR vehicle for loads entitled to go
  without them.

- **The IATA Q status reaches the document, not just the screen.** Whether the Q check of
  5.0.2.11 actually ran was derived in the API route, so the compliance panel said "no Q
  check was performed" and the export said nothing — at the one moment the document leaves.
  `exporter.py` states in its own comment that the screen must never be the only place this
  is enforced. The status is now part of the compliance outcome, so every caller sees it.

- **A position that was never checked no longer counts as checked.** A position holding two
  or more substances with no `n` and no `M` was skipped silently, so as soon as one other
  position was filled in the whole shipment reported "checked". It is now reported as not
  checked, and one unchecked position makes the shipment unchecked.

### Changed

- **Rail stops hedging about its own chapter.** RID 1.1.3.6.3 prescribes the same five
  transport categories with the same maxima (0, 20, 333, 1000, unlimited) and 1.1.3.6.4 the
  same multipliers (50, 3, 1) against the same calculated value of 1,000. The arithmetic was
  right all along. The old note said RID "has its own 1.1.3.6 which EMCargo does not
  hold" — true, but it invited the user to distrust a number that is the number RID
  prescribes. The panel now cites 1.1.3.6.3/1.1.3.6.4 and names the one real difference:
  RID counts per wagon or large container, ADR per transport unit.

- **The 3.4/3.5 limits are confirmed against the published text.** ADR 3.4.2's 30 kg,
  3.4.3's 20 kg for shrink- and stretch-wrapped trays, 3.5.5's 1,000 packages and the whole
  of table 3.5.1.2 (E1 30/1000, E2 30/500, E3 30/300, E4 1/500, E5 1/300) are as shipped in
  v1.31.0. That release claimed they had been verified without leaving a record of it; there
  is now a record, and the values were correct.

- **`docs/dg-coverage.md`** separates what has been read from what has not. Road, rail and
  inland waterway carry provision numbers; sea and air keep their `[verify]` markers,
  because the IMDG Code and the DGR genuinely cannot be read here. The gap ranking loses
  two entries and gains an ordered list of what to build next, starting with RID and ADN
  mixed loading — which no longer needs anything EMCargo cannot get.

- The pinned example image and Docker Hub cleanup tags in the installation and privacy
  guides, and the sample health response, moved off v1.29.3.

## [1.32.0] — 2026-08-05

Nine dangerous-goods specialist findings from the v1.31.0 review are closed: air
prohibition, Q noise, multi-PG silence, class 1 mass, the 8-tonne LQ mark, the class 8
pair exception, forbidden substances in the points table, modality-filtered hints, and
the inner-packaging field when LQ/EQ have no route.

### Added

- **Division 2.3 (toxic gases) is refused for air transport.** Enrichment reads the
  division from the labels column when Table A only states class "2", so chlorine
  (UN 1017) and similar gases raise an ICAO TI / IATA DGR error on the air stack instead
  of staying silent.
- **Net explosive mass for class 1.** A dedicated field feeds ADR 1.1.3.6.3 points and the
  NEM figure on land transport documents (5.4.1.2.1). Without it the points table reports
  incomplete rather than counting product mass as explosive mass.
- **ADR 3.4.13/3.4.14 when LQ packages exceed 8 tonnes gross** on a transport unit: the
  large LQ mark of 3.4.15 is required and the 3.4.14 waiver no longer applies.
- **IMDG 7.2.6.5 next to the acid×alkali pair** that triggered a segregation finding, as
  an info note that leaves the warning in place.

### Fixed

- **The IATA Q check no longer starts on auto-filled n alone.** Participation requires an
  entered M (maximum per packing instruction), so every air shipment is not marked
  incomplete when all-packed-in-one does not apply.
- **Multi-row UN numbers respect the user's packing group** and warn when several groups
  exist without a choice, instead of silently taking the first Table A row.
- **Carriage-prohibited substances are excluded** from the 1.1.3.6 points table and from
  document lines; the panel names them separately.
- **Modality hints follow the active profiles:** EmS/IMDG noise stays off a pure road
  prepare, and the air prohibition hint appears only when IATA is selected.
- **The net-per-inner field is hidden when LQ is 0 and EQ is E0**, so the step is not
  permanently "incomplete" for substances with no limited/excepted route.

### Changed

- The dangerous-goods coverage assessment records the specialist fixes as shipped in
  v1.32.0.

## [1.31.0] — 2026-08-05

The limited and excepted quantity limits are applied instead of only explained, and the
dangerous goods step becomes readable again.

### Added

- **The LQ and EQ limits of chapters 3.4 and 3.5 are checked against the entered
  quantities.** A new "net per inner packaging" field feeds a per-line assessment for the
  ADR, RID, ADN and IMDG profiles: the column 7a limit and the E-code limits of table
  3.5.1.2, the 30 kg gross limit of 3.4.2 (naming the 20 kg tray limit of 3.4.3) and the
  1,000-package cap of 3.5.5. The limit values were verified against the published
  3.4/3.5 text before the check was written. Qualifying is reported, never granted: the
  LQ/EQ mark and the packaging and testing requirements remain conditions, and a
  qualifying line is never removed from the 1.1.3.6 points calculation. Mass is never
  compared against a volume limit, and a number without a unit is asked about rather
  than guessed at. On IMDG the values come from the 42-24 Dangerous Goods List, with
  differences from the ADR value flagged; on RID and ADN the same basis note appears as
  for the points table; for air no claim is made.

### Fixed

- **Live compliance checks from the wizard work again.** The wizard sends its line
  identifier as a number; the schemas introduced in v1.30.0 rejected that with HTTP 422,
  so every live check from the wizard failed before anything was computed and the panel
  showed a validation error instead of an outcome.

### Changed

- **The dangerous goods step folds its findings into collapsible summary cards.** The
  headers carry the outcome — status chips, severity counts, totals — and the
  substantiation unfolds on demand. Nothing is silenced by the fold: a carriage
  prohibition stays outside the cards, a section holding an error opens by itself, and
  every collapsed header shows the counts of what is inside.

## [1.30.1] — 2026-08-05

A release-metadata and documentation cleanup following v1.30.0.

### Fixed

- Synchronise the frontend lockfile version with the canonical application version before a release tag is created.
- Restore the changelog to one continuous file; the temporary archive through v1.29.5 is merged back before tagging.
- Update the dangerous-goods coverage assessment: a missing IATA Q calculation is no longer silent since v1.30.0, although n and M still require manual input because EMCargo does not contain IATA quantity tables.

### Changed

- Release preparation now normalises derived metadata before tagging, preventing the application version and npm lockfile from drifting apart again.
- LQ/EQ application is documented as the next data-supported dangerous-goods priority.

## [1.30.0] — 2026-08-05

The compliance boundary, authentication boundary and build boundary are now explicit instead of relying on the browser or deployment convention to do the right thing.

### Fixed

- **The IATA compliance contract now uses one canonical profile name.** `IATA_DGR` is accepted end to end by the wizard, API and calculation engine. The previous `IATA` value remains a temporary compatibility alias, while unknown profiles still fail with HTTP 422.
- **An absent IATA Q calculation no longer looks like approval.** Compliance results say whether Q was checked, incomplete, exceeded or not checked, and the panel warns when all-packed-in-one may apply but n/M data is absent.
- **Changing a password now ends every existing session for that user.** Tokens carry a one-way fingerprint of the current password hash; after a password change old cookies no longer authenticate and the current cookie is cleared.
- **Interrupted export cleanup covers the formats EMCargo actually creates.** PDF, ZIP, XLSX and temporary files are removed case-insensitively at startup; one undeletable file no longer stops the rest, and unrelated files and directories are untouched.

### Added

- **Strict authentication and administrator safety rules.** Login cookies automatically use `Secure` for HTTPS or trusted `X-Forwarded-Proto=https`, with `COOKIE_SECURE` as an explicit override. Roles are limited to `admin` and `user`; an administrator cannot remove their own administrator access or remove the last active administrator.
- **Bounded spreadsheet and remap imports.** Raw uploads are limited to 10 MB, imports to 20,000 rows, 100 columns and 10,000 characters per cell, and XLSX archives to 50 MB after decompression. The limits apply to wizard and equipment imports and nested remap JSON.
- **Executable API contract coverage for dangerous goods.** FastAPI integration tests cover air and multimodal wizard profiles, the legacy IATA alias, unknown profiles and Q-status behaviour.

### Changed

- **Production dependencies are now audited and reproducible.** Docker uses Node 22 and `npm ci`; Python runtime packages are separated from pytest-only dependencies; `pip check`, version consistency and a blocking `npm audit --omit=dev --audit-level=high` run in CI.
- **The frontend moved to React 19.2.8 and React Router 8.3.0.** This removes the vulnerable Router 7 dependency chain while retaining the existing wizard behaviour and frontend test suite.
- **Pull-request Docker builds prove both AMD64 and ARM64 images without publishing them.** Release and main builds retain the publishing path.

### Tests

- The combined release was validated with backend tests, frontend tests, TypeScript and Vite build, production dependency audit, Python dependency validation, version consistency and a multi-architecture Docker build.

## [1.29.5] — 2026-08-04

Road, rail and inland waterway were being treated as one regime. They are three.

### Fixed

- **The tunnel restriction code no longer appears on rail and inland waterway
  documents.** It comes from column 15 of ADR Table A and belongs on the road document
  under 5.4.1.1.1 (k). RID Table A has no such column and the ADN transport document does
  not carry one — yet EMCargo printed `(D/E)` on a CIM consignment note and on an ADN
  document. That is not a missing check but wrong information the application added by
  itself. The code is now written only when the ADR profile is selected. The CMR is
  unaffected.

### Changed

- **A calculation now says which tables it was made with.** The 1.1.3.6 points and the
  mixed loading of 7.5.2 are computed from the ADR tables. RID and ADN have their own
  versions of those chapters and they are not in EMCargo. Selecting RID or ADN gave an
  outcome that silently read as *the RID outcome*. The compliance panel now carries a
  note naming the basis, in all three interface languages. The numbers themselves are
  unchanged — a road shipment sees no note, and 1200 points stay 1200 points.

### Added

- **`docs/dg-coverage.md`** — an assessment, per mode, of what EMCargo actually checks
  against what the regime requires, with the gaps ranked by how much damage the gap can
  do. It separates what was read out of the code from what comes from knowledge of the
  regimes, and marks the latter as unverified: the regulatory texts are not in this
  repository and could not be consulted while writing it. Nothing in it is a citation, and
  nothing in it should become a check before it has been verified against the published
  text.

## [1.29.4] — 2026-08-04

Documentation only. Nothing in the application changed.

### Changed

- **The docs caught up with the last few releases.** The interface badge and the goods
  database still said Dutch and English; the paste box was described as reading Dutch or
  English; the Unraid instructions still told you to fill in `APP_SECRET_KEY`, which is
  now generated; the pinned example image and the Docker Hub cleanup tags still pointed at
  v1.13.2; and the `/api/health` sample predated the `regulatory` block.

- **Getting started now answers the question that actually came in.** "The container
  starts and immediately stops, and the log window closes before I can read it" is a
  troubleshooting entry, naming the affected versions (v1.25.0 – v1.29.2), the fix, and
  what to set if you cannot update yet.

- **The v1.25.0 changelog entry is marked as reverted** rather than left standing as
  advice, and its dead link into `configuration.md` is repaired. The original wording is
  kept, quoted, because a changelog is a record and not a place to quietly rewrite what
  was said at the time.

- **The user guide describes the language choice**, including the one thing that does not
  follow it: the proper shipping name is prescribed per mode, so a sea or air document
  stays English whatever the screen says.

### Fixed

- **A claim in the development notes was wrong, and testing it is what showed that.**
  Both `docs/development.md` and `AGENTS.md` were about to say that `APP_ENV=development`
  preserves `APP_SECRET_KEY=dev-secret`. It does not: a published key is replaced in every
  environment, and `APP_ENV` only silences the CORS and admin-password warnings. The
  generated key is stored and reused, so a developer is logged out once rather than at
  every start. Both files now say that.

- `ROADMAP.md` still listed German as a third interface language and the import column
  mapping as planned; both shipped in v1.29.0 and v1.28.0.

## [1.29.3] — 2026-08-04

**If you are on v1.25.0 or later and the container will not start, this is the release
that fixes it.** No configuration change is needed on your side.

### Fixed

- **EMCargo refused to start on its own default settings.** Since v1.25.0 the
  application stopped at startup when `APP_SECRET_KEY` was published, empty or shorter
  than 32 characters, or when `CORS_ALLOWED_ORIGINS` was `*`. Those are the values it
  ships with — `app_secret_key: str = "change-me"` and `cors_allowed_origins: str = "*"`
  in `config.py` — and the Unraid template passes `APP_SECRET_KEY` through with an empty
  value. So every installation that had not set both by hand died on startup, in a
  container that exited too quickly to read the message explaining why.

  The reasoning behind the refusal was right: the default signing key is published in
  this repository, and anyone who has it can write themselves a valid admin token, so a
  line in a log nobody reads is not an answer. The conclusion was wrong. A self-hosted
  application with its own data directory does not need to ask the user for a signing
  key — it can make one.

  It does now. On first start EMCargo generates a key, stores it as `secret_key` in
  `DATA_DIR` with owner-only permissions, and uses it from then on. It survives restarts
  and container recreation because it lives on the mounted volume. A key you set yourself
  still wins, as long as it is not a published value and is long enough. The result is
  strictly safer than what shipped before — random instead of published — and costs the
  user nothing.

  `CORS_ALLOWED_ORIGINS=*` and a documented `ADMIN_PASSWORD` are now reported in the log
  rather than fatal. Neither is worth a dead application, and the CORS case is largely
  theoretical anyway: browsers refuse to combine a wildcard origin with cookies, so the
  cross-site call it warns about does not work regardless.

### Tests

- `test_starts_out_of_the_box.py` builds the application in a real subprocess with a
  clean environment, no `.env`, and nothing configured that a user would not also have —
  including the exact shape the Unraid template produces. It fails on eight of its nine
  cases against v1.29.2 and passes on all nine here.

  This is the test that was missing. The 500 tests that existed all ran with
  `APP_ENV=test`, which is precisely the setting that skips the check, and not one of them
  built the app the way a user starts it. A suite can be large and still miss the only
  thing that matters.

### Changed

- The Unraid template no longer marks `APP_SECRET_KEY` as required, and says the key is
  generated if left blank. `.env.example` and `docs/configuration.md` say the same, and
  the documentation records what the old behaviour was and why it was wrong.

## [1.29.2] — 2026-08-04

Following the rules and being pleasant to use are the same job, not a trade-off.

### Changed

- **A sea or air document now gets the English shipping name instead of refusing to
  export.** 1.29.1 got the regulation right and the experience wrong. If you drafted a
  German road document and then added a sea leg, the German name stayed in the field and
  the export **blocked**, telling you to retype `GASOLINE` — a word EMCargo had just
  printed in the error message. That is making the user do what the application already
  knows.

  The language of the proper shipping name belongs to the **document**, not to the
  shipment. One shipment produces a CMR reading `BENZIN ODER OTTOKRAFTSTOFF` and an IMO
  Multimodal Dangerous Goods Form reading `GASOLINE`, from the same data. So the name is
  now resolved per document at the moment it goes on paper — in the goods column, in the
  5.4.1.1.1 description line, in the DG table and in the filled IATA PDF — and the export
  says what it did rather than what you still have to do.

  Only what EMCargo derived itself is adjusted. Wording you typed — a technical name
  on an N.O.S. entry, your own addition — is left exactly as it stands: we cannot judge
  it and must not silently overwrite it.

- **Why a multimodal shipment stays English throughout, including on the CMR**, where
  German would have been allowed: one shipment then carries the same goods description on
  every piece of paper. A forwarder and a customs officer want those to match, and two
  languages for one substance across two documents of the same consignment is a question
  you do not want to be asked. The reasoning is written down in
  `app/services/dg/naming.py` so it reads as a decision rather than an accident.

### Tests

- The export is checked by reading the generated workbook back: the IMO form contains
  `GASOLINE` and does **not** contain `BENZIN ODER OTTOKRAFTSTOFF`, and the CMR from the
  same shipment contains the German name. A warning that says the right thing while the
  document says the wrong thing would otherwise pass unnoticed.

## [1.29.1] — 2026-08-04

The two gaps left open by 1.29.0, closed. One of them was not the gap it was described as.

### Fixed

- **The proper shipping name was always English, even where German was prescribed.**
  1.29.0 claimed the ADR source table "carries Dutch and English but no German". That was
  wrong twice over: the table carries `name_en` **and** `name_de` for all 2,928 entries,
  and it carries no Dutch at all. The German name was sitting in the data the whole time
  and every code path reached past it with `entry.get("name_en") or entry.get("name_de")`.
  A German consignor got `GASOLINE` on a CMR while `BENZIN ODER OTTOKRAFTSTOFF` stood
  right next to it in Table A.

  Fixing it is not "translate along with the screen", because the modes differ. ADR
  5.4.1.4.1 — and along the same line RID and ADN — wants the transport document in an
  official language of the forwarding country, so a German name belongs on a German CMR
  or CIM. IMDG 5.4.1.4.1 wants English, French or Spanish. IATA DGR 8.1.2.1 wants English.
  `BENZIN` on a Shipper's Declaration is not a matter of taste; it is a refused shipment.

  So `app/services/dg/naming.py` gives the German name only when the reader is German and
  no sea or air profile is in play — for a multimodal shipment English satisfies all three
  regimes and German only one. The UN lookup and the type-ahead now carry the same
  language and profiles, so the suggestion the user clicks is the text the document will
  actually carry.

  And for the sequence that would otherwise slip through — draft a German road document
  first, add a sea leg afterwards, keep the German name that is already in the field — the
  export refuses it and names the English wording that belongs there instead.

- **The catalogue search always answered in Dutch.** `search_catalog` took no language
  parameter at all, so an English user got Dutch material names too; German only made an
  existing problem visible. It now takes one, and the route and the frontend pass it.
  Searching still spans every language — type `Stahl` while reading Dutch and you still
  find staal — only the answer follows the interface.

  All 400 goods and the reference items gained German labels, as did the product-type and
  fallback-material tables and the dimension hint under a suggestion. This is not
  decoration: the suggestion a user clicks becomes the description in the goods column of
  a waybill.

### Fixed (CI)

- **The frontend CI job had never once run.** `ci.yml` pinned Node 20 while `jsdom` 30
  declares `^22.22.2 || ^24.15.0 || >=26` and `undici` 8 declares `>=22.19.0`, so
  `npm test` died with `webidl.util.markAsUncloneable is not a function` before a single
  test was collected. The job has been red on `main` since it was introduced in 1.24.2 —
  the backend half was green, which is presumably why it went unnoticed. Both workflows
  now use Node 22, matching what the toolchain asks for.

### Tests

- `test_shipping_name_language.py` pins the ADR/IMDG/IATA split, the fallback for entries
  with no German name, and the road-then-sea sequence. It also holds the lookup and the
  export to the same answer — a suggestion that differs from what gets exported is worse
  than no suggestion.
- `test_catalog_search_language.py` covers the three languages, cross-language searching,
  a German name that exists only as a label, and the guarantee that a label is never
  empty — an empty label means an empty goods column.
- `seed/materials.json` and `seed/reference_items.json` joined the completeness check, so
  a new material has to arrive in all three languages.

## [1.29.0] — 2026-08-03

German as a third interface language, and one place that decides which language anything is in.

### Added

- **Deutsch.** The interface, the field labels, the dangerous goods help texts, the
  compliance warnings and the generated documents are now available in German alongside
  Dutch and English — 592 texts across the document registry, the compliance rules, the
  DG instructions and the seed data, plus the 350 interface strings.

  German transport terminology follows the official wording where the regulations have
  one: *Beförderungskategorie* for the ADR 1.1.3.6 transport category, *Verpackungs-
  anweisung* for the packing instruction, *schriftliche Weisungen* for the instructions
  in writing, and the IMDG distinction between *entfernt von* (away from) and *getrennt
  von* (separated from) — a difference that is the whole point of a segregation warning.

  The disclaimer says in its German text that it is a translation and that the Dutch
  version prevails; the governing law was and stays Dutch.

- **German input is understood too.** A language on the screen does not help if the paste
  box does not recognise what you type into it: an unrecognised product yields no weight
  and therefore no usable document. `Stahl Winkelprofil`, `Quadratrohr`, `Rundstab`,
  `Stahlblech`, `Träger`, `Betonplatte`, `Sperrholz`, `Kunststoffplatte` and their
  neighbours are now detected, the language detector answers in the language you wrote in
  rather than falling back to English, and `Stück`/`Stk` count as units.

  `PVC-Rohr` deliberately does not go through a bare `Rohr` pattern — a plastic pipe
  weighs an order of magnitude less than a steel one, and that is a wrong weight on a
  waybill rather than a cosmetic slip.

### Changed

- **One place decides the language, instead of eleven.** Every module that produced text
  carried its own copy of `"en" if language.startswith("en") else "nl"`. With two
  languages that was correct. With a third it would have silently answered "Dutch" for
  German — a German screen with Dutch warnings and a Dutch export — and `TEXTS[key][lang]`
  would have raised a `KeyError` outright.

  `app/core/languages.py` now holds the supported languages and the fallback order, and
  `normalise()`/`pick()` replaced every two-way branch. `pick()` falls back to the next
  language that does have the text rather than returning nothing: a field label in the
  wrong language can still be read, a field without a label cannot. The frontend has the
  same single point in `src/i18n/language.ts`, so the screen and the backend can no
  longer disagree about which language a document is in.

### Tests

- The completeness of a language is enforced, not eyeballed. `test_languages.py` walks
  the data files and asserts every block with a Dutch and an English text also carries a
  German one, that a list stays a list of the same length, and that a "translation" is
  not simply the Dutch text repeated. An AST pass over `app/` catches the same omission
  in code, and a source check fails on any two-way language branch coming back.
  On the frontend, `translations.test.ts` holds the three bundles to identical keys and
  identical interpolation variables.

### Known gaps

Both were closed in 1.29.1; the second one turned out not to be a gap in the data at all.

- The catalogue search (`search_catalog`) returns material names in Dutch regardless of
  the interface language. It takes no language parameter at all, so this affects English
  users today as much as German ones; the German labels are in the data, waiting. Making
  the search language-aware is its own change, touching the route and the frontend call.

- The proper shipping names come from the ADR source table, which carries Dutch and
  English but no German. A German user sees the German interface around an English or
  Dutch shipping name — which is what belongs on the document anyway, since the proper
  shipping name is prescribed and not translated freely.

## [1.28.1] — 2026-08-03

### Fixed

- **A field that promises a format now has to keep it.** The export only ever checked
  whether a required field was empty. The NHM commodity code on the CIM is labelled
  "box 24, 6 digits", but `72` or `7208 51` passed straight through onto an official rail
  consignment note. That is not cosmetic there: the carrier prices the shipment on that
  code and customs reads it.

  The check is generic — a `pattern` in the document registry — so the next field with a
  fixed shape gets it without new code. An empty required field is still reported as
  missing rather than as misformatted; sending someone twice to the same line for two
  different reasons helps nobody.

### Added

- **`scripts/probe_nhm_sources.py`** and a workflow to run it. Box 24 wants a six-digit
  NHM code and EMCargo cannot supply a list, so the field says look it up elsewhere.
  Inventing six-digit codes is not an option here, so this measures first: is a candidate
  source reachable, does it carry six-digit codes *with* descriptions — a list of bare
  numbers is useless to someone choosing one — and does it cover the goods EMCargo
  knows. The same order that worked for the Dangerous Goods List.

  It records nothing. Until a source turns up that holds up, box 24 stays a free-text
  field with a format check.

## [1.28.0] — 2026-08-03

The spreadsheet import used to guess in silence.

### Fixed

- **An unrecognised header meant columns 0, 1 and 2, with no way to tell.** A file laid
  out as `Ref | Benaming | Aant. | Eenh.` — none of those names are in the alias list —
  came out with the reference numbers as descriptions, the descriptions as quantities,
  and the header row imported as a cargo line. What a user saw of that was `status=error`
  and 0 kg, with nothing pointing at the column layout.

  The import still guesses, because the alternative is making every import manual. What
  changed is that it says so, and hands over enough to put it right.

### Added

- **A column mapping panel.** Every column comes back with its header and its first few
  values, so the dropdown reads `2. Benaming · Stalen hoekprofiel 80x80x8x6000` instead
  of "column 2" — with an unrecognised header there is no name to show, so the values
  have to do the work. A field can be left unmapped, and the first row can be marked as
  a header, which is what stops it being imported as cargo.
- The panel is amber when the layout was guessed and plain when the header was
  recognised, so it is obvious which of the two you are looking at.
- `POST /api/import/wizard-remap` applies a different mapping to the same rows. It is
  separate from the upload because **nothing about the file is kept on the server**: the
  rows travel with the request and come back as text. That costs some bandwidth and
  buys never leaving half a shipment sitting on the server.

## [1.27.1] — 2026-08-03

The Dangerous Goods List extractor checked itself against the UN cards, which are also
an IMDG source. That is one IMDG reading held up against another, and it measures
nothing.

### Changed

- **The class cross-check now reads ADR Table A** (`un_numbers.json`) instead of
  `card_data.json`. Agreement goes from 2322/2336 to **2328/2329**, and the fourteen
  differences drop to one:

  - Eleven were the cards, not the list: UN 2984–2992, 3548 and 3550 carried sequence
    numbers in their class field.
  - Six more appear and then resolve — UN 2186, 2421, 2455, 3537, 3538 and 3539. ADR has
    no division to give for these: the label column reads `BEFÖRDERUNG VERBOTEN` for the
    ones forbidden on the road, or `siehe 5.2.2.1.12` for articles carrying the labels of
    each hazard present. They travel by sea and the IMDG Code names their division
    normally. Comparing where one source has no answer is not a check, so those entries
    are left out rather than counted as disagreeing.
  - What remains is **UN 3423**, the genuine 42-24 reclassification from 8 to 6.1 (8) —
    which the list confirms itself with its change marker.

- A UN number can appear in Table A more than once (UN 1950, aerosols, is both 2.1 and
  2.2), so divisions are collected as a set. And where the IMDG Code says class 2 while
  ADR gives 2.1, that is not a contradiction but a difference in how finely the two
  regimes divide; a class that heads an ADR division counts as agreement.

### Removed

- **The `class` field from `card_data.json`** and from `extract_un_card_data.py`. Nothing
  in the application ever read it — only that cross-check. It was also wrong: the card
  parser picked up the wrong line for those eleven substances, and where two card
  variants disagreed `merge()` kept both, producing `["10", "9"]`. Repairing a field
  nobody reads is wasted effort.

### Notes

- The division rule now exists twice: in `parse_hazards()` and in the extractor, which
  runs in GitHub Actions with only pymupdf and cannot import the application. A test ties
  them together over all 2928 Table A entries, and it earned its keep immediately — it
  caught that the copy skipped the label normalisation that turns `9A` into `9`.

## [1.27.0] — 2026-08-03

The manifest from v1.26.0 knew the IATA DGR expires on 31 December 2026, but only told
whoever asked `/api/regulatory`. Someone making an air declaration in 2027 saw nothing.

### Added

- **A compliance result now says when it was computed with an edition that no longer
  applies.** The warning reaches the wizard *and* the export, because a document outlives
  the session it was made in while a screen does not. Expiry is not a prohibition, so it
  warns rather than blocks — stopping the export would only push people to work around
  the check.
- **`stale_rule_sets()`, which is deliberately not the same as `expired_rule_sets()`.**
  The 41-22 UN cards are expired *and knowingly replaced*: columns 16a and 16b have come
  from the 42-24 list since v1.23.0, and what the cards still supply — marine pollutant
  and bulk — did not change with the edition. Warning about that on every single check
  would make warning itself worthless: someone who dismisses a message every time will
  dismiss the one that matters too. A rule set carrying `superseded_by` is left out.

  Today this reports nothing at all. On 1 January 2027 it reports the IATA DGR, and only
  to the IATA profile — a road shipment has no use for an air-freight notice.
- **The manifest id travels with the result**, in the compliance response and under the
  panel, so a bug report can say which data the installation computed with.

## [1.26.0] — 2026-08-03

### Added

- **A regulatory manifest**, at `GET /api/regulatory` with a compact form on
  `GET /api/health`. Per rule set: edition, source, validity period, errata, what it
  covers, and a SHA-256 over every data file behind it.

  It answers two questions documentation cannot. **Has an edition expired?** The IATA
  DGR is replaced yearly and the 67th edition runs to 31 December 2026; from 1 January
  2027 the manifest reports it as expired rather than quietly carrying on. The UN cards
  (41-22) already come out as expired — still used, but only for marine pollutant and
  bulk carriage, and the entry says so. **Do two installations hold the same data?** The
  `manifest_id` is a hash over all seed files together.

  Where something is not tracked, it says so: IATA addenda and operator variations are
  named as out of scope rather than left to look complete.

- **An `Authorization` field on the IATA declaration** — the approval, exemption or DGR
  reference a shipment flies under. The template EMCargo fills has no form field for
  it (that box sits inside the goods table), so it is written as its own labelled line
  under that table. Left empty it is omitted entirely: an empty box with the word
  "Authorization" in it suggests something was approved.

### Notes

- The reviewer's concern about the IATA edition turned out to be unfounded: the
  compliance rules already cite the 67th edition (2026). A test now ties the manifest and
  those rules together so they cannot drift apart.

## [1.25.0] — 2026-08-03

> [!CAUTION]
> **Reverted in [1.29.3](#1293--2026-08-04). Do not run this version or anything up to
> 1.29.2 unless you set `APP_SECRET_KEY` and `CORS_ALLOWED_ORIGINS` yourself.** What this
> release introduced — refusing to start on a published or empty signing key — matched the
> values EMCargo itself shipped with, so installations that had not configured both by
> hand simply died at startup. The signing key is generated automatically from 1.29.3
> onwards; see [Configuration](docs/configuration.md#the-signing-key-looks-after-itself).
>
> The note as it read at the time:
>
> > **Upgrading may stop your container on purpose.** If you never set `APP_SECRET_KEY`,
> > EMCargo now refuses to start and tells you what to put there — including a
> > ready-made key. Changing the key logs everyone out; nothing else is lost.

### Fixed

- **An installation that never set `APP_SECRET_KEY` had no working authentication.**
  That key signs the JWT that says you are logged in, and its default — `change-me` —
  is published in this repository. Anyone holding it can write themselves a valid admin
  token, so there was no login to bypass; it was already bypassed. `APP_ENV` defaults to
  `production`, so this was the state of every deployment that followed the quickstart
  without setting the variable.

  The application now stops at startup. Logging a warning was the alternative and it is
  not one: logs go unread and the app keeps serving.

### Added

- **`app/core/security_checks.py`**, run before the application is even assembled.
  Three things are refused in production, all reported at once so a single restart is
  enough:

  - `APP_SECRET_KEY` that is empty, published (`change-me`, `dev-secret`, the
    placeholder from `.env.example` — which is 34 characters and would otherwise have
    passed a length check) or shorter than 32 characters.
  - `CORS_ALLOWED_ORIGINS=*` while the API works with cookies, which lets any website
    make requests on behalf of a logged-in user.
  - `ADMIN_PASSWORD` set to one that appears in this project's own documentation.

  The error carries a freshly generated key that is usable as-is, and a test asserts
  that the suggested key passes the check — an error message that stops the app has to
  contain its own solution.

- Anything that is not clearly a development environment counts as production, so a
  typo in `APP_ENV` cannot quietly switch the check off.

### Changed

- `.env.example` no longer ships a configuration that would be refused: the secret and
  the admin password are empty with instructions above them, and `CORS_ALLOWED_ORIGINS`
  names an address instead of `*`.

## [1.24.2] — 2026-08-03

Checks that run on their own, and one gap they found.

### Added

- **CI** (`.github/workflows/ci.yml`): backend pytest and the frontend tests plus
  typecheck on every push and pull request to main. The workflows here were all about
  publishing; the tests only ran locally, so a broken test could travel all the way to
  a release.
- **A version-consistency test.** The number lives in four places and they must agree.
  This is not theoretical: an external review of EMCargo produced a list of problems
  that were largely already fixed, because the reviewer was reading
  `frontend/package.json` at 1.14.1 while the rest of the project was far past it. The
  test also insists the changelog leads with the current version.
- **Export integration tests** that read the generated PDF back: the export runs the
  compliance check itself, a Q above 1 blocks it while a Q within the limit does not,
  the air declaration carries the IATA packing instruction and not the ADR one, the
  emergency contact reaches the document, and the declaration comes out flat so the
  values cannot be edited away.

### Fixed

- **An export above the ADR 1.1.3.6 threshold said nothing.** Only an incomplete points
  calculation produced a warning; going over the threshold, or carrying a category 0
  substance, produced none at all. Neither is forbidden — but the exemption lapses, and
  with it come driver training, an ADR vehicle, orange plates and extinguishers. Someone
  who last saw "exemption possible" on screen now reads on the export that it no longer
  applies, with the totals behind it.

## [1.24.1] — 2026-08-03

Two defects in the compliance panel that only a test would catch, and the tests to
catch them.

### Fixed

- **A slow older check could overwrite a newer one.** Two checks can be in flight at
  once — you keep typing while the previous request is still out — and if the first
  resolves last, its result won. The screen then showed an outcome belonging to input
  from two edits ago. Each check now carries a sequence number and a stale response is
  discarded.
- **A 422 came out as `[object Object]`.** FastAPI answers a validation error with a
  list of `{loc, msg}` per field, and that went straight into `new Error()`. You could
  see something was wrong but not what, or which field. `describeDetail()` in the API
  layer now turns it into `entries → 0 → products → 1 → adr_total_quantity: hoeveelheid
  '-5 L' moet groter dan nul zijn`, and the panel renders it as an alert over several
  lines. Since v1.24.0 refuses unusable input, this is the normal path rather than an
  edge case.

### Added

- **Vitest and Testing Library**, with `npm test` in `frontend/`. Thirteen tests cover
  the panel's core promise — what is on screen belongs to the input that is there now:
  automatic re-check after the debounce, the previous outcome cleared the moment input
  changes, a stale response losing to a newer one, and a validation error appearing
  readably with no old result left beside it.

## [1.24.0] — 2026-08-03

The compliance endpoint validates its input instead of coercing it.

### Added

- **`backend/app/schemas/dg_compliance.py`** — `ComplianceRequest`,
  `ShipmentPosition`, `DangerousGoodsProduct` and a `RegulatoryProfile` enum.
  `POST /api/dg/compliance` took `entries: list[dict]` and `profiles: list[str]`, so
  Pydantic never looked at them and the calculation layer had to make the best of
  whatever arrived.

  Two cases are dangerous there, because they do not surface as an error but as a
  *more favourable* answer than reality:

  - A negative quantity lowers the ADR 1.1.3.6 points total and can suggest an
    exemption that does not apply. `-5 L`, `0` and `0 kg` are now refused.
  - A misspelled profile (`IDMG`) silently produced no sea-transport check at all,
    and the screen then showed a clean result with nothing behind it. Profiles are
    an enum: ADR, RID, ADN, IMDG, IATA.

  Also refused: a packing group other than I/II/III, a transport category outside
  ADR's 0–4, and a Q component with `n` or `M` at zero — which used to drop out of
  the sum unnoticed. All of these return **HTTP 422 before anything is calculated**.

  Empty stays allowed. The wizard sends half-filled input while you work, and the
  check is supposed to report `incomplete` rather than refuse the request. Fields
  the schema does not name are passed through untouched, and `class` keeps its own
  name on the way to the calculation layer.

## [1.23.1] — 2026-08-03

Community health files, so it is clear how to report something and what happens next.
No change to the application.

### Added

- **`CONTRIBUTING.md`** — says plainly that this is a personal project: reports and
  corrections are very welcome, code should be agreed in an issue first. Covers what a
  useful report contains for weights, documents and dangerous goods, and repeats the two
  standing rules: no regulatory text in the repository, and redact real shipment data
  before attaching anything to a public issue.
- **`SECURITY.md`** — private vulnerability reporting through GitHub, with the scope
  spelled out for a self-hosted app: authentication and the admin bootstrap, file upload
  and PDF handling, path traversal in export and UN card downloads, and
  `CATALOG_AUTO_SYNC` fetching external URLs at startup. Wrong regulatory data is
  explicitly *not* a security issue — it is a normal bug.
- **`CODE_OF_CONDUCT.md`** — Contributor Covenant 2.1, with the private advisory thread
  as the confidential channel since the repository publishes no email address.
- **Issue forms** in `.github/ISSUE_TEMPLATE/`: a bug report, a data-or-document
  correction that asks for the source and its edition, and an idea form that asks for the
  situation rather than the feature. Blank issues are off; the security advisory, the
  documentation and the rule-set-editions table are linked instead.
- **`.github/pull_request_template.md`**, with the project's own checks: changelog, the
  three version files agreeing, both language files, no regulatory text, no real shipment
  data.

## [1.23.0] — 2026-08-03

The Dangerous Goods List itself, all 2860 entries of it, now backs columns 16a and 16b —
the columns 7.2.3.1 lets take precedence over the segregation table.

### Added

- **`backend/seed/dg/imdg_dgl.json`**: chapter 3.2 of IMDG Amendment 42-24, read by
  `scripts/extract_imdg_dgl.py` from IMO resolution **MSC.556(108)**. 2860 rows over 2347
  UN numbers — entries with several packing groups appear once per group — carrying class,
  subsidiary hazards, packing group, special provisions, limited and excepted quantities,
  packing and IBC and tank instructions, EmS, stowage and handling, segregation, and the
  properties column.
- **`app/services/dg/dangerous_goods_list.py`** reads that file per UN number and splits
  the columns the way the code writes them: `Category B SW2 SW5` into a stowage category
  and its codes, `SGG2 SG27 SG31` into segregation groups and SG codes. A dash is layout,
  not a value, and is dropped rather than passed on.
- **Stowage category for 2324 UN numbers**, where the UN cards carried it for none.
- **The change marker.** The list prints a triangle in front of every entry Amendment
  42-24 touched; those 66 entries are flagged, and the wizard says so.
- Special provisions, packing instructions, tank instructions and the properties column
  are surfaced per substance.

### Changed

- Column 16b now comes from the list rather than the UN cards. Coverage goes from 840 to
  847 UN numbers, and 81 codes that the card extraction had dropped mid-list come back —
  UN 1295 for instance carried `SG5 SG8 SG13 SG25` and actually has
  `SG5 SG8 SG13 SG25 SG26 SG36 SG49 SG72`. No substance loses a code except UN 2988,
  whose card row is misaligned (see below). Column 16a gains 118 UN numbers and the H
  codes of 7.1.6, which the cards did not name.
- Segregation groups are taken from 3.1.4.4 and column 16b together instead of 3.1.4.4
  alone, and both lookups now honour the packing group.

### Notes

- The extraction checks itself against two independent sources and refuses to write below
  the agreement threshold. It came out at **EmS 2293/2293** and **class 2322/2336**.
  All fourteen class differences were examined and none is a misread: twelve are defects
  in `card_data.json`, where UN 2984–2992, 3548 and 3550 carry sequence numbers
  (`"4"`, `"5"`, `["13","14","12"]`, `"6.3"`) instead of classes; UN 1950 is the ADR split
  `2.1 / 2.2` against the code's plain class 2; and UN 3423 is a genuine 42-24
  reclassification from 8 to 6.1 (8), which the list's own change marker confirms.
  `card_data.json` is left as it is for now — it is a separate source and correcting it is
  its own job.

## [1.22.0] — 2026-08-02

The IMDG Code's own chapter 7 now supplies the wording behind every column 16a and 16b
code, replacing the fragments that were scrapeable from the UN cards.

### Added

- **The stowage, handling and segregation code descriptions**, in
  `backend/seed/dg/imdg_codes.json`: **SW1–SW31** from 7.1.5, **H1–H5** from 7.1.6 — a
  series the app did not carry at all — and **SG1–SG78** from 7.2.8. Read by
  `scripts/extract_imdg_codes.py` from IMO resolution **MSC.556(108)**, the instrument
  that adopted Amendment 42-24. The compliance findings and the wizard both prefer this
  wording; the card paraphrase remains only as a fallback.
- **Reserved codes are kept apart.** SG64, SG66 and SG73 read `[Reserved]`, which is not
  a provision, so they are never offered to a user as guidance.

### Fixed

- The extractor's first run found nothing: `find_section` anchored `^` against the whole
  page without `re.MULTILINE`. It now matches on the introducing sentence, which is
  unique — the section number appears in the contents list and in five cross-references.
- The workflow reported "nothing to commit" after a successful extraction, because
  `git diff` does not see a file that is still untracked.

### Notes

Two readings confirmed earlier work against the source rather than against a summary.
7.2.3.1 reads, verbatim, *"In case of conflicting provisions, the provisions of column 16b
of the Dangerous Goods List, always take precedence"* — the rule implemented in v1.21.0.
And SG75 is absent from the segregation code list altogether, where SG64, SG66 and SG73
are explicitly reserved: independent confirmation that the SGG1a marking removed in
v1.21.0 had indeed left the Code.

## [1.21.0] — 2026-08-02

IMDG Amendment 42-24 has been mandatory since 1 January 2026. This release closes the gap
without pretending to a full rebuild: the tables that turned out to be unchanged are
confirmed as current, the per-substance changes are applied as a difference layer, and
column 16b now takes the precedence the Code gives it.

### Added

- **An IMDG 42-24 difference layer** (`backend/seed/dg/imdg_42_24.json`), laid over the
  41-22 UN card data. It holds the eleven new UN numbers with their EmS schedules — sodium
  ion batteries UN 3551/3552, the battery-powered vehicle entries UN 3556–3558, disilane
  UN 3553, gallium in manufactured articles UN 3554, the trifluoromethyltetrazole entry
  UN 3555, both fire suppressant dispersing device entries UN 0514/3559 and the new
  tetramethylammonium hydroxide entry UN 3560 — plus 42 amended entries and the new
  stowage code SW31.
- **The new UN numbers are searchable.** Sodium ion batteries exist in IMDG 42-24 and not
  yet in ADR 2025; they are merged into the lookup marked as IMDG-only, so a sea shipment
  can find them instead of coming up empty.
- **Per-substance change notes.** UN 2303 became a recognised marine pollutant and gained
  SW1; UN 1361 gained SW27; UN 2956 gained SW11; UN 3536 moved to stowage category D. Each
  change is shown against the substance in the wizard, in Dutch and English.
- **The UN 1361 document requirement of 5.4.1.5.18** — date of production, date of
  packing, mean material temperature and ambient temperature on that day — is raised as a
  requirement when the substance is declared.
- **IMDG 7.2.3.1 precedence.** The class segregation table and a substance's own SG codes
  can disagree about the same pair; the Code says column 16b always wins. Nitric acid
  beside sulphur is the plain case: the table says "away from", SG16 says "separated from",
  and the 16b provision now governs. Both findings stay visible — the governing one says
  it governs, the superseded one says what superseded it — because hiding a segregation
  finding is a worse failure than showing one too many.

### Changed

- **Chapter 7.2 is no longer flagged as out of date.** The only change 42-24 makes there
  is a rewording of 7.2.6.1. The class segregation table (7.2.4), the exemption tables
  (7.2.6.3), the class 1 compatibility matrix (7.2.7.1.4) and the segregation groups
  (3.1.4.4) are unchanged, so the tables the app computes with are the current ones. The
  `rule_sets` metadata on every result says this, names the source of the difference layer,
  and lists what the layer does not cover.
- **A changed classification is reported, never silently applied.** UN 3423 becomes class
  6.1 with a subsidiary 8 in 42-24 while ADR 2025 still lists it as class 8. Segregation is
  still computed on the ADR classification and a warning says so, because swapping the
  class behind the scenes would change the outcome with nothing on screen to explain why.

### Removed

- **The SGG1a tagging.** The separate segregation-group marking for strong acids was
  dropped from the Code with Amendment 41-22 — the UN cards never mention it and 42-24
  leaves 3.1.4.4 alone — but 21 substances still carried it. Removed from the seed, from
  the label lookup and from the documentation.

## [1.20.0] — 2026-08-02

Fixes from an external review: calculation errors, stale state, the IATA PDF, and
export enforcement. Every confirmed defect has a regression test that reproduces
the reported failure.

### Fixed

- **Derived quantities no longer go stale.** The ADR total and the Q net quantity are
  computed values, but they were only filled when empty — so after editing 2 packages of
  10 L into 3 of 20 L, the description showed 60 L while the points calculation still used
  20 L and the Q value 10 L. They are now recomputed from the current package data on
  every derivation; `adr_total_quantity_override` and `q_net_quantity_override` pin a
  manual value. The wizard also re-derives when quantities, contents or packaging change,
  not only when a UN number changes.
- **The Q value could round an exceedance away.** Component ratios were rounded to four
  decimals before summing: 0.50001 + 0.50001 became 1.0 and passed. The sum is now taken
  over unrounded Decimal ratios and only the result is rounded up — that case yields
  Q = 1.1, exceeded.
- **Invalid Q components no longer vanish.** A missing, zero or negative n or M used to
  drop the component silently, and with fewer than two left the whole result disappeared.
  The position now reports status `incomplete` with the reason.
- **Negative quantities are invalid input, not a discount.** A numeric −5 lowered the ADR
  points total; the text "-5 L" was read as +5 because the parser dropped the sign. The
  parser keeps the sign and both calculations treat non-positive quantities as incomplete.
- **The IATA declaration no longer carries an ADR packing instruction.** The automatic
  derivation fills the generic field with the ADR instruction (P001, IBC02, …), and the
  official PDF printed that field. The PDF now uses `iata_packing_instruction`, accepts a
  numeric instruction typed into the generic field, and prints nothing rather than an
  instruction that is invalid in the air.
- **The 24-hour emergency contact reaches the PDF.** It was a required input that was
  never written; it now lands in Additional Handling Information.
- **The stale compliance panel.** The result is cleared the moment the substances change
  and re-checked automatically after a short debounce, instead of keeping the previous —
  possibly green — outcome on screen until someone pressed the button.
- **Info findings looked like problems.** The 7.2.6.3 exemption has severity `info` but
  was styled identically to a warning; it is now visually distinct.

### Added

- **Export re-runs the compliance engine server-side.** The panel in the wizard is an
  aid; the frontend is no longer the only place where compliance is enforced. A DG
  document export now blocks on segregation errors and on an exceeded Q value, and
  carries the remaining findings as warnings.
- **Every compliance result names its rule sets** — including, prominently, that the
  IMDG data on board is Amendment 40-20 (class tables) and 41-22 (per-substance data)
  while **Amendment 42-24 is mandatory since 1 January 2026**. Until the data is
  refreshed, IMDG outcomes are indicative and the current Code prevails. See
  [docs/dangerous-goods.md](docs/dangerous-goods.md#rule-set-editions).

## [1.19.0] — 2026-08-02

SG72, and it turned out to be a relaxation.

### Added

- **The four tables of IMDG 7.2.6.3**, from chapter 7.2 of Amendment 40-20 — the same
  edition as the class segregation table. SG72 in column 16b points at them, and 36
  substances carry it.
- SG72 reads "See tables in 7.2.6.3", which sounds like an extra restriction. It is the
  opposite: *"No segregation needs to be applied … Substances within the same table
  7.2.6.3.1, 7.2.6.3.2 or 7.2.6.3.3 are compatible with one another."* Two organic
  peroxides from table 7.2.6.3.4, for instance, need no segregation between them.
- **The exemption never removes a warning.** Suppressing a segregation finding on the
  strength of a rule is a worse failure than showing one too many, so the exemption is
  reported alongside the finding with its table named. The finding and its legal basis end
  up in view together and the judgement stays with the shipper — which is how a safety
  adviser would read it anyway.
- Table 7.2.6.3.4 carries the caveat of 7.2.6.4: the dangerous reactions of 7.2.6.1.1 to
  7.2.6.1.4 continue to apply. That is stated in the finding.

With this, five provisions remain shown-but-not-checked, and none of them is a rule: SG1
and SG77 modify other provisions, SG48 and SG71 are definitions, and SG69 applies only to
waste aerosols.

## [1.18.0] — 2026-08-02

The remaining segregation provisions, as far as they go.

### Added

- **Provisions that name a substance are now checked.** Eight of them — sulphur, chlorine,
  ammonia, bromine, carbon tetrachloride, ammonium salts, mercury salts, and explosives
  containing chlorates or perchlorates. The wording is resolved to UN numbers in
  `dg_compliance.json`, deliberately narrowly: SG62 says "sulphur", which means elemental
  sulphur (UN 1350, UN 2448), not sulphur dioxide.
- Where a defined segregation group stands in for a narrower wording — SGG2 "ammonium
  compounds" for the "ammonium salts" of SG22 — the warning says so, because the match is
  wider than the provision.
- **Provisions whose target is ordinary cargo are raised as requirements.** Foodstuffs,
  animal and vegetable oils, odour-absorbing cargo, liquid organic substances. EMCargo
  does not know what non-dangerous cargo travels alongside, so these appear whenever the
  substance is in the shipment — the same shape as the existing ADR CV28 foodstuff
  warning. SG26 is conditional and only appears next to class 2.1 or 3.

### Fixed

- **SG74 was missed by the parser.** It reads "Segregation as for 1.4G" without the word
  "class", so it fell through to the informational bucket instead of becoming a rule.

### Still shown but not checked

Six provisions, and they are not rules: SG1 and SG77 modify other provisions, SG48 and
SG71 are definitions, SG69 is conditional on the substance being waste aerosols, and SG72
points at a table in IMDG 7.2.6.3 that is not in any source we hold. Turning any of these
into a check would mean inventing the rule.

## [1.17.0] — 2026-08-02

Column 16b is now a check, not just a note.

### Added

- **The segregation provisions of column 16b are applied to the shipment.** The class
  table of IMDG 7.2.4 works on class; column 16b adds provisions per substance. Load
  anhydrous ammonia (UN 1005) together with hydrochloric acid (UN 1789) and the compliance
  panel now reports both sides of it: *"Stow separated from SGG1 (Acids). Stow 'separated
  from' SGG1 – acids (SG35)"* against the ammonia, and the mirror-image SG36 against the
  acid. Until now the codes were only displayed.
- **The meaning of each code was read from the cards, not written from memory.** Every SG
  code appears in a fixed sentence — *Stow "separated from" class 5.1 (SG17)* — so the
  action and its target are parsed out of the source itself. Of the 70 codes in use, 48
  name a class or a segregation group and became machine-checkable; the other 22 point at
  foodstuff tables, named substances or a table in the Code, and are shown to the user
  without being acted on. A wrong segregation rule is a safety-relevant error, so guessing
  at the ones that do not parse cleanly is not on the table.
- **Exceptions are honoured.** SG14 reads "separated from class 1 except for division
  1.4S". Treating 1.4S as a second target would warn about a load the Code explicitly
  allows, so the exception is parsed separately and suppresses the finding.
- A bare class target covers its divisions — "separated from class 1" applies to 1.1D as
  much as to 1.3G — and subsidiary risks count towards a match, not just the primary class.

## [1.16.0] — 2026-08-02

Columns 16a and 16b, per substance.

### Added

- **Stowage and segregation codes for 2,336 UN numbers**, read out of the UN cards by
  `scripts/extract_un_card_data.py` into `backend/seed/dg/card_data.json`. 1,242
  substances carry stowage codes (SW, column 16a) and 840 carry segregation codes
  (SG, column 16b). Nitric acid, for instance, now yields
  `SG6, SG16, SG17, SG19, SG36, SG49`.
- **Each code comes with the wording that explains it.** `SG6` on its own tells a user
  nothing; the dangerous goods step shows "Segregation as for class 5.1 (SG6). Stow
  'separated from' class 7 (SG19)." This was the last place the app had to send someone
  to the Dangerous Goods List itself.
- **Marine pollutant per substance** (column 4): 202 confirmed, 38 explicitly not, and
  the rest marked as depending on the actual substance — which is what the source says
  for n.o.s. entries, and is reported as such rather than guessed either way. A confirmed
  marine pollutant now fills the field on the IMO and IMDG documents by itself.
- **Bulk carriage**: the 28 substances that may travel in bulk, with their BK instruction.

### Verification

The extraction read its own EmS code from every card and compared it with `ems.json`,
which comes from the official EmS Guide: **2,282 agreed and none disagreed**. Two
independent sources for the same field arriving at the same answer is a good sign for
both of them. The EmS Guide remains the authority; the card reading is only a check.

### Removed

- The **Fetch UN cards** workflow. It was a one-off and its work is done. Both scripts
  stay, so a future edition of the IMDG Code is a matter of running them again — see
  [docs/development.md](docs/development.md#the-un-cards).

## [1.15.0] — 2026-08-02

The UN card library is in.

### Added

- **2,849 UN cards covering 2,336 UN numbers** in `un_cards/`, fetched from Cantell's
  IMDG UN cards (2023 edition, IMDG 41-22). Every one of the 2,900 source files was
  opened and the UN number read out of the card itself, because the source numbers its
  files sequentially with no relation to their contents. 2,703 were confirmed by both the
  number and the shipping name, 146 by the number alone, and **none** contradicted itself
  or fell out of sequence. A sample of twelve was checked by hand against the filename:
  twelve correct.
- The 2,336 unique UN numbers match `backend/seed/dg/un_numbers.json` exactly. The extra
  513 cards are second and third entries for the same UN number, which the regulations
  give a separate card per packing group; all of them are handed to the user.
- **The download option in the export now works.** A shipment with dangerous goods gets a
  zip with the cards for the substances it declared. It was built in 1.14.0 but stayed
  hidden while the library was empty.

### Changed

- Parts 2850 to 2900 of the source are the card layout with every field empty. They carry
  no substance and are not included; `manifest.json` records that they were seen.
- The fetch workflow no longer fails when it cannot open a pull request — that needs a
  repository setting, and the pushed branch is the deliverable either way. It prints the
  compare link instead.

### Note on size

`un_cards/` is 581 MB on disk but **49 MB packed**: every card embeds the same seven
fonts, so git's delta compression collapses them, and the Docker layer compresses the
same way. A clone and an image pull stay small; the unpacked container grows by ~580 MB.

## [1.14.1] — 2026-08-02

### Changed

- **The UN card fetcher now reads the card's own `UN number` field.** The real cards
  (Cantell's IMDG UN cards, 2023 edition) are laid out as label/value pairs and repeat
  the number in the footer, which is far more reliable than judging by font size. Both
  are read and must agree; a card that contradicts itself is parked for a human instead
  of being filed on a coin flip. The previous heuristic — prominence plus shipping-name
  match — remains as the fallback.
- The source URL is filled in as the workflow's default, and the parts are checked for
  ascending UN order so a card that steps backwards is flagged even when it read cleanly.

## [1.14.0] — 2026-08-02

UN cards for your own records.

### Added

- **Download the UN cards for your substances** at the end of the wizard. A shipment
  with dangerous goods gets a zip with one reference card per UN number it declared —
  only those, not the whole library — plus a README stating what is in it and which
  declared substances no card is held for. The cards are reference material for the
  user's own file; they are not transport documents and are attached to nothing.
  New endpoints: `POST /api/documents/un-cards` and
  `POST /api/documents/un-cards/availability`.
- **A workflow to fetch the card library** (`.github/workflows/fetch-un-cards.yml`).
  The source numbers its files sequentially — `part1`, `part2`, … — with no relation to
  the UN number on the card, so the workflow opens every document, reads the UN number
  out of the contents and saves it as `un_1033.pdf`.
- The identification is deliberately cautious. A four-digit number only counts if it is
  a real entry in the UN database, prominence on the page is weighed so a page number or
  a cross-reference cannot outrank the card's own heading, and a card is marked
  `confirmed` only when the shipping name printed on it matches the name we hold for
  that number. Anything weaker goes to `un_cards/_unidentified/` for a human to look at,
  and `un_cards/manifest.json` records what happened to every part. A card filed under
  the wrong UN number would hand someone the emergency information for a different
  substance, so the script skips rather than guesses.
- If the card library is absent — any fork that has not run the workflow — the download
  option simply does not appear.

## [1.13.2] — 2026-08-02

Documentation rewritten, in English, and split up.

### Changed

- **The README is now about the app, not about everything.** It says what EMCargo is,
  what it does for you and how to start it, and links onward. Installation instructions,
  environment variables, data provenance and developer setup have moved into `docs/`.
- **All documentation is in English**, including the changelog and the roadmap.
- **New guides in `docs/`**: [getting started](docs/getting-started.md),
  [user guide](docs/user-guide.md), [documents](docs/documents.md),
  [dangerous goods](docs/dangerous-goods.md), [configuration](docs/configuration.md),
  [data sources](docs/data-sources.md), [privacy](docs/privacy.md) and
  [development](docs/development.md).
- Badges on the README for Docker pulls, the latest release, build status, development
  status, licence, image size and stack.
- The disclaimer is now available in English as `DISCLAIMER.md`. The Dutch text remains
  the legally binding version and has moved to `DISCLAIMER.nl.md`; the two link to each
  other.

### Fixed

- **`GET /api/health` reported the wrong version.** `backend/VERSION` takes priority over
  the repository root `VERSION`, and it had been left at 1.13.0. Both are now bumped
  together, and a test fails if the root `VERSION`, `backend/VERSION` and
  `frontend/package.json` ever drift apart again.
- The transport mode tiles still advertised "internal forms" — a leftover from the
  military form removed in v1.4.0 — and a separate ADR document that no longer exists
  since v1.13.0. Road now reads "CMR and AVC waybill, packing list and delivery note",
  inland waterway "ADN document, VGM and packing list".

## [1.13.1] — 2026-08-02

The AVC waybill now fills in the official form.

### Changed

- **The AVC waybill is no longer redrawn — it is filled in.** The official waybill form
  from sVa / Stichting Vervoeradres now ships as `templates/forms/avc.pdf` and is filled
  in by the backend, just like the CMR, the CIM and the IATA declaration. The previous
  version redrew the form with reportlab; the result looked like the original but was
  not one.
- Unlike the CMR, the AVC form has no PDF form fields (AcroForm), so the values are
  placed as a text layer over the template. The positions are derived from the form's
  own ruling and field labels: sender, delivery address, franking instruction with the
  Franco / Not franco checkboxes, carrier, the goods table with its number, packaging,
  contents and weight columns, the totals, and the place and date of dispatch — in both
  the waybill and the receipt panel.
- The ADR description (5.4.1.1.1) stays in the "contents" column, and the total per
  transport category (5.4.1.1.1.1) now appears under the last goods line instead of in
  the footer. Text too long for a column is wrapped on actual text width, so the
  "contents" column no longer runs into "weight in kg".
- The AVC waybill therefore also gets the **Official form** label in the form overview.

## [1.13.0] — 2026-08-02

An AVC waybill in place of a separate ADR road document.

### Added

- **AVC waybill** for domestic road carriage, generated as a PDF following the standard
  sVa / Stichting Vervoeradres model: the waybill on the left, the receipt on the right,
  with the same box layout (sender, delivery address, franking instruction with Franco /
  Not franco, carrier, goods table with number, packaging, contents and weight, totals,
  place and date of dispatch). The reference clause makes the **Algemene
  Vervoercondities 2002** applicable. The carrier's signature and the consignee's receipt
  stay blank; the sender can have their own signature placed.

### Changed

- **The CMR now carries the dangerous goods data itself.** For a package containing
  dangerous goods, the official description under ADR 5.4.1.1.1 goes into boxes 6–12
  (`UN 1203, GASOLINE, 3, II, (D/E), 10 jerrycan, 200 L`) instead of the free
  description, and box 13 gets the total quantity per transport category (5.4.1.1.1.1).
  Packages without dangerous goods keep their normal description, and the mass is not
  counted twice.
- The same applies to the AVC waybill: the ADR description appears in the "contents"
  column.

### Removed

- **The separate ADR transport document for road has been dropped.** ADR 5.4.1
  prescribes no form for the transport document: a waybill carrying the data of
  5.4.1.1.1 is sufficient. Now that the CMR and the AVC waybill contain that description
  themselves, a separate document is redundant. The ADN transport document for inland
  waterways remains, because there is no waybill for that mode in the app.

## [1.12.0] — 2026-08-01

Segregation groups per substance, from the official IMDG Code.

### Added

- **All eighteen segregation groups with their substances** (IMDG 3.1.4.4): 632 entries
  across 539 UN numbers, from acids and alkalis to cyanides, azides, permanganates,
  metal powders and mercury compounds. The 21 **strong acids** get the separate SGG1a
  marking. A substance can fall into several groups — lead azide (UN 0129) belongs to
  heavy metals, lead *and* azides at once.
- **Segregation group straight from the UN number**: as soon as a UN number is entered,
  the app shows the applicable groups, for example "SGG1 (Acids), SGG1a (strong acids)"
  for hydrochloric acid.
- **Incompatible segregation group checks** in the compliance panel for sea freight.
  Reported combinations include acids with alkalis, acids with cyanides (hydrogen
  cyanide), acids with chlorites or hypochlorites (chlorine dioxide and chlorine gas
  respectively), acids with nitrites, acids with azides (explosive hydrazoic acid), acids
  with metal powders (hydrogen evolution) and peroxides with acids. Manually entered
  group codes are taken into account.

## [1.11.0] — 2026-08-01

EmS emergency schedules, complete, from the official EmS Guide.

### Added

- **All 2,338 UN numbers from the EmS Guide.** The index of IMO MSC.1/Circ.1588/Rev.3
  (*Revised Emergency Response Procedures for Ships Carrying Dangerous Goods*) has been
  taken over in full. Coverage goes from 12.9% to **99.5% exact codes**; only a handful
  of entries not present in the guide still fall back on an indicative class default.
- **A description with every code**: all ten fire schedules (F-A Alfa "general fire
  schedule" through F-J Juliet) and all 26 spillage schedules (S-A Alfa "toxic
  substances" through S-Z Zulu "toxic explosives") are included in Dutch and English.
  The app now shows "F-E (Flammable liquids that do not react with water) · S-E
  (Flammable liquids that float on water)" instead of just the code.
- **A schedule per packing group**: 43 UN numbers have a different emergency schedule per
  packing group — UN 1826 (nitrating acid mixture), for instance, is treated as oxidising
  (S-Q) in packing group I and corrosive (S-B) in group II. Without a known packing
  group, the app shows both options rather than guessing one.
- **Variants with their own schedule**: UN 3166 (vehicles) gets a different schedule for
  gas than for liquid propulsion; both are shown.
- **Air freight rules updated** to the IATA Guidance Document for Lithium Batteries and
  Sodium ion Batteries, 2026 edition: the 30% state-of-charge limit under PI 965 with the
  approval route of special provision A331, the CAO label for UN 3090/3480, approval
  route A201, and newly the **sodium-ion batteries** UN 3551 (PI 976) and UN 3552 (PI
  977/978) — with the caveat that sodium-ion batteries with an aqueous alkaline
  electrolyte fall under UN 2795. The battery-powered vehicles UN 3556, 3557 and 3558 are
  included as well.

### Changed

- The EmS data no longer comes from a curated selection but straight from the official
  guide. During the transfer, 13.5% of the earlier curated entries turned out to deviate
  (39 out of 288), mostly oxidisers that are F-H rather than F-A and temperature-controlled
  peroxides that fall under F-F. All of those are now correct.

## [1.10.0] — 2026-08-01

Segregation verified against the official IMDG Code and extended with segregation groups
and class 1.

### Changed

- **Segregation table verified and updated to Amendment 40-20.** The table was compared
  line by line with chapter 7.2 of the official IMDG Code. 287 of 289 cells were already
  correct; four cells were updated because Amendment 40-20 is stricter than the older
  edition the previous version relied on:
  - class 2.1 × 4.3: from "no general segregation" to **2 (separated from)**
  - class 3 × 4.3: from 1 (away from) to **2 (separated from)**
  - class 2.2 × 5.2: from 2 to **1 (away from)**

  The table is now pinned verbatim in a test, so a future change cannot slip through
  unnoticed.

### Added

- **Segregation groups (IMDG 7.2.5)**: all nineteen groups SGG1 through SGG18 (acids,
  strong acids, ammonium compounds, bromates, chlorates, chlorites, cyanides, heavy
  metals, hypochlorites, lead, halogenated hydrocarbons, mercury, nitrites, perchlorates,
  permanganates, metal powders, peroxides, azides and alkalis) are included as reference
  in the compliance panel, with the explanation that column 16b of the Dangerous Goods
  List determines whether a substance belongs to one, and that for n.o.s. entries the
  shipper assesses this themselves (5.4.1.5.11).
- **Exception for class 8 (IMDG 7.2.6.5)**: acids and alkalis of packing group II or III
  may nonetheless travel together in one cargo transport unit in packages up to 30 L or
  30 kg, provided the substances do not react dangerously and the transport document
  carries the statement of 5.4.1.5.11.3.
- **Loading compatibility check for explosives (IMDG 7.2.7.1.4)**: the full compatibility
  group matrix A through S now determines whether class 1 packages may share a space or
  cargo transport unit. Group S is compatible with everything except L; group L only with
  its own type; the special provisions for groups G (fireworks), L and N are shown as
  warnings. The exception of 7.2.7.2.1 (ammonium nitrate and nitrates together with
  explosives, except UN 0083) is included.
- **A subsidiary class 1 risk counts as division 1.3** when determining segregation (IMDG
  7.2.3.3), which is stricter than the primary hazard alone.

## [1.9.0] — 2026-08-01

EmS database extended and carriage prohibitions flagged.

### Added

- **EmS emergency schedules extended from roughly 90 to 305 UN numbers** in a dedicated
  data file (`backend/seed/dg/ems.json`), grouped by hazard profile: flammable, toxic,
  oxidising and inert gases, flammable liquids (distinguishing those that float on water
  from the rest), flammable and pyrophoric solids, water-reactive substances, oxidising
  substances and ammonium nitrate, organic peroxides, toxic and infectious substances,
  radioactive material, corrosives (including the corrosive-and-oxidising combinations),
  environmentally hazardous substances and lithium batteries. Each entry shows the
  profile ("Flammable liquid that floats on water"), so it is visible *why* that schedule
  applies.
- **Carriage prohibition flagging**: fourteen substances that ADR Table A does not permit
  for carriage (including UN 1798 aqua regia, UN 2249 symmetrical dichlorodimethyl ether,
  UN 2186 refrigerated hydrogen chloride and several n.o.s. entries with incompatible
  hazards) are recognised. The dangerous goods step shows a red block and export of
  transport documents is refused; carriage is only possible with an exemption from the
  competent authority.
- Explanation for articles containing dangerous goods (UN 3537 through 3548) about
  labelling under 5.2.2.1.12.

### Fixed

- **German source data leaked into forms.** For prohibited substances, ADR Table A fills
  *every* column with the text "BEFÖRDERUNG VERBOTEN". That ended up in the packing group,
  the limited quantity, and even the description line of the transport document
  (`UN 1798, NITROHYDROCHLORIC ACID, 8, BEFÖRDERUNG VERBOTEN`). All columns are now
  filtered; the prohibition is shown only as a warning.
- The EmS fallback did not account for the division: gases got no indication on the basis
  of class "2". The division from the labels column is now used first (2.1 → F-D/S-U,
  2.2 → F-C/S-V, 2.3 → F-C/S-U), so nearly every UN number gets a usable emergency
  schedule.

### Known limitation

The EmS data is a curated compilation: nine entries were checked against public sources
while compiling and marked as such; the rest follow the substance's hazard profile. For
UN numbers without an exact entry, the app shows an indicative class default, presented
recognisably as a suggestion and not filled in automatically. The current IMDG edition
remains the authority.

## [1.8.0] — 2026-08-01

Dangerous goods: automatic completion per transport mode, and sea segregation.

### Added

- **Automatic completion of dangerous goods data** (`POST /api/dg/prepare`): you enter
  only the UN number per package (or search by substance name) and EMCargo derives the
  proper shipping name, class, subsidiary risks, packing group, packing instruction,
  transport category, tunnel code, Kemler number and LQ/EQ limits. Number of packages,
  packaging type and masses are taken from the packages already entered. Only empty fields
  are filled, so manual corrections always survive.
- **EmS emergency schedules for sea transport**: the EmS code (fire and spillage schedule)
  is filled in per UN number for a curated selection of commonly carried substances from
  the IMDG Dangerous Goods List; for other substances an indicative class default is shown
  and marked as such.
- **Air freight rules**: lithium batteries UN 3090/3480 are automatically marked **Cargo
  Aircraft Only** with the correct IATA packing instruction (PI 965/968), UN 3091/3481 get
  PI 966/967 and 969/970 respectively, and class 2.3 (toxic gases) is reported as
  forbidden in aviation.
- **Official description lines per form** are assembled automatically and shown before
  export: ADR/RID/ADN under 5.4.1.1.1 including tunnel code, number of packages and total
  quantity; IMDG with EmS code and marine pollutant; IATA with packing instruction and
  Cargo Aircraft Only.
- **Total quantity per transport category** (ADR 5.4.1.1.1.1) is calculated and placed on
  the generated ADR/RID/ADN documents — mandatory when using the 1.1.3.6 exemption, and
  until now manual work.
- **IMDG segregation check (7.2.4)**: the full class segregation table is included, with
  codes 1 through 4 ("away from", "separated from", "separated by a complete compartment
  or hold", "separated longitudinally") and their distances. Subsidiary risks count; for
  sea freight, conflicts appear in the compliance panel.
- **Excepted and limited quantities** are explained in plain language (E1 through E5 with
  the maxima per inner and outer packaging under 3.5.1.2, and the LQ limit per inner
  packaging under 3.4).
- **Class-specific document requirements** are named: net explosive mass and compatibility
  groups for class 1, temperature control for self-reactive substances and organic
  peroxides, the responsible person for class 6.2, and radionuclides, package category,
  transport index and criticality safety index for class 7. Sea freight gets the container
  packing certificate, air freight the signature in duplicate.
- **Versioning policy** written down explicitly: patch releases for corrections, minor for
  new functionality, major only for major overhauls.

### Fixed

- **The ADR classification code was wrongly entered as a subsidiary risk.** When choosing
  a UN number, the classification code (for example `F1` for gasoline, `M4` for lithium
  batteries or `C1` for sulphuric acid) ended up in the "subsidiary risk" field, so the
  description on the transport document read `UN 1203, GASOLINE, 3 (F1), II` instead of
  `UN 1203, GASOLINE, 3, II`. Subsidiary risks are now read correctly from the labels
  column of ADR Table A: UN 2031 (nitric acid) now correctly yields `8 (5.1)`, and
  gasoline no longer yields a subsidiary risk. The classification code is stored
  separately.
- **The division of gases and explosives** is now determined correctly: ADR Table A lists
  only class "2" for gases and "1" for explosives, while the actual division sits in the
  labels column (2.1/2.2/2.3) or the classification code (1.4S). This drives loading
  compatibility and segregation, which could previously be incomplete.
- The IATA description showed the ADR packing instruction (P001, IBC02), which is not
  valid for air freight; an IATA packing instruction is now shown only where one is known.
- The button to download a document was still labelled **"Download Excel"** while all
  documents are exported as PDF; it now reads "Download document".
- Two missing translation keys showed raw text in the interface: the paste field in the
  import dialog had no placeholder, and inactive equipment showed `questions.no` (a
  leftover from the removed internal form) instead of "Inactive".
- The explanation on the dangerous goods step still described the old approach (fill in
  everything by hand, UN data online only) and has been brought in line with automatic
  completion from the offline database.

## [1.7.0] — 2026-07-31

Goods database extended to 400 transport goods.

### Added

- **Goods database extended from 159 to 400 goods** with bulk and solid densities,
  min/max ranges and Dutch/English aliases, across the whole transport spectrum:
  - **Construction and natural stone**: basalt, bluestone, travertine, quartzite,
    porphyry, track ballast, screed mortar, tile adhesive, concrete blocks, kerbstones,
    paving bricks, gypsum plaster, silver sand, dolomite, chalk, loam, roofing rolls,
    bagged cement, wet ready-mix concrete, rubble stone
  - **Insulation**: perlite, vermiculite, foam glass, wood fibre board, cellulose blow-in
  - **Metals**: pure iron, chromium, manganese, tungsten, molybdenum, cobalt, silver,
    gold, platinum, antimony, cadmium, bismuth, silicon, zamak, cemented carbide
    (tungsten carbide), mercury, ferrosilicon
  - **Timber and sheet material**: pine, poplar, alder, maple, walnut, cherry, hornbeam,
    elm, chestnut, lime, iroko, sapele, bangkirai, padauk, wengé, accoya, western red
    cedar, robinia, thermally modified wood, OSB, MDF, HDF, hardboard, softboard, glulam,
    cross-laminated timber (CLT), cork, round timber
  - **Fuels, chemicals and gases**: crude oil, naphtha, heating oil, biodiesel (FAME),
    HVO, solvents (toluene, xylene, benzene, styrene, MEK, IPA, ethyl acetate, white
    spirit/turpentine), acids (acetic, nitric, phosphoric), hydrogen peroxide, ammonia
    solution, glycerine, vegetable oils by type (olive, palm, sunflower, rapeseed,
    linseed), bitumen emulsion, spirits, and liquefied gases (LNG, propane, butane, CO₂,
    nitrogen, oxygen, argon, hydrogen, anhydrous ammonia)
  - **Fertilisers and solid chemicals**: ammonium nitrate, ammonium sulphate, DAP/MAP/TSP,
    kieserite, UAN, calcium chloride, citric acid, washing powder, activated carbon,
    carbon black, titanium dioxide, zinc oxide, starch, vacuum salt, sodium bicarbonate,
    paraffin, bleach lye, iron chloride, epoxy resin
  - **Agricultural**: spelt, buckwheat, millet, sorghum, quinoa, linseed, pulses (peas,
    beans, lentils, chickpeas), feed materials (soybean meal, rapeseed meal, sunflower
    meal, palm kernel expeller, beet pulp pellets, DDGS, alfalfa pellets, fish meal),
    silage, slurry and solid manure, compost, tree bark, wood shavings, potting soil,
    grass seed, mustard and sesame seed, peanuts, hop pellets, tobacco and tea
  - **Fruit and vegetables** (effective density in crates and boxes): bananas, oranges,
    lemons, pears, grapes, melons, strawberries, tomatoes, cucumbers, peppers, leeks,
    cauliflower, cabbage, carrots, mushrooms
  - **Foodstuffs**: table salt, pasta, oats, milk and whey powder, butter, cheese, honey,
    chocolate, cocoa butter, roasted coffee, bottled water, sugar syrup, vinegar
  - **Ores and energy**: copper and zinc concentrate, chrome ore, manganese ore, nickel
    ore, phosphate rock, ilmenite, barite, bentonite, kaolin, feldspar, olivine, rock
    salt, petroleum coke, lignite, anthracite, alumina, slaked lime
  - **Plastics, paper and textiles**: solid polystyrene, ABS, polycarbonate, PET, PTFE,
    PUR foam, rubber granulate, copy paper, newsprint, tissue, books, wool, flax and
    carpet goods, clothing
  - **Waste and recycling**: RDF bales, e-waste, incinerator bottom ash, green waste,
    sewage sludge, used cooking oil, mixed plastic waste
  - **General cargo practical averages**: empty pallets and crates, machinery on skids,
    white goods, lead-acid batteries, cable drums, sanitary ware, fasteners, mattresses,
    bicycles
- Every entry states whether the figure is a bulk density, solid density, liquid density
  or an effective pallet density

### Changed

- Overly broad aliases have been moved to more specific goods (for example "olive oil"
  from generic vegetable oil to olive oil, "potting soil" from peat to potting soil,
  "slaked lime" from quicklime to lime hydrate), so recognition and density are more
  accurate
- All aliases are guaranteed unique across the whole database, so a description always
  resolves to exactly one entry
- Existing installations pick up the new goods automatically at the next catalogue sync,
  which by default runs at startup

## [1.6.0] — 2026-07-25

Signatures on documents, and a complete offline UN and packaging database.

### Added

- **Draw, upload or skip a signature**: on the shipment details step the sender can draw
  a signature (mouse, finger or stylus, with smooth lines, undo and clear) or upload an
  image (PNG/JPEG/WebP; a white background is made transparent automatically and the
  signature is trimmed tightly). The signature is placed in the sender's box of the
  documents: CMR box 22 (all four copies), the signature field of the IATA Shipper's
  Declaration, and a proper signature section on all generated PDFs. Skipping remains
  possible at all times, to sign physically with a pen. Carrier and consignee signatures
  (CMR boxes 23/24, CIM box 61, delivery note receipt) always stay blank.
- **UN number autocomplete**: when entering a UN number or substance name, suggestions
  appear straight away from an **offline database of 2,928 ADR entries** (class,
  classification code, packing group, labels, limited and excepted quantities, packing
  instructions, transport category, tunnel code and Kemler number from ADR Table A;
  English substance names from the official US 49 CFR 172.101 table). One click fills the
  proper shipping name, class, packing group, packing instruction, transport category and
  tunnel code; where internet is available, the existing ADR 2025 lookup enriches the data
  live. New endpoint: `GET /api/dg/search`.
- **Packaging database**: all 107 UN packaging codes under ADR 6.1.2/6.5.1.4/6.6.2 (drums,
  jerricans, boxes, bags, composite packagings with plastic or glass inner receptacles,
  metal, flexible, plastic and composite IBCs such as big bags and 1000-litre totes, large
  packagings and pressure receptacles) with Dutch/English descriptions and a liquid/solid
  indication. The packaging field on the dangerous goods step is now a searchable list;
  free text remains possible. New endpoint: `GET /api/dg/packagings`.
- The UN lookup (`GET /api/dg/lookup`) falls back to the offline database automatically
  when the external ADR source is unreachable — the dangerous goods step now works fully
  offline.

### Changed

- Form texts clarified: carrier and consignee signatures are never pre-filled; the
  sender's signature is only placed when the user draws or uploads one.

## [1.5.0] — 2026-07-25

One wizard for all forms, location and address autocomplete, and a transport-wide goods
database.

### Added

- **Forms sub-wizard**: after entering packages there is one continuous wizard — first the
  **shipment details** (parties, route, references) which are entered once and reused in
  *all* selected forms, then a step per form ("Form x of y") with only the fields that
  form still needs. Steps are directly clickable and show a green or orange dot for
  whether all required fields are filled; forms without their own fields are listed as
  "covered by the shipment details".
- **Address autocomplete**: address fields (sender, consignee) can search and fill an
  address automatically via a Photon geocoder on OpenStreetMap data (configurable with
  `GEO_ADDRESS_API_URL`; goes quiet without internet access, manual entry always remains
  possible). New endpoint: `GET /api/geo/address`.
- **Location autocomplete for airports, ports and railway stations**: route fields (place
  of loading, place of discharge, receipt/delivery, final destination) search live in
  bundled open datasets — 4,500+ airports with IATA/ICAO code (OurAirports), 17,500+ ports
  with UN/LOCODE (UNECE) and 750+ European main stations (Trainline EU). The right kind is
  suggested per mode (air → airports, sea and inland waterway → ports, rail → stations,
  road and multimodal → everything plus addresses). New endpoint: `GET /api/geo/locations`.
  Free text remains allowed at all times.
- **Goods database greatly extended**: from 18 to **159 goods** with bulk and solid
  densities and Dutch/English aliases — construction materials (cement, sand-lime brick,
  brick, roof tiles, natural stone, asphalt, aggregates, insulation), metals and scrap,
  timber species and timber products, fuels and liquids (diesel, kerosene, lubricating
  oil, acids, AdBlue), chemicals and fertilisers, agricultural bulk (grain, seed,
  potatoes, animal feed, hay and straw, coffee, cocoa), foodstuffs and drinks, paper and
  packaging, ores and energy (iron ore, coal, coke), recycling and waste streams, textiles
  and general cargo practical averages (pallets, parcels, furniture).
- Catalogue search now also shows goods directly as a **material suggestion with density**
  (for example "Wheat — 780 kg/m³"), alongside the existing profile and equipment results.
- **Weight calculation for block-shaped goods**: a recognised material with three
  dimensions is now calculated as a solid block on density (for example "brick
  100x100x100cm" → 1,900 kg), even without an explicit product type such as sheet or beam.

### Changed

- The "Shipment details" step keeps its name in the progress bar but now contains the
  sub-wizard with its own navigation; duplicate entry of the same data across forms is
  gone entirely.
- New environment variables: `GEO_ADDRESS_API_URL` and `GEO_ADDRESS_TIMEOUT_SECONDS`.

## [1.4.0] — 2026-07-13

EMCargo is fully civilian: military forms removed.

### Removed

- The internal military form has been removed completely: the wizard step with its
  questions, the Excel template, the export endpoints, the PDF rendering and all
  references in the interface. Military use gets a separate private fork (EMCargo MIL)
  with its own forms.
- Military flags and help texts (weapons, ammunition, ITAR, TBB) and external references
  to defence portals
- Older Docker images still contain the form; these are removed through the Docker Hub tag
  cleanup

### Changed

- **Package entry**: the "Review" step is now called **Packages**; each package can be
  ticked as containing dangerous goods. A tick (or a recognised UN number) automatically
  brings up the dangerous goods step.
- The dangerous goods step, UN detection, ADR/IATA compliance checks and all transport
  documents are fully retained
- Per mode, the primary transport document is pre-selected (road: CMR, rail: CIM, air: AWB
  instructions, sea: B/L instructions)

## [1.3.0] — 2026-07-13

Dangerous goods compliance guidance (ADR and IATA).

### Added

- **ADR 1.1.3.6 points calculator (the 1,000-point rule)**: transport category (0–4) and
  total quantity per DG product; automatic calculation with factors ×50/×3/×1/×0, verdicts
  "exemption possible", "over 1,000 points", "category 0 — no exemption" and "incomplete",
  including an explanation of what the exemption releases you from and what remains
  mandatory
- **Loading compatibility check ADR 7.5.2**: warning for class 1 (other than 1.4S)
  together with other classes, different compatibility groups within class 1 (7.5.2.2) and
  the CV28/7.5.4 separation of foodstuffs (labels 6.1/6.2 and class 9 UN
  2212/2315/2590/3151/3152/3245)
- **IATA segregation (Table 9.3.A)**: check on incompatible packages (class 1 excluding
  1.4S × 2.1/3/4.1/5.1; class 8 × 4.3) including subsidiary risks, plus the lithium
  battery rule (UN 3090/3480 separated from 1/2.1/3/4.1/5.1)
- **IATA Q value (5.0.2.11)**: automatic calculation of Q = Σ n/M, rounded up to one
  decimal, with a warning above 1.0
- **Compliance panel** on the dangerous goods step and in the export summary, with source
  references (ADR 2025, IATA DGR 67th edition) and a recalculate button
- New DG fields with help text: ADR transport category, total quantity (1.1.3.6.3 units),
  net per packaging and max. net per packaging (Q); the UN lookup fills the transport
  category where the ADR database provides it
- Cargo Aircraft Only flagging towards the Shipper's Declaration and AWB handling
  information
- New endpoint: `POST /api/dg/compliance`; rule configuration in
  `backend/app/config/dg_compliance.json`

## [1.2.0] — 2026-07-12

Multimodal transport selection.

### Added

- **Transport mode selection at the start**: a tile screen with road, rail, sea, inland
  waterway, air and multimodal (separate illustrations for light and dark theme)
- **Form selection as the first wizard step**: only relevant forms per mode; with
  multimodal, all forms selectable
- **Document registry** (`backend/app/config/document_registry.json`) with field
  definitions and field statuses (`USER_REQUIRED`, `CONDITIONAL`, `CARRIER_PROVIDED`,
  `OPERATIONAL`, `SIGNATURE_REQUIRED`, …)
- **All documents are now downloaded as PDF.**
- **Official fillable PDF forms filled in**: the **CMR consignment note** (IRU model 2007,
  4 copies), the **IATA Shipper's Declaration** (open format) and the **CIM consignment
  note** (CIT CIM/CUV, 2019 edition) are filled in as the original, fillable PDF templates
  — including correct box numbering, IATA column order and "delete non-applicable"
  strikethrough. Signature fields stay blank.
- **Self-designed documents as clean PDFs** (reportlab): packing list, delivery note, IMO
  Multimodal Dangerous Goods Form, VGM declaration, AWB/B-L Shipping Instructions and the
  ADR/ADN transport document — with parties, goods table, DG table per profile, fixed legal
  texts and a disclaimer.
- **New documents**: CMR (PDF), IATA (PDF), CIM (PDF), IMO Multimodal DG Form, VGM
  declaration (method 1/2 with a total cross-check), AWB Shipping Instructions, B/L or Sea
  Waybill Shipping Instructions, ADR/ADN transport document, packing list and delivery note
- **Legal disclaimer**: a separate disclaimer page in the app (NL/EN), `DISCLAIMER.md`, a
  draft warning on export and a disclaimer in the metadata and footer of generated
  documents. Liability fully excluded; Apache License 2.0 with Commons Clause named
  explicitly.
- Official regulations and fixed legal texts (CMR paramount clause, IATA
  certification/WARNING, IMO declaration, VGM SOLAS reference, ADR 5.4.1 description line)
  plus links to the official source templates per document
- **Shipment details step**: shared blocks (parties, route, references) are entered once
  and reused in all selected documents
- **Document statuses in the summary**: ready for export, draft, waiting for carrier data,
  blocked by safety validation, not applicable
- **Dangerous goods validation per mode** (ADR/RID/ADN/IMDG/IATA DGR): export of DG
  declarations is blocked on incomplete classification (UN number, proper shipping name,
  class; for IATA also packing instruction, packages and quantity)
- Extra DG fields on IMO/IATA forms: technical name, marine pollutant, Cargo Aircraft Only,
  overpack, emergency contact, EmS code
- New API endpoints: `GET /api/documents/registry`, `POST /api/documents/validate`,
  `POST /api/documents/export`

### Changed

- The wizard starts with the form selection
- Signature, carrier and operational fields are never pre-filled; they are marked as such
  in the export
- Navigation: the starting point is called "New shipment" and begins at the mode selection
- The wizard progress bar shows icons instead of text on mobile (more steps fit on screen)

## [1.0.0] — 2026-07-11

First stable release.

### Added

- Wizard: review-first flow with a material catalogue and synonyms
- Dangerous goods with ADR UN lookup
- Equipment overview: management, import via template (.xlsx/.csv/.txt)
- Wizard import: paste and file upload with a template
- Weight per line editable; total weight proportionally scalable in the summary
- Automatic catalogue sync (materials, profiles) from public sources
- Dark mode, NL/EN interface, Docker and Unraid deployment

### Changed

- Semantic versions from v1.0.0 onwards (`VERSION`, Docker tags `v*`, health endpoint)
- The equipment library starts **empty**; no pre-filled operational data in the repository
  or the image

### Removed / privacy

- Pre-filled equipment list (`equipment_overview.json`) removed from the codebase and the
  Docker build
- On startup, legacy items with the source `overzicht_materieel` are removed from existing
  databases
- Stale built frontend assets in `backend/static/` (the build happens in Docker)
