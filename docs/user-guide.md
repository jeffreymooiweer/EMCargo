# User guide

A walk through EMCargo, from opening the app to downloading your paperwork. The whole
flow is one wizard; you can go back to any earlier step at any time.

- [1. Pick a transport mode](#1-pick-a-transport-mode)
- [2. Enter your packages](#2-enter-your-packages)
- [3. Dangerous goods](#3-dangerous-goods-only-if-needed)
- [4. Shipment details](#4-shipment-details)
- [5. Export and your documents](#5-export-and-your-documents)
- [The AI assistant](#the-ai-assistant)
- [The equipment library](#the-equipment-library)
- [Settings](#settings)
- [Language](#language)
- [Tips](#tips)

## Overview and navigation

The desktop sidebar provides the overview, new shipment, shipments, trips, library
and administration. On smaller screens, open the menu in the top bar. Availability
of account and history features depends on the retention setting and your role.

The overview lets you resume a draft, search recent shipments or start directly by
pasting an Excel list. Counts and document availability come from actual saved data.

The shipment header shows three stages: goods, shipment details and documents.
Dangerous-goods questions are part of the goods stage and remain mandatory when
applicable; the sections below explain these tasks separately. The desktop summary
shows totals beside the goods. The bottom action bar contains the next action and
**Save and close**; failed saves stay visible so you can retry without losing input.

New installations use the dark theme. Existing explicit theme choices are preserved.

## 1. Pick a transport mode

Click **New shipment** and choose how the goods travel. **Road, rail, sea and inland
waterway are selectable**. Air and multimodal appear alongside them with a
short **In development** label and cannot be selected.
The [roadmap](../ROADMAP.md) tracks when each one unlocks.

This choice decides which documents are offered, which rulebook applies to any dangerous
goods (ADR for road, RID for rail, IMDG for sea, ADN for inland waterway, IATA DGR for
air), and which kind of locations the route fields suggest.

Always ship the same way? Set a fixed transport mode under [Settings](#settings) and
EMCargo opens straight into it; *change transport mode* at the top of the wizard brings
the tiles back.

You do not choose forms here. EMCargo assembles the document set from the shipment
itself and shows the advice on the [export step](#5-export-and-your-documents), where you
can still adjust it.

## 2. Enter your packages

Three ways to get your load in:

**Type it.** Each line carries its description, its quantity and its unit as fields you
type in directly; the catalogue searches while you type the description. **Enter** makes
the next line, so a list can be typed without touching the mouse. What EMCargo works
out — the weight, the measurements, the volume — appears under the line as you go.
Dimensions you want to set yourself, the packaging, the wall thickness and your own
weights are under **Details** on the line.

**Paste it.** Click **Paste from Excel** on the goods step and paste. One line per row:

```
Steel angle 80x80x8x6000 | 8 | pieces
Euro pallet with bricks   | 12 | pallets
```

Columns are separated by a pipe (`|`) or a tab, in the order
`description | quantity | unit`.

**Upload a file.** **Choose a file** takes `.xlsx`, `.csv` or `.txt`, and the goods panel
takes a file dropped on it. **Download template** next to it gives you the exact layout if
you want it.

Your file rarely has the template's layout, and it does not have to. EMCargo reads the
header row and works out which column is which. When it recognises the names there is
nothing to ask and the lines simply go in; when it does not, it guesses by position,
**tells you it guessed** in an amber panel, and waits for you to look before importing
anything. Each dropdown shows what is actually in that column — `2. Benaming ·
Stalen hoekprofiel 80x80x8x6000` rather than "column 2" — so you can see at a glance
whether it picked the right one.

Two things worth knowing there. A column you do not need can be left unmapped. And if
your file starts with a header row that EMCargo did not recognise, tick **first row is
a header**, or that row is imported as a piece of cargo.

**Adding or replacing.** With nothing in the shipment yet there is nothing to replace, so
you are not asked: the lines go in. Once there are lines, both **Add** and **Replace** are
offered by name, and whichever you pick can be taken back from the snackbar that follows —
which is what makes replacing safe to offer at all.

### What happens next

EMCargo reads each line and tries to recognise the material and any dimensions in it,
in Dutch, English, German or French. `Steel angle 80x80x8x6000` becomes steel, 80 × 80 × 8 mm,
6000 mm long, and so does `Stahl Winkelprofil 80x80x8x6000`. From there it calculates the weight, the material volume and the transport volume.

A green line means it worked. An orange or red line means it could not work out the
weight — usually because the description has no dimensions — and says which of those it
was. Type the weight in yourself under **Details** and carry on; nothing blocks you.

Above the list you get the count: *49 settled · 1 wants attention*, with a button that
narrows the list to those. On fifty imported lines that is the difference between finding
the one that needs you and scrolling for it.

While a line is being recalculated it keeps its previous figures, greyed out and marked
*to be rechecked* — except the line you are actually changing, which shows no figures at
all until they have been worked out for what it says now. Nothing on that screen shows a
number for something it was not computed from.

You can adjust any weight by hand under **Details**, and scale the total proportionally
from the summary if you know the real weighbridge figure.

### Dangerous goods on a line

Tick **Dangerous goods** under **Details** on any package that contains them. EMCargo
also spots UN numbers written in a description (`UN 1203`) and ticks the box for you.

And it recognises substances by name. Type `petrol` or `benzine` and the line asks you,
underneath itself: *this looks like UN 1203, PETROL (class 3) — is that right?* Three
answers, and you have to give one of them:

- **Take UN 1203** — the line is dangerous goods and the number travels to the dangerous
  goods step.
- **A different substance** — the line is dangerous goods, but not that one; you fill in
  which at the dangerous goods step.
- **This suggestion is wrong** — this substance is not it. That is *all* it says: it is
  not a finding that the goods are harmless, and it leaves your own tick alone.

The line then says which of the three you answered, with **Change the answer** beside it,
so a decision can be found again and revised. Until you answer, the goods step counts the
question above the list and the export step says so too — an unanswered question is not
an answer, and it is exactly what a document check is for.

Either way, a dangerous goods step appears after this one.

The contents of one package are read from the sentence too: `1000 jerricans of 25 l of
petrol` fills the net quantity per package and computes the totals, for jerricans,
drums, IBCs and any other counted package alike.

### Articles from your own library

On an installation that keeps its shipments, the line dialog carries an **Article from the
library** field: pick one of your own article codes and the line takes its name, is
flagged as dangerous goods when the article carries a UN number, and hands the dangerous
goods step what the library knows — the UN number, the proper shipping name, the packing
group, the type of package and the content per package — so nothing is typed twice. The
**Articles** page in the menu is where the library is kept: one article per code, with a
spreadsheet template, an export and an import in the same columns.

## 3. Dangerous goods (only if needed)

Enter the **UN number**, confirm the chip from the previous step, or search by
substance name. That is usually all you need to type.

From that one number EMCargo works out the proper shipping name, the class and
division, subsidiary risks, packing group, packing instruction, transport category,
tunnel code, Kemler number, limited and excepted quantity limits, the EmS emergency
schedules for sea transport and the air freight rules. Quantities, packaging type and
masses come from the packages you already entered.

**Only empty fields are filled.** Anything you typed yourself stays exactly as you left
it.

**Only the genuinely open questions are asked.** Everything the tables can supply is
shown as an answer, not a question; what remains is the short list of facts only you
know — how it travels (packages, tank, bulk), which of several official names fits your
product, the kind of packaging (steel 3A1 against plastic 3H1) — each with the reason
it is asked.

Below the form, the **compliance panel** shows live warnings: the ADR 1,000-point
calculation, loading incompatibilities, sea segregation conflicts, the IATA Q value.
Fill in the **net quantity per inner packaging** (with a unit, such as `500 g` or
`0.5 L`) and it also compares your quantities against the limited and excepted quantity
limits of chapters 3.4 and 3.5 — telling you per line whether it falls within or
outside those limits, or that it needs more input. Some findings are warnings you can
proceed past; a few — an incomplete classification, or a substance that is not
permitted for carriage at all — will block the export until resolved.

[Dangerous goods](dangerous-goods.md) explains all of it in detail.

**Say how it travels.** Next to the unit sits a **form**: solid, sheets, bundled, stacked
or loose bulk. It decides how much of a cubic metre is actually material, so 20 m³ of oak
is 14,400 kg as beams and 6,480 kg tipped loose. For gravel, grain and liquids the field
shows a dash — their density already describes them as they travel, and applying a second
factor would count the air twice.

**A profile needs its wall thickness.** An angle profile of 80 × 80 is two legs a few
millimetres thick, not a solid 80 × 80 bar — the difference is a factor of five. So for an
angle profile, a square tube or a round tube a fourth field appears: **wall thickness in
mm**. Leave it empty and the line reports that the thickness is missing rather than
producing a weight; a plate, a beam or a plank does not show the field at all, because
three measurements already describe them.

**A round section needs no height.** For a pipe or a round bar the width column *is* the
diameter and the height field shows a dash: a diameter, a length and — for a pipe — a wall
thickness fix the weight completely.

**The weight recalculates by itself.** There is no recalculate button any more. Change a
quantity, a unit, a form or a dimension and the figures follow shortly after you stop
typing.

**Dimensions belong in their own columns.** Length, width and height are fields on the
line, so a description no longer has to read `balk 200x200x3000` for the measurements to
count. Anything recognised in the description still fills in as a placeholder; what you
type wins. On a phone the three fields sit behind **view more**, with quantity and unit on
the collapsed card.

## 4. Shipment details

This is where you enter the shipment **once**:

- **Parties** — sender, consignee, carrier
- **Route** — place of loading, place of delivery, terminals
- **References** — order numbers, booking references, customs references. Two of them
  carry a condition rather than a rule, and the route decides it: the **ENS reference
  (ICS2)** for goods entering the EU customs territory (the entry summary declaration is
  normally lodged by the carrier; when its MRN is known, it travels on the papers) and
  the **AES ITN** for exports from the United States (the proof of the Electronic Export
  Information filing, which belongs on the transport document). Once the route is filled
  in, each field says whether it **applies on this route**, does not, or is exempt — and
  on what ground: goods from China discharged in Rotterdam enter the ICS2 area (the EU
  customs territory with Northern Ireland, Norway and Switzerland); goods into Great
  Britain from anywhere, the EU included, need HMRC's own entry summary declaration in the
  Safety and Security GB service; a load from Detroit to Toronto is exempt under 15 CFR
  30.36, while the same load from San Juan is not; a movement within the area needs
  neither. A route
  the application cannot place — free text without a country in it — gets no verdict, and
  the condition stays in the help text as before. An applicable reference left empty is
  a warning on the export, never a refusal. Both fields check their format on export, so
  a mistyped reference is caught before it reaches an official form.

The carrier's numbers usually arrive **after** you book — in the confirmation e-mail.
**Paste booking confirmation** at the top of this step reads that e-mail for the
recognisable references (AWB number with its own check digit, booking number, ENS MRN,
AES ITN) and puts them only into fields that are still empty. Nothing you typed is ever
overwritten, and the pasted text is read once and stored nowhere.

Address fields search real addresses as you type. Route fields suggest airports, ports
or railway stations, filtered to your transport mode. You can always type your own text.

**Rail: the NHM code (CIM box 24).** The UIC's goods nomenclature is behind the box: type
the start of a code (`7208 5`) or a word of the English or French description
(`flat-rolled`, `pétrole`) and pick from the list, or type the six digits you know — the
description is read back under the box either way. The list is the NHM 2025 with 5,640
six-digit codes; labels exist in English and French because that is what the UIC
publishes.

You can also **draw or upload your signature** here, or skip it and sign on paper. Your
signature goes in the sender's box only — carrier and consignee signatures are always
left blank.

After the shared details, each selected form gets its own small step ("Form 3 of 5")
with only the fields that form still needs. A green dot means that form is complete, an
orange dot means something required is still missing. Forms that need nothing extra are
listed as *covered by the shipment details*.

Dates that mean "drawn up today" start as today; operational dates (loading, requested
departure) are facts of the trip and are never guessed. The details of your previous
shipment can be brought back with one click, so a regular route is not retyped.

On an installation that keeps its shipments (see [Shipments](#shipments-the-history-where-the-installation-keeps-one)),
the parties section carries an **address book** shared by everyone: pick a consignor,
consignee or carrier from it and their name, address and contact are filled in; **Save**
next to a party puts what you typed into the book under that name. Saving a name that is
already there brings the entry up to date rather than adding a second one. The carrier's
one "name and address" field is saved with its first line as the name.

## 5. Export and your documents

The final screen assembles your document set and lists every document with its status.
The **advice** does the choosing for you: the documents the rules require come first
(the dangerous goods transport document for your mode, for instance), the customary
ones are recommended, and everything else the mode offers is there to add. Tick and
untick as you like — the advice is a starting point, not a lock.

| Status | Meaning |
|---|---|
| **Ready** | All required fields are filled |
| **Draft** | Exportable, but some optional fields are still empty |
| **Waiting for carrier data** | Fields only the carrier can supply are missing |
| **Blocked** | A safety check failed — see the compliance panel |

For dangerous goods, first choose **Submit for review**. A DG Specialist reviews
the submitted version and releases it or requests changes with a comment. The
status appears here and on **DG review**; changing document inputs requires a
new review. Downloads, mail and completed shipment saving remain blocked until
release, unless an administrator disabled the requirement. Submitted versions
are stored separately from optional history. See [DG review and roles](dg-review.md).

Click **Download document** for each one, or **Download all as ZIP** for one archive
holding every document that is ready — and, when the shipment carries dangerous goods,
the UN cards and the instructions in writing for the journey's regimes as well.
Anything the server has to leave out (an incomplete document, a UN card it does not
hold) is named in a README inside the archive rather than silently missing. Every
document downloads as a PDF and carries a draft notice. Two entries in the list are not
paper: the **Structured export (JSON)**, the whole shipment as data with what EMCargo
derived (see [The structured shipment export](shipment-export.md)), and — for a shipment
with dangerous goods — the **Dangerous goods notification (UN/EDIFACT IFTDGN)**, the EDI
message a port community system or a forwarder's gateway reads, as an `.edi` file (see
[The IFTDGN notification](iftdgn.md)). Both go into the ZIP with the rest.

**Mail them instead of downloading.** Where your administrator has set up a mail
server, the same set can be sent straight from this screen: fill in the address, add a
covering note if you want one, and the documents travel as attachments. The message is
written in the language the papers are drawn up in, so a German consignee reads German.

> Documents are generated on the spot and deleted from the server the moment your
> download finishes. Nothing is archived.

### UN cards

If your shipment contains dangerous goods, you can also download the **UN cards** for the
substances you declared — a zip with one datasheet per UN number **per regime** your
journey touches (ADR for road, ADN for inland waterways, IMDG for sea), for your own
records. Only your substances are included, not the whole library, and a regime for
which no card exists is named as missing rather than papered over with another regime's
card. They are not part of the transport documentation.

The card set itself is not bundled with the application: an administrator installs it
once under **Settings → UN Cards**, either straight from the EMCargo releases or from
an uploaded ZIP (see [un-cards.md](un-cards.md)). Until then the wizard simply says no
cards are available.

## The AI assistant

The compass button in the wizard header opens the shipment assistant. Describe
what you are sending, how much and where to. For example:

`4 pallets of machine parts from Rotterdam to Duisburg; sender: Example Ltd; receiver: Demo GmbH`

This is guided entry, not a chat. The ordinary goods calculation, dangerous goods
preparation and selected document definitions decide what is still needed. One
question is shown at a time, with plain-language help and choices. You can also
answer in your own words. Explicit labels let one answer supply several facts,
such as `Sender: Example Ltd; receiver: Demo GmbH`. A route answer can fill both
endpoints. Corrections can name a field or use **Edit** in the shipment summary.

The summary shows what has actually been recorded, with calculated weights
labelled separately. If a weight could mean a total or a weight per item, the
assistant asks which. Missing counts, uncertain measurements, invalid dates and
unrecognised answers stay open. Your typed answer remains available to correct;
the assistant does not silently advance or turn “I don't know” into a field value.
A required question cannot be skipped. Additional details can be left for later;
optional document fields are offered as a separate choice after the main questions.

Address and route lookups use the same fields as the ordinary wizard. **Previous**
restores the complete previous draft. You can close the assistant and continue
manually; reopening reads the current wizard data. Late responses from a closed
assistant do not overwrite later work. Questions about quantities and DG facts
remain attached to their goods when rows have been removed or renumbered.

The final screen is a handoff for review in the ordinary wizard, not transport
release. Calculation, document validation, saving and the configured DG Specialist
release still happen through the application's existing workflow.

The assistant requires an installed local model. An administrator installs it
under **Settings → AI assistant**. Until then, continue manually in the wizard.
Once installed, exact readers handle simple counted descriptions, familiar
answers and uncertain replies without a model round trip. Model output must be traceable to the source text;
it cannot supply a missing address, a guessed measurement or a regulatory choice.
A paraphrased choice understood only by the model is shown as a suggestion. It
is recorded only when you explicitly select the intended option.
See the [README](../README.md#the-ai-assistant-optional) for resource requirements.


## Groupage: several consignments on one vehicle

Every other screen asks about *one* consignment. The ADR does not look at your
administration, though — it looks at what is physically on the vehicle, and three of its
rules are decided per transport unit no matter how carefully each consignment was filled
in:

- **The 1.1.3.6 points.** Two consignments that each stay under the 1000 can pass it
  together, and the moment they do the whole load needs orange plates, a driver with an
  ADR certificate and the equipment of 8.1.5. This is the case the screen exists for:
  each customer is told "exempt", truthfully, and the vehicle is not.
- **Mixed loading (7.5.2).** Within one consignment this was always checked. Between two
  consignments from different customers, nobody was checking it.
- **The limited-quantities mark (3.4.13/3.4.14).** Both of its conditions are about the
  unit rather than the consignment.

Open **Groupage** in the menu and add the consignments. They come in as the **JSON
exports** the export step writes for each shipment — on an installation that keeps no
shipment history there is no list to pick from, and the file you already have is the
input. On an installation that keeps its shipments, a second box, **From the history**,
lists the kept shipments you may see that carry dangerous goods; search by reference or
party and add them to the vehicle with one click. Underneath it is the same export.
Rename them to whatever you call them on the floor: those names appear in the warnings,
so "these two may not travel together" tells you which pallet to take off.

One optional field: the **permitted maximum mass of the transport unit** in tonnes.
Provision 3.4.13 only applies above 12 tonnes, and that is the one fact about the load
the app cannot work out for itself. Leave it empty and the limited-quantities marking is
reported as undecided rather than guessed.

**The trip is not stored** on an installation that keeps no shipments. It exists on the
screen and in the request, and reloading clears it — the same promise the rest of the
application keeps about your shipments. On an installation that keeps its shipments, a
box under the assessment offers to **keep the trip**: give it a name — the vehicle, the
route, the date — and press the button. What is kept is what was on the vehicle, the
permitted maximum mass and the judgement as it was given, with the editions it was
computed against. **Trips** in the menu lists them, with the points together and a mark
where the exemption fell away; open one for the judgement as it stood, reopen it on the
groupage page to change the load or assess it again under today's rules, or remove it.
Who sees which trips follows the same department rule as the shipments.

## Shipments: the history, where the installation keeps one

By default EMCargo keeps no shipments: once the papers are downloaded, the shipment is
gone. An administrator can switch a history on under **Settings → Administration → Keep
shipments** (see [Configuration](configuration.md#shipment-history)), and then two things
appear. Switching it off again is refused while kept shipments or trips exist: the screen
names the counts and deletes them on confirmation, and only then goes off.

On the export step, a **History** card. Downloading the documents keeps the shipment; the
card's button keeps it before that, and says when it was last kept. A shipment that was
opened from the history keeps its identity, so keeping it again updates the same entry.

In the menu, **Shipments**: the kept shipments with a search over reference and parties,
a transport-mode filter and a date range — a table on a wide screen, cards on a phone.
Opening one shows the record and offers four things: **Open in wizard** puts the whole
shipment back where it was, on the step it was on; **Use as template** starts a *new*
shipment with the same goods, parties and route, its reference, the carrier's numbers
and every date left empty, so keeping it makes a new entry rather than changing the old
one; **Documents again** renders the same bundle the export step handed out, on the
current version; **Remove** takes it out of the history after a confirmation. The
**Structured export (JSON)** is the same file the export step offers, and it is what the
groupage page accepts.

The **DGSA annual report** button is available to Admin and DG Specialist, and
to Super Users only when an admin enables their report access. It draws the safety adviser's
yearly report of ADR 1.8.3.3 over the kept shipments of one calendar year, within what
you may see: how many shipments, with and without dangerous goods, per month, mode,
regulation and department, per class and per UN number with kilograms and litres kept
apart, what the 1.1.3.6 points count said about each shipment, and which documents were
issued. The duties the ADR gives the adviser are listed as headings with nothing filled
in: that judgement is the adviser's, not the application's. **Download workbook** hands
over the same figures as an `.xlsx` with an empty column beside the duties. A shipment
that was never kept is not in the count, and the report says so.

**Fill in the report** is the second tab: the report in the shape of the DVSA template
(the UK competent authority's *DGSA Annual Report for the Carriage of Dangerous Goods*,
December 2025) — company and adviser details, a risk rating, the executive summary,
activities, incidents, training, high consequence dangerous goods, the transport table
per class with the operations and the quantity band, practices and procedures (the
thirteen duties of 1.8.3.3 as yes/no questions with a details column, plus accident
reports to management and 1.8.5 notifications), a class 7 block that appears only when
class 7 was carried, the DVSA's additional points, and who prepared it. What the history
can propose — the classes and quantities, the method of carriage, the high consequence
goods the 1.10.3 check found, the annual tonnage, the company name from the branding —
sits under a **Take over** button and is never written into an answer by itself. The
answers are kept per year (and per department scope for an administrator), so the report
can be filled in over weeks and found again in five years. **Report as PDF** draws it on
the installation's paper in the template's order, with the adviser's saved signature from
the settings, the counted figures as an appendix and the DGSA1 to DGSA21 checklist last,
each line naming the section of the report that answers it.

Who sees which is a matter of **departments**. Admins, Super Users and DG Specialists see every kept shipment
and get a department filter on the page; other users see their own department's
shipments, and someone without a department sees the ones that belong to none. An
installation that never makes a department keeps the plain rule: everyone sees
everything. Admins and Super Users make departments and assign people on the **Users** page.

## The equipment library

Open **Library → Equipment** to maintain vehicles, machines, containers and other
transport items. The library stores their transport dimensions and weight, asset
numbers, photographs, files and confirmed location history. In a shipment, use
**Choose equipment** to copy the selected item's data; later library edits do not
change that saved selection. Containers can travel empty or carry allocated goods,
with their tare counted once.

It starts **empty on purpose** — no operational data ships with the app. An
admin or Super User adds items directly or imports a completed spreadsheet template.

**Export library** hands the whole list back as a spreadsheet in the very same columns
the import reads, so metadata round-trips for a colleague who maintains the list in
Excel or a second installation. Photos, files and movement history are included in
the database backup, not the spreadsheet. Nothing is exported unless you click.
See [Equipment library](equipment-library.md) for configurations, confirmed transfers,
imports and container document scope.

## Roles and specialist review

The [roles and release guide](dg-review.md) lists every role’s permissions,
review workflow, defaults and storage behaviour. The **DG review** page is
available from the main navigation and overview even when history is disabled.

## Settings

Everything under **Settings** belongs to your account, not to the browser you happen to be
using. Sign in somewhere else and it comes with you.

**Appearance.** Light, dark or follow the system, and the interface language.

**Defaults for a shipment.** If you always ship by the same mode, pick it here and
EMCargo opens straight into it — the transport-mode tiles are still one click away, via
*change transport mode* at the top of the wizard. You can also set the unit a new package
line starts with.

**My details.** The consignor name and address, a contact, your usual carrier, your loading
point, and the 24-hour emergency number that the IMDG Code and the IATA DGR want on a
dangerous goods declaration. These are the fields that are the same on nearly every
consignment, and they are filled in for you on every form that asks for them — only where
the field is still empty, so nothing you typed yourself is ever overwritten. Switch
*Pre-fill my details* off to keep the details without having them applied.

**Signature.** Draw or upload it once and it is ready on every shipment; you can still
replace or remove it per shipment. It is stored on your own server and nowhere else — see
[Privacy](privacy.md#what-is-stored).

**Two-step verification.** Under *Details* you can protect your account with a second
factor: an authenticator app, which scans a QR code, or a code sent to your e-mail
address — whichever suits you, unless your administrator requires one. Setting it up
gives you eight recovery codes; write them down, because they are shown once and each
works only once. They are what gets you back in when the phone is gone. Switching it off
asks for a code first, and if you chose the e-mail method you can have one sent to you
at that moment.

**Forgotten your password?** The sign-in screen has a link. You get a mail with a link
that works once and expires after an hour, and after choosing a new password you are
signed in straight away rather than sent back to the sign-in screen. Both need a mail
server; without one, ask your administrator to set a new password for you.

### After an update

When your administrator pulls a newer EMCargo image, the first sign-in afterwards shows
a **what's new** card with the release notes between the version you last used and the one
now running. Close it and it will not return until the next update; the card follows your
account, so a second device does not show the same notes twice. The notes themselves are
the project's own changelog entries and are in English; a first sign-in on a fresh account
shows no card at all.

### For administrators

Administrators see two more tabs. **Administration** holds the settings that apply to
the whole installation and are saved together: the language and theme new users start
with, the organisation name and address offered as a consignor to anyone who has not
filled in their own, whether the UN card download is offered, how long a session lasts,
and — under **Outbound connections** — whether address lookup, catalogue sync and the
update check are allowed to reach the internet at all. It also holds the **mail server**,
with a test message to prove it works before anyone depends on it, the **web address**
the application is reached on (which the links in those mails use), and the **two-step
verification policy**: off, required for administrators, or required for everyone. See
[Configuration](configuration.md#mail-server) for the settings themselves. Under
**Branding** the installation gets its own face: a name for the header, the sign-in page
and the browser tab, a logo shown in its own colours in both themes and carried in
outgoing mail, and a picture per transport mode for the tiles on the first screen. Both
the name and the logo are printed on every document EMCargo draws itself, in the
header and the foot of every page, and the "generated with" line names the installation
rather than the software; where nothing is set, the documents carry EMCargo's own
name and logo. The official forms (CMR, CIM, AVC) are filled in and not rebranded. The
pictures apply the moment they are uploaded and each has a way back to the default; the
name is saved with the button. See [Configuration](configuration.md#branding) for the
formats and sizes accepted.

**Users.** A separate page lists the accounts, where an administrator adds one, changes
a role, deactivates or removes an account, sets a new password, and clears somebody's
two-step verification when they have lost both their phone and their recovery codes. A
new account can be invited by mail instead of being handed a password: the colleague
gets a link, valid for seven days and usable once, and chooses their own password. The
invitation says an administrator made the account without naming which one. On an
installation that keeps its shipments the same page holds **Departments**: make one,
rename it, remove it — its people and shipments then belong to none rather than
disappearing — and pick a department per user beside their role. **Maintenance** holds the things
an administrator *does* rather than saves: updating, the **UN Cards** section where the
card set is installed, checked for updates or removed (see [un-cards.md](un-cards.md)),
and the local model required to enable the optional assistant. When the update check is on and a newer
release exists, administrators get a small dismissible note in the
corner. The **Updates** panel carries a **check now** button and,
on supported installations with Docker socket access (see
[Configuration](configuration.md#updating-from-inside-the-application)), an **update
and restart** button that pulls the new release and swaps the container — the brief
restart is the update happening, and a failed attempt puts the previous version back.
In-app updates are enabled by default; no environment switch is needed.
Without Docker socket access the section explains the manual route: pulling the newer image and
restarting the container, by hand, with Docker Compose, via Watchtower or from Unraid's
Docker tab. See
[Configuration](configuration.md#two-places-and-which-one-wins) for how these relate to the
environment variables.

**Audit log.** A page of its own, for administrators, that says who did what and when:
who signed in and who was refused, who signed out or changed a password, which accounts
were made, changed or removed, which settings changed (the names of the settings, never
their values — the mail password is among them), which shipments were kept, updated,
reopened for their documents or removed, which documents were downloaded or mailed (the
document keys and how many recipients, never the addresses), and which annual reports
were drawn. Each line carries the account, the moment and the address the request came
from. Filter it by account, by action or by date, page through it, or export the same
selection as CSV for whoever keeps records elsewhere. What a shipment contained — the
parties, the goods, the UN numbers — is never in this log, so it can be kept longer than
the shipments themselves: the **retention** under Administration says how many days a
line stays (365 by default), and whatever is older is removed when the application
starts. Every installation uses accounts and records these actions. See
[Privacy](privacy.md#the-audit-log).

## Language

Under **Settings** you pick Dutch, English, German or French. That choice runs all the way
through: the screens, the field labels, the dangerous goods help, the compliance warnings,
the error messages and the documents you download.

One thing follows the regulations rather than your choice. The proper shipping name of a
dangerous substance is prescribed per mode: a German CMR or CIM may carry the German name
from ADR Table A, but a sea or air document must be in English (IMDG 5.4.1.4.1, IATA DGR
8.1.2.1). EMCargo puts the right one on each document and tells you when it did.
See [Dangerous goods](dangerous-goods.md#what-one-un-number-gives-you).

## Tips

- **Reference numbers in the description.** Anything the parser does not recognise stays
  in the description and ends up on the document, so notes stay visible.
- **Free text always wins.** Every suggestion box also accepts text you type yourself.
  Nothing forces you into a list.
- **Missing a document?** The advice on the export step preselects what the shipment
  needs, but everything the mode offers can be ticked there as well.
- **Working offline?** Packages, weights, UN numbers, ports and airports all work
  without internet. Only address autocomplete needs a connection.
- **Check before you sign.** Every document is a draft. The app is a typing assistant,
  not a safety adviser.
