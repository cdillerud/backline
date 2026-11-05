# Backline v0.4.0-rc.3 — show operations

This development release implements the first RoadOps-inspired operational
workflows. All acceptance data is synthetic. The integration branch and draft PR
remain separate from production; no live delivery or deployment is included.

## Changes and urgent acknowledgements

Advance and tour-stop edits record author, timestamp, before/after values, reason
and revision. Existing records begin their history with the first recorded edit;
no earlier history is invented. The browser sends the revision it loaded, and a
stale save returns HTTP 409 without overwriting another person's work. Legacy
advance/tour API callers may omit revisions for compatibility; new guest/lodging/
import editing workflows require their current revisions.

Timing/access/contact changes to an existing advance generate a crew alert when
the venue time zone is valid and the show is today, starts within 24 hours, or is
inside an explicitly recorded overnight show-to-curfew window. An initial draft
save, a no-op save or an unknown time zone does not generate a guessed alert.
Crew recipients are snapshotted from active band accounts; acknowledgement is a
separate, idempotent personal action. Managers see acknowledgement names/counts;
other recipients see counts and their own acknowledgement only. Reading the normal
notification does not acknowledge the operational change.

Alerts are in-app with five-second polling while the app is visible. Email uses
the existing disabled/test-only outbox. Browser push, SMS and live email are not
implemented or activated by this release.

## Guests and passes

Owner/manager policies define permitted passes, an offset-aware request cutoff and
an approved-headcount limit. Members can request passes for named guests, see their
own requests and cancel their own requests. Re-submitting a cancelled name/pass
returns the same record to pending, preserves history and requires fresh approval.
An approval never survives cancellation/resubmission. Requests are bounded to 100
per requesting person per show, with 5,000 total show-request records.

Managers approve/decline/return requests to pending, with revision checks and an
audit reason. Approved headcount cannot exceed the policy limit; policy edits
cannot reduce the limit below existing approvals. Manager decisions may occur
after the request cutoff. A cancellation notifies managers to review previously
printed lists. The box-office PDF contains approved names, quantities and pass
types only; internal/request notes and other private fields are omitted. Export
snapshots carry a UTC timestamp and page numbers, not a live box-office feed.

## Hotels and rooming

A band can keep multiple stays with hotel contact/address, explicit-offset check-in
and check-out, optional show/tour links, private booking references and manager
notes, plus separate traveler notes. Rooms have a label, type, capacity and selected
active band travelers. Capacity, duplicate rooms for a traveler, cross-band
occupants and overlapping active stays are checked transactionally. Editing stay
dates cannot silently create an overlapping assignment. Cancelled stays remain in
history; their PDFs are prominently marked cancelled.

Managers see all stays/rooms and can download a private rooming PDF. Assigned
travelers see their hotel and room only, with no booking references, manager notes,
other room labels or other occupants' identities. Full private rooming history and
PDF exports are manager-only. A rooming export prints one traveler per row so long
crew lists paginate safely with repeated headers.

## Reviewed CSV itineraries

Supported fields: `date`, `city`, `region`, `venue`, `status`, `arrival_time`,
`departure_time`, `lodging`, `travel_notes`. Date and city are required; columns must
be unique and recognized. Files are UTF-8, at most 250 KB and 200 data rows. Creating
a draft never creates tour stops. Original source text, source line numbers and a
SHA-256 fingerprint are retained. Managers can view every proposed field and the
original source in the review screen.

Selected valid rows are applied only after explicit confirmation. Duplicate rows,
existing tour stops, stale revisions and already-applied rows are rejected. The
selected batch and its history commit atomically. Re-uploading the same source for
the same tour reopens the same draft; differently formatted files still cannot
bypass duplicate-stop detection at application. Imported stops are unlinked, private
tour-planning records, not automatically confirmed gigs or public announcements.

This is deterministic CSV review. It does not claim PDF/email/AI confirmation
extraction, travel-provider integration, automatic venue matching or route estimates.
Correct invalid source rows and upload a new source version to review them.

A manager-only **Download review CSV** action provides a spreadsheet-readable row audit with source row and line, validation issue, duplicate-existing indicator, and minimally necessary stop identity fields. It does not include free-text travel notes or private source contents. The original CSV remains separately viewable with its SHA-256 evidence. Editing the report itself does not modify or apply stops; fix the original source CSV and create a newly reviewed draft.

## Access and storage boundaries

- Owners/managers manage guest policies, approvals, hotel/room records and imports.
- Members gain only exact-path own guest-request submission/cancellation writes;
  existing membership checks remain in force. They cannot approve guests or read
  other requesters' guest lists, private lodging history, source imports or exports.
- Viewers/treasurers retain their previous write restrictions. Any active band
  account may read an explicitly assigned room and acknowledge its own crew alert.
- Operational histories for guests, guest policies, hotels, rooms and imports are
  manager-only. Other crew history covers advances and tour stops.
- No new anonymous route is introduced. Public band pages and capability calendars
  retain their existing explicit allowlists and default-off exposure flag.
- New tables are additive. There is no existing-table rebuild, production migration,
  data deletion, automated source rollback or production deployment.

## Next operational release work

Actual-phone acceptance, localized cutoff/date entry, larger touring-party audience
controls, advance/history retention and recovery operations, push/live delivery,
rooming change notifications, richer guest edits/bulk guest tools, spreadsheet
mapping/import correction, provider/AI confirmation drafts, and offline conflict
handling remain follow-up work. Guest-request and CSV workflows are usable here,
but this remains a development release pending independent security/recovery review.


## Post-RC3 import mapping preview

Authenticated managers can POST a source-to-target column mapping to `/api/bands/{band_id}/itinerary-imports/{import_id}/map-preview`. The mapping requires unique target fields, including `date` and `city`, and each source header must exist in the retained original. The response contains canonical CSV, per-row validation results, and the SHA-256 of the unmodified original. It makes no database edits and cannot directly create tour stops; the canonical output must be uploaded as a new draft, reviewed and explicitly applied. No live spreadsheet provider or automatic correction is integrated. The UI for choosing mappings is still outstanding.

A separate manager-only `POST /api/bands/{band_id}/itinerary-imports/map-source` supports CSV with unfamiliar header names *before* any import draft is created. It accepts tour, filename, bounded original CSV and an explicit one-to-one column map, then returns the canonical CSV and row-by-row validation without saving a draft or changing tour stops. The user must upload the converted CSV through the normal review workflow and confirm selected rows. Original pre-mapping evidence SHA-256 is returned but the raw original is not stored by this dry-run endpoint; keep the original separately for traceability. A UI mapping wizard remains to be built.
