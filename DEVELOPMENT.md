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
