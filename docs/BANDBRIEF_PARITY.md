# BandBrief minimum-feature acceptance checklist

Source: the feature list supplied by Chad on October 26, 2026, corresponding to
https://bandbrief.com/features/. This is an acceptance checklist, not a claim that
Backline has reached feature parity. “Verified” below means synthetic automated
tests exercise the described behavior; commercial release still needs review.

| Requested capability | Backline status | Evidence / remaining acceptance |
|---|---|---|
| Create bands, free member invitations | Implemented, account preview only | Existing invitation/account regression tests; no per-member billing exists. |
| Instruments, consistent display names, profile photos | Partial | Roster names/instruments and task assignees exist; linked account/roster profiles and photo uploads remain. |
| Shared band hub | Implemented | Band dashboard, roster, shows, task board, venue book and repertoire; all private under existing account middleware. |
| Multiple colour-coded calendars | Implemented | Named calendars, scoped event assignment, monthly grid; API and browser tests. |
| Gigs, rehearsals and sessions | Partial | Gigs/rehearsals work; independent session events remain. |
| Per-event RSVP and availability | Missing; permission design prepared | Self-service member writes require the access-policy approval described in SECURITY_CHANGE_PROPOSAL.md. |
| Load-in, doors and stage times | Implemented | Advancement, day-of-show timeline, calendar event cards, production PDF and iCal export. |
| Personal calendar merges bands | Implemented | Calendar view combines only bands returned by the signed-in user's authorized band list. |
| iCal feed | Partial | Authenticated .ics download works; revocable subscription tokens/feeds remain pending privacy review. |
| Venue book with contacts, load-in and curfew | Implemented within each band | Structured promoter/engineer contacts, tags/favourites, live gig links and PDF context. |
| Venue catalog shared across bands | Missing; explicit-sharing design prepared | Current band isolation intentionally remains in place. |
| Songs: key, tempo, artist and tags | Implemented | Editable repertoire metadata and tags; API tests and setlist musical cues. |
| Reference recording attachment | Partial | Shared HTTPS recording link works; validated hosted audio upload/playback remains. |
| Drag-and-drop setlists, live runtime | Implemented | Drag handles plus accessible reorder buttons, add/remove, persistence, measured runtime excluding breaks. |
| Print-ready setlist PDFs | Implemented | Band-scoped PDF downloads with song order, musical cues and duration; extracted-content test. |
| Assigned tasks, due dates, gig/song/set links | Implemented | Task creation/edit/completion and validated same-band references; API/browser tests. |
| Due-tomorrow reminders | Partial | In-app task-board flags for overdue/today/tomorrow; personal notifications and email delivery remain. |
| Band/song/setlist discussion threads | Missing; permission design prepared | Member posting and audience/mention rules need the requested review. |
| @mentions and real-time/typing updates | Missing | Authenticated scoped messaging transport and rate/retention design remain. |
| Photo albums and lightbox | Missing; upload design prepared | Image validation, storage quotas and metadata stripping require review. |
| Public/members-only albums | Missing; visibility design prepared | No anonymous media exposure or public publishing added. |
| Public bio/banner/upcoming gigs/albums | Missing; visibility design prepared | Public preview/publish/revoke flow and explicit output allowlist need review. |
| Notification centre and per-category email | Missing; recipient design prepared | In-app task flags exist; authenticated personal inbox and category preferences remain. |
| Immediate/daily/none email and daily digest | Missing | Queue, verified identity, email provider, timezone scheduling and idempotent processing remain. No live messages sent. |
| Installable PWA on phones/tablets | Missing | Manifest/icons and a reviewed service worker/update strategy remain; no private-data offline cache introduced. |
| Free core coordination and commercial pricing | Not a billing release | No charges or subscriptions introduced; commercial tier design/payment implementation remains separate. |

## Completion gates

Each missing or partial item must have a visible UI, persisted behavior, authorized
role coverage, same-/cross-band regressions, mobile/browser acceptance and a clearly
stated delivery/hosting dependency before it can be marked complete. API stubs,
buttons and preference forms alone do not count. Public features must demonstrate
that private venue notes, contacts, discussions, finances and RSVP details never
appear in anonymous responses.
