# Privacy and data storage

EMCargo runs on your own machine or server. There is no EMCargo cloud service, no
account with us, and no telemetry.

## What is stored

Everything persistent lives in the `/data` volume:

| Stored | Why |
|---|---|
| User accounts | Logging in |
| Profile photos users choose to upload | Their account menu and the operational managers’ user directory; stored as a small image without camera metadata, readable only by the owner, Super Users and administrators, and removable under Settings / My details |
| Catalogue reference data | Materials, profiles, locations, UN numbers |
| Catalogue sync status | So startup knows what is current |
| Equipment **you** imported | Your own library |
| Your settings | Language, theme, the details you asked to have filled in for you, and which version's release notes you have already seen |
| The installation's settings | What an administrator set for everyone |
| The installation's branding | A name, a logo and tile pictures an administrator uploaded, in `/data/branding` |
| Kept shipments — **only** with the history switched on | The shipments the organisation chose to keep; see [The shipment history](#the-shipment-history) |
| The address book — **only** with the history switched on | Parties (name, address, contact) somebody pressed **Save** on in the details step, shared by everyone on the installation |
| The articles library — **only** with the history switched on | Your own article codes with the UN number, names, packing group and packaging you gave them, shared by everyone on the installation |
| Submitted DG reviews | The explicitly submitted version, including document inputs and any signature; independent of optional history, visible to its submitter, specialists and admins until removed |
| The safety adviser's annual reports — **only** with the history switched on | The answers an adviser saved on the DGSA report form, one record per year and scope; the figures are recounted from the kept shipments each time |
| The audit log — organisation application only | Who did what and when, as metadata: the action, the account, a reference or a document key, the address the request came from. Never the contents of a shipment; see [The audit log](#the-audit-log) |

That is the whole list.

Settings are stored per account, so they follow you to a second device rather than staying
behind in one browser. They hold what you chose to put there: your consignor name and
address, a contact, a carrier, a loading point, an emergency number — and, if you draw one,
**your signature**. Saving a personal signature keeps it for future forms; removing
it from personal settings does not erase copies already submitted for review or
kept in shipment history. Profile photos and branding images are also stored.
The document signature is included in exports and any mail the user sends.

## What is deliberately not stored

- **No completed shipment history unless enabled.** Explicitly submitted DG
  reviews are a separate exception: they retain the submitted version until the
  submitter or admin deletes it, whether history is on or off.
- **Drafts are autosaved only while history is enabled.** Without history, an
  unsubmitted draft must be downloaded to continue later.
- **No document archive.** Exports are written to a temporary file, streamed to your
  browser and deleted immediately afterwards.
- **No operational equipment data in the repository or the Docker image.** The equipment
  library starts empty; an administrator fills it by importing a template.
- **No trips**, unless an administrator switched the history on. The groupage screen
  assembles several consignments into one load, judges them together and forgets them;
  reloading the page clears it. An organisation application with the history on offers
  to keep the assessed trip beside its shipments — see
  [The shipment history](#the-shipment-history) — and only when somebody presses the
  button.

The operator manages access, backups and retention for all stored data, including
review submissions. Finishing a job does not delete its retained records.

## What leaves your server

Six things, and only if you let them:

**Address autocomplete** sends what you type in an address field to a Photon geocoder
(`photon.komoot.io` by default). An administrator can switch it off entirely on the
settings screen, point `GEO_ADDRESS_API_URL` at their own instance, or you can simply not
use the suggestions — typing by hand always works. The assistant's address questions go
through the very same switch.

**Catalogue sync** fetches public reference data (steel profiles, material densities) at
startup. Switch it off on the settings screen or with `CATALOG_AUTO_SYNC=false`.

**The update check** asks GitHub's public release listing whether a newer EMCargo
exists, only while an administrator is signed in, and sends nothing but the request
itself. Switch it off on the settings screen or with `UPDATE_CHECK_ENABLED=false`;
off means EMCargo never asks. Where the optional update service is configured, an administrator can install
an update from the application; this triggers the separate image download below.

**The assistant's model download** happens once, only when an administrator clicks
*install* on the settings screen: the pinned llama.cpp build and the Qwen3 model file
are fetched into `/data/assistant` and verified against SHA-256 digests recorded in the
repository. Nothing about your shipments is ever sent — the download is the only
traffic, and after it the assistant runs entirely locally. Never installing it is the
default, and the assistant works without it.

**The in-app update** pulls the newer EMCargo image from GHCR, and only
when an administrator confirms an update. This action is enabled by default on
supported installations with a mounted Docker socket; see
[Configuration](configuration.md#updating-from-inside-the-application).
Updates never install automatically; nothing about your shipments travels with the pull.

**The UN card download** happens only when an administrator clicks *check* or
*download* under **Settings → UN Cards**: the server asks GitHub's public release
listing for the newest `un-cards-` release of this repository and, on download, fetches
the card package from it — never from a caller-supplied address. Every file is verified
against the SHA-256 digests in the packaged manifest before it is installed. An
installation without outbound access imports the same package as an uploaded ZIP
instead, with identical verification, so this connection is never required.

The switches sit together under **Outbound connections** in the administrator section of
the settings screen, so an air-gapped installation can be made silent from one place.

Airport, port, station, UN number and packaging lookups are all local. Nothing about
your shipment ever goes anywhere.

## What a stranger can reach

What is on the door, and one thing more if you switch it on.

**The name and the pictures.** The installation's name, its logo and its tile pictures
are readable without a sign-in, because the sign-in page shows them — a door has its
sign on the outside. They are what an administrator chose to put there and nothing else.

**The QR code on transport documents** (**Settings → QR code with UN cards on
documents**, off by default) prints a code on every document that opens a page of UN
cards. The page and direct PDF downloads require sign-in, just like the rest of
the application. A scan made without a session opens sign-in first and returns
to the requested UN numbers and regime afterwards.

What the code carries is the UN numbers and the regime, and nothing else. No consignor,
no consignee, no quantity, no reference, no shipment identifier. The link does not
look up a stored shipment. The document that carries the code already
prints those same UN numbers in plain text and larger, so the code discloses nothing the
paper in the reader's hand does not already say.

The page behind it answers with two things per number: the number, and whether this
installation holds a card for it. A missing card is reported missing rather than left
out, because somebody standing at a vehicle needs to know a card is absent instead of
being handed a shorter list and left to assume it was complete. A card is never
substituted from another regime — ADR and IMDG print different obligations.

Card links are off until an administrator turns them on. Printing a code needs
the installation's address configured. Lookup answers about at most thirty UN
numbers per link and is rate limited to thirty requests a minute per caller. Requests without a
valid session answer 401. With the switch off, authenticated requests answer 404.

The link addresses a UN number and regime, not a consignment. It has no shipment
expiry; the cards available later depend on the installation's current card set,
feature setting and the reader's active session.

## Account access

EMCargo always requires sign-in to use the full application. Accounts, personal
preferences, avatars and the organisation's settings live on this installation.
The former open application is retired; an old `EMCARGO_MODE=open` variable does
not bypass authentication or disable saved settings and auditing.

UN-card links and direct card downloads also require a valid session.
Login and account recovery, status probes and the branding displayed on the
sign-in page are also reachable before signing in. Business API endpoints and
API documentation require a valid session.

Upgrading preserves existing accounts and data. No scheduled database reset is
implemented. Shipment retention is still the administrator's explicit choice.

## The shipment history

Off by default. An organisation that would rather not retype the same five customers,
or that wants to hand out last month's papers again, has an administrator switch it on
under **Settings → Administration → Keep shipments**. This is what that changes, and only
this:

**What is kept.** Each shipment whose documents were downloaded, or that a user chose to
keep from the export step: the wizard's state as it stood (the goods lines, the declared
dangerous goods, the document fields, the signature if one was drawn for it), the request
that produced its documents, and the structured export with the derived findings and the
editions they were computed against. The documents themselves are **not** archived; they
are rendered again from the kept request when asked for.

**Who sees it.** Admins, Super Users and DG Specialists see every kept shipment. Other users see the
shipments of their own **department**, and a user without a department sees the ones
nobody's department claims — so an organisation that never makes a department has
everybody seeing everything, and one that does has each department seeing its own. A
shipment carries the department of whoever kept it, at the moment it was kept; somebody
moving departments does not take last year's shipments along. A shipment another
department kept is, for you, not there: the server answers as if it did not exist.

**How it goes away.** A user removes a shipment from the shipments page, after a
confirmation. An administrator switches the whole history off on the same screen that
switched it on — and while kept shipments or trips are still in the table the server
**refuses** the switch: the screen names the counts and, on confirmation, deletes them
first, then saves the switch. A switch alone never deletes anything, and a table is never
kept while the interface claims it does not exist — that would be the one outcome worse
than either choice. Should a database hold kept shipments while the setting says off (an
installation that dropped the old deploy-time variable after upgrading), start-up switches
the setting back on and says so in the log rather than hiding them.

**Trips.** With the switch on, the groupage page offers to keep an assessed trip: the
consignments as they sat on the vehicle (their names, their dangerous goods entries, and
which kept shipment each came from when it did), the permitted maximum mass of the
transport unit, and the check's answer as it was given, with the editions it was computed
against. Nothing is kept until somebody presses **Keep trip**. Trips follow the same
department rule as shipments, are listed on their own page, reopen on the groupage page,
and are removed there or from their record. Switching the history off counts them along
with the shipments and deletes them in the same confirmed step.

**Drafts and review submissions.** The history feature autosaves a private draft
while it is being edited. DG submissions are explicitly saved separately and are
not completed-history entries. Disabling or clearing history does not erase those
submissions or their signatures. See [DG review](dg-review.md) for removal and
release revocation. With history off, its own API routes return 404; the review
queue remains available to authorised accounts.

## The audit log

The organisation application keeps a log of who did what, for its administrators. It
is written by the routes that do something worth an administrator's attention and read
on a page of its own. Retiring guest mode does not disable this log.

**What a line holds.** The moment; the account (its name is kept beside its identifier,
so a line outlives the account it describes); the action, as a code from a fixed list —
signing in, a refused sign-in, signing out, a password change or reset, a second factor
switched on or off, an account made, changed, cleared or removed, the settings changed,
a shipment kept, updated, reopened for its documents, exported or removed, a document or
bundle downloaded, a bundle mailed, an annual report drawn; a short summary in the
application's own words; and the address the request came from, as the rate limiter
sees it.

**What a line never holds.** The contents of a shipment. The summary of a kept shipment
is its reference; of a document download, the document key; of a settings change, the
*names* of the settings that changed — the mail password among them, never its value;
of a mailed bundle, the document keys and how many recipients, never who. DG review
events record the reference or decision status, not the submitted data or comments. A refused
sign-in records the name that was tried and why it was refused, never the password. The
test suite searches the whole table for the consignment's parties and goods after a full
round of keeping, exporting and mailing, and finds none of them.

**How long.** As many days as an administrator set under Administration — 365 unless
changed — and whatever is older is deleted when the application starts. The same
selection the page shows can be exported as CSV for whoever keeps records elsewhere.

## Container distribution

Current EMCargo images are published exclusively to GHCR:

```bash
docker pull ghcr.io/jeffreymooiweer/emcargo:latest
```

Preserve the existing data volume when replacing a container. Historical images
from other registries are not maintained by this repository's release workflow.
