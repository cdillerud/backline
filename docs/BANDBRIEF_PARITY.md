# BandBrief minimum-feature acceptance checklist

Source: the feature list supplied by Chad on October 26, 2026, corresponding to
https://bandbrief.com/features/. This is an acceptance checklist, not a claim that
Backline has reached feature parity. “Verified” below means synthetic automated
tests exercise the described behavior; commercial release still needs review.

| Requested capability | Backline status | Evidence / remaining acceptance |
|---|---|---|
| Create bands, free member invitations | Implemented, account preview only | Existing invitation/account regression tests; no per-member billing exists. |
| Instruments, consistent display names, profile photos | Implemented | Manager-only account/roster links; shared stage names, instruments and validated profile photos in roster, RSVP and discussions. |
| Shared band hub | Implemented | Band dashboard, roster, shows, task board, venue book and repertoire; all private under existing account middleware. |
| Multiple colour-coded calendars | Implemented | Named calendars, scoped event assignment, monthly grid; API and browser tests. |
| Gigs, rehearsals and sessions | Implemented | Session classification adds no destructive table rebuild; sessions retain ordinary event IDs, calendars and RSVP support. |
| Per-event RSVP and availability | Implemented | Session-derived identity, yes/no/maybe board, availability notes and notification requests; owner/manager/member self-service only. |
| Load-in, doors and stage times | Implemented | Advancement, day-of-show timeline, calendar event cards, production PDF and iCal export. |
| Personal calendar merges bands | Implemented | Calendar view combines only bands returned by the signed-in user's authorized band list. |
| iCal feed | Implemented; exposure defaults off | Hashed, revocable tokens for one selected calendar; minimized fields, secret-URL warning and access-log redaction. Authenticated downloads remain available. |
| Venue book with contacts, load-in and curfew | Implemented within each band | Structured promoter/engineer contacts, tags/favourites, live gig links and PDF context. |
| Venue catalog shared across bands | Implemented | Manager access in both bands, field-selection preview, explicit confirmation, live show links and revocation; no blanket source-band access. |
| Songs: key, tempo, artist and tags | Implemented | Editable repertoire metadata and tags; API tests and setlist musical cues. |
| Reference recording attachment | Implemented with format limits | Private PCM WAV uploads/playback up to 25 MB plus shared HTTPS recording links; MP3/transcoding remains future work. |
| Drag-and-drop setlists, live runtime | Implemented | Drag handles plus accessible reorder buttons, add/remove, persistence, measured runtime excluding breaks. |
| Print-ready setlist PDFs | Implemented | Band-scoped PDF downloads with song order, musical cues and duration; extracted-content test. |
| Assigned tasks, due dates, gig/song/set links | Implemented | Task creation/edit/completion and validated same-band references; API/browser tests. |
| Due-tomorrow reminders | Implemented in-app; email delivery disabled | Personal idempotent due reminders use account time zones when notification centre refreshes; delivery-worker scheduling remains a live-service prerequisite. |
| Band/song/setlist discussion threads | Implemented | Managers create scoped threads; members post and edit their own replies. Viewers/treasurers remain read-only. |
| @mentions and real-time/typing updates | Implemented through polling | Explicit same-band mention picker, personal alerts, two-second reply polling and expiring typing presence. WebSocket/SSE optimization remains future work. |
| Photo albums and lightbox | Implemented | JPEG/PNG validation, pixel/byte caps, metadata stripping, 100 MB band media quota and authenticated lightbox. |
| Public/members-only albums | Implemented; exposure defaults off | Members-only default, explicit publication, immediate privacy revocation, extra confirmation for photos added to published albums. |
| Public bio/banner/upcoming gigs/albums | Implemented; exposure defaults off | Authenticated draft preview, explicit publish/revoke, allowlisted public JSON/HTML and selected-media checks; synthetic browser tests only. |
| Notification centre and per-category email | In-app implemented; email queued only | Personal assignment/RSVP/mention inbox, own read states, per-category preferences; revoked band memberships lose access. |
| Immediate/daily/none email and daily digest | Partial; live delivery excluded | Time-zone-aware queue, daily grouping, suppression/rescheduling and fake-transport retry tests work. Provider activation, verified recipients, scheduled worker and crash-delivery certification remain. No live mail sent. |
| Installable PWA on phones/tablets | Shell implemented; device acceptance pending | Manifest, icon and root-scoped network-only worker; no API/media/HTML caches. Test checks worker readiness and empty Cache Storage. Native installation on actual devices still needs acceptance. |
| Free core coordination and commercial pricing | Not a billing release | No charges or subscriptions introduced; commercial tier design/payment implementation remains separate. |

## Approval and remaining release work

Chad approved the development-only security proposal on October 26. Implementation
and tests are on the integration branch only. Public capability routes are disabled
unless explicitly configured; no deployment, live mail or real public publication
is authorized. Remaining commercial work includes billing, scheduled live delivery,
real-device PWA/accessibility acceptance, storage operations, backup/migration
certification and independent security review.

## Completion gates

Each missing or partial item must have a visible UI, persisted behavior, authorized
role coverage, same-/cross-band regressions, mobile/browser acceptance and a clearly
stated delivery/hosting dependency before it can be marked complete. API stubs,
buttons and preference forms alone do not count. Public features must demonstrate
that private venue notes, contacts, discussions, finances and RSVP details never
appear in anonymous responses.
