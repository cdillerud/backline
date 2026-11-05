# Backline v0.4 development record

Branch: `integration/backline-v0-4-rc`  
Draft pull request: https://github.com/cdillerud/backline/pull/5  
Session date: October 26, 2026  
Starting revision: `b4bd8926d7170fda56b4ecf42268d8c8f9e0d951`

## Implemented in this batch

- Venue advancement accepts validated 24-hour times, IANA venue time zone,
  explicit show-date / day +1 / day +2 offsets, venue address, lodging, hospitality,
  settlement instructions and up to 50 crew calls with owners, locations and notes.
- Confirmation requires venue contact, load-in, soundcheck, doors, show time,
  a venue time zone, chronological milestone order and no unresolved questions.
  Saving crew-call changes through the editor returns advancement to draft.
- A shared schedule projection powers the band/gig-scoped timeline API, day-of-show
  screen, browser print view and PDF. PDFs read current saved advancement rather
  than duplicating contact/timing fields into editable document templates.
- PDF packets contain contacts, access and lodging details, confirmation warnings,
  and an overnight-aware schedule with repeatable table headers. Embedded fonts
  keep print spacing consistent; the timeline starts on a dedicated page.
- Stage equipment can be renamed, retyped, removed and positioned with inline
  fields, dragging or arrow keys (Shift = ten grid units). Input channels expose
  channel number, source, microphone/DI, stand and notes, plus reorder controls.
  Stage editor adds keyboard focus handling and unsaved-change exit protection.
- Tour stops have form-based creation and editing, including arrival/departure,
  lodging, travel notes and gig links. Itineraries read current linked advancement
  contacts and time zone, and open the show's call sheet directly. Canceled stops
  are excluded from transfer warnings; changed gig dates raise a review flag.
- Mobile layouts, scrollable navigation, focus outlines, show-tab keyboard
  navigation, accessible notifications, and workspace-selection reset improved.
- Regression coverage includes overnight validation, real-session authorization,
  current PDF contents, escaped exports, editable stops and Chromium workflows
  at desktop and 390px widths. CI audits production requirements with pip-audit.

## Validation and deployment boundaries

All test databases and contacts are synthetic and disposable. No production
repository branch, database, service or Fly volume is modified by these tests.
Run `BACKLINE_LOCAL_DEV=1 python -m pytest -q` after installing
`requirements-dev.txt` and Playwright Chromium. CI also runs JavaScript syntax,
Python compilation and `python -m pip_audit -r requirements.txt`.

This batch is not deployed. Fly CLI/token authentication is unavailable in the
execution environment. Only `backline-visual-preview` is an authorized deployment
target; follow `PREVIEW_DEPLOY.md`. Never deploy these commits using `fly.toml`.

## Data compatibility and permissions

No SQL schema migration or destructive operation is introduced. New advancement
fields live in the existing JSON body. Legacy missing/invalid time zones or clock
strings are readable and flagged as provisional in the timeline/PDF; users must
correct clock strings and provide a valid zone before saving a confirmed advance.
Day offsets are explicit, never inferred from a decreasing clock time. Existing
show-document snapshots remain editable and are not overwritten by advancement.

Existing account middleware remains unchanged: owners/managers can edit these
workflows; treasurers, members and viewers can read their band's operational
records but cannot edit them. Anonymous and cross-band requests remain denied
when account mode is enabled. This does not certify account mode for production.

## Outstanding work

1. Advancement revision history, concurrent-edit detection, venue confirmation
   evidence and contact-specific roles/email/phone rather than one shared pair.
2. Time-zone picker, calendar-date labels on overnight calls, DST ambiguity
   handling, overlapping crew-call warnings and per-person filtered call sheets.
3. Stage undo/redo, reusable band layouts, monitor mixes and linked input/source
   labels; touch-device usability testing and fuller accessibility audit.
4. Independent contact directory and reusable venue profiles, hotel reservations,
   transport/rest budgeting and tour-wide printable/exportable itineraries.
5. Public-commercial release gates: independent authorization/security review,
   sensitive-document hardening, migration/versioning and tested off-site recovery.
6. Preview acceptance on actual phones and tablets; deploy this batch only after
   preview authentication is available. Production merge/deployment stays blocked.

## Local validation result

57 tests passed, including four Chromium browser cases (desktop/mobile show
workflows, mobile tour editing, and existing navigation/document editing smoke).
JavaScript syntax and Python compilation passed. Production requirement audit
reported no known vulnerabilities. PDF cover, contacts and timeline were rendered
and visually reviewed. The environment emits one upstream Starlette/httpx
compatibility deprecation warning; it does not fail the suite.

## BandBrief minimum-feature follow-up

Chad supplied the BandBrief feature list as the minimum acceptance checklist.
`docs/BANDBRIEF_PARITY.md` records each requested capability as implemented,
partial or missing. This release must not be described as full feature parity.

Implemented next: private per-band venue records with multiple contacts, tags,
favourites and live show links; linked venue details in production PDFs; assigned
tasks with due flags and validated gig/song/set links; editable musical metadata,
tags and HTTPS recording references; persisted drag/keyboard setlist ordering,
live runtime and setlist PDFs; named colour-coded calendars, a monthly grid,
combined authorized-band view and authenticated iCalendar downloads.

This follow-up adds only new SQLite tables; it does not rebuild existing tables or
alter production data. Tables are initialized only when the new source is started
against the selected development/test database. Back up and rehearse migration
before any future production launch. Recording links are external references;
media hosting, anonymous pages and subscription feeds are not enabled.

The existing account authorization middleware is unchanged. Self-service RSVP,
member discussions, personal notifications, uploads and public sharing remain
pending the concrete authorization proposal in
`docs/SECURITY_CHANGE_PROPOSAL.md`, as required by the user's operating rules.

CI installs only the Chromium headless shell needed by the tests and gives browser
installation a ten-minute limit, to make stalled dependency installs diagnosable.
The new workspace script also receives a JavaScript syntax check.

Follow-up validation: **64 tests passed**, including six Chromium cases. Both
JavaScript files passed syntax checks; Python compilation and Git whitespace checks
passed. The setlist PDF was rendered and visually reviewed. Tests use fake contacts,
fictional venues and disposable databases. The earlier show-operations PR workflow
also passed in GitHub Actions; final follow-up runs are verified separately.

## Approved collaboration, media and sharing — v0.4.0-rc.2

Chad approved sections A/B/C of the security proposal on October 26, 2026.
Implemented and exercised only with synthetic local accounts and data:

- Session-bound RSVP/availability and scoped band/song/setlist discussions, own-reply
  editing, explicit mentions, expiring typing indicators and two-second updates.
- Owner/manager account-to-roster links; consistent stage names, instruments and
  profile photos across band contexts. Personal notifications/read states, category
  preferences, timezone-aware daily queue grouping and once-per-day task reminders.
  A fake-transport dispatcher is testable; there is no live sender or scheduled
  delivery worker. Real-provider crash/idempotency behavior still needs certification.
- Validated JPEG/PNG and PCM WAV media. Images are re-encoded without EXIF, capped
  at 12 megapixels/5 MB and 2400px output; audio is re-encoded PCM WAV, at most 25 MB
  and 20 minutes. Per-band media quota is 100 MB. No arbitrary URL fetching.
- Private albums/lightbox, recording attachments/playback, draft public-page preview,
  explicit publication/revocation and selected public images/gigs only. Adding photos
  to already-published albums requires additional explicit confirmation.
- Cross-band venue shares require manager rights in both workspaces, selected-field
  preview and confirmation. Destination views and show PDFs resolve only those
  fields; revocation removes future access. No shared production advancement data.
- Revocable, hashed calendar subscriptions for one selected calendar, minimized
  public fields and token redaction in Uvicorn access logs. Reverse-proxy/provider
  logs and retained calendar copies need operational review before live activation.
- Installable online PWA shell and mobile workspace switching. The root-scoped worker
  has no fetch handler or private caches. Logout/session loss clears local app state
  and revokes authenticated media object URLs. Actual-device installation acceptance
  remains. This is not offline editing or offline access.
- Session events use an additive classification table over the legacy non-gig event
  storage type, preserving event IDs, RSVP and calendar behavior without rebuilding
  the existing CHECK-constrained events table. A future canonical schema migration
  should replace that compatibility layer during a separately rehearsed release.
- Role-aware app loading fixes member login failures caused by eager finance reads.
  Dashboard/event/calendar responses no longer leak fees or financial totals to
  member/viewer roles; treasurers retain their existing financial reads/writes.
- Application/API health identify `0.4.0-rc.2`; optional `BACKLINE_BUILD_SHA` records a
  deployment's source commit. Pillow is constrained to patched 13.x after auditing.

`BACKLINE_PUBLIC_SHARING_ENABLED` defaults off. Tests explicitly enable it for
fictional band pages and feeds on loopback only. Nothing here authorizes production
merge, deployment, real publication or live email delivery. No production source
branch, data, credentials or service has been modified.

RoadOps was reviewed for additional product ideas. `docs/ROADOPS_REVIEW.md` records
proposed change history, urgent alerts, guest lists, structured rooming and reviewed
imports. Those RoadOps additions remain proposals, not claimed implementations.

Approved-batch validation: **84 tests passed**, including twelve Chromium cases
across desktop and 390px mobile workflows. JavaScript syntax, Python compilation
and whitespace checks passed. The resolved production dependency audit reports no
known vulnerabilities with Pillow 13.0.0. An upstream Starlette/httpx deprecation
warning remains non-failing. Final GitHub Actions results are recorded on draft PR #5.

Final regression refinements keep test show dates relative to the fixture data,
keep unfiled photos accessible through Photo library, select newly created albums,
and align RSVP avatar/name rows. The complete suite remains 84 passing tests;
focused desktop/mobile gallery acceptance also passed after the library refinement.


## RoadOps-inspired operations — v0.4.0-rc.3

Chad instructed continuation of change history/urgent acknowledgements, guest lists,
structured hotel rooming and reviewed imports. Implemented the shared operations
audit/version layer, exact-path own guest-request writes, manager approval/privacy
boundaries, private exports and review-only CSV-to-tour-stop flow.

`docs/OPERATIONS_RC3.md` describes the detailed behavior, role matrix, additive data
compatibility and remaining work. Public-page/feed allowlists and default-off
exposure are unchanged. There is no live sender, push provider, production merge,
deployment or production-data access. The browser now waits for all feature scripts
to load before initial rendering, avoiding cross-script initialization races.

Box-office and multi-page rooming PDFs were rendered and visually reviewed for
spacing, repeated headers, timestamps and pagination. Newly added desktop/mobile
cases cover guest approval/export, urgent acknowledgement/history, assigned-room
privacy and reviewed source import/application.

RC3 validation: the complete local suite passed 99 tests, followed by the added
stale-session/privacy case and a fresh combined run of all **19 browser cases**.
There are now **100 collected tests**. Focused operations/API/PDF regressions also
passed after cancellation/export refinements. All syntax, compilation and whitespace
checks passed, and the production dependency audit reports no known vulnerabilities.
Final full-tree GitHub Actions results are recorded on draft PR #5.

The JSON API wrapper rejects late responses after an account or workspace change;
operations additionally guard their grouped refresh and live-alert callbacks. The
new browser regression deliberately holds a private response until after logout and
verifies that the signed-out screen and cleared state remain intact.
