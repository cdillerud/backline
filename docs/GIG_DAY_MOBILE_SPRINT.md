# Backline — Mobile Gig Day implementation and validation

**Scope:** Development branch `integration/backline-v0-4-rc`, draft PR #5. No production deployment or schema migration.

## Product result
A musician-centric **My Gig Day** view is separate from the detailed Show Production workspace. It is reachable from the Band Home next-show panel and from a Gig's calendar event dialog.

The initial screen answers the practical questions in one place:
- **Where:** venue/address, production or venue contact, parking instructions if recorded, phone/email actions if supplied
- **When:** load-in, soundcheck, doors, showtime, and curfew from the existing venue advance; explicit show-date/day+1/day+2 labels and the recorded IANA timezone
- **What to play:** linked show setlists, an inline preview of recorded song order, and an existing performance-view action
- **What to do:** the signed-in user's open tasks only, plus a self-completion action
- **Where to stay:** only the logged-in traveler's authorized linked room data, never other occupants or confirmation references
- **What changed:** urgent change alerts scoped to the selected gig and authenticated recipient, with acknowledgement and refresh

The player can change the selected show without leaving Gig Day, refresh the snapshot, open RSVP, task lists, setlists, performance, personal notifications, detailed production, or (manager only) crew operations.

## Data and security contracts
- Reuse existing event, song, setlist, task, venue-advance, rooming and urgent-alert records. No second source of truth or fictional completion states.
- Private API requests carry the current bearer token and band path; show loads are dropped if band, session, or gig selection changes before responses arrive.
- The existing lodging API filters member rooms server-side. The player view additionally filters manager-authorized room collections to rooms containing the signed-in user's ID.
- The urgent-alert endpoint is called with an explicit event ID and is recipient-scoped. Only id/title/timestamps are retained in client state, not recipients.
- A new `POST /api/bands/{band_id}/gigs/{event_id}/tasks/{task_id}/complete-mine` endpoint checks valid signed-in band role, a Gig event, roster account link, and exact assigned task's event/member linkage inside a SQLite immediate transaction. No caller can mark another person's task or another band's task done through this endpoint. The operation is idempotent and preserves other task fields.
- Unrecorded call times are **TBD**, incomplete advances are not represented as confirmed, and missing hotel assignments are not inferred.
- No new public sharing, third-party notifications, calendar mutations or live delivery.

## UX and accessibility
- Focused route `gigday` with five large call cards, responsive two/three/five-column grids, accessible named sections, high-visibility actions and readable on-stage setlist order.
- Mobile navigation remains grouped under **Shows & Tours**; no duplicate Shows/Rehearsals/Agenda top-level tabs are introduced.
- Explicit return to schedule; all primary actions have clear names, working destinations, and keyboard focus outlines.

## Test gates
1. Existing authenticated demo browser flow opens Gig Day from the event dialog, confirms real seeded calls, personal assignment and setlist, and transitions to detailed production.
2. Desktop and 390px mobile browser flow opens Gig Day from Home, checks no horizontal overflow, and navigates into show-specific tasks.
3. Member account can view its gig-day details but cannot access privileged crew operations.
4. Server security test covers unauthenticated and non-member requests; owner not assignee; unlinked member; cross-band ID; wrong gig; foreign task; idempotent self-completion preserving notes and links.
5. GitHub Actions checks Python regression suite and `node --check` on the new `gigday.js`, plus dependency audit and compile.
6. Final head CI and preview acceptance are prerequisites to development preview deployment. Production merge remains unapproved.

## Out of scope
Automatic arrival geofencing, background push/email, maps/navigation, guest roster disclosure, payment settlement, and automatically declaring a show ready based on partial records.

## Follow-on sprint — inline musician workflow
The stand-alone Gig Day view is now extended with:
- An **inline personal RSVP editor**: the signed-in user can choose Going, Maybe, Can't go or Not answered, optionally provide a short note and save through the established self-only RSVP endpoint. Only the user's response and note are stored in the Gig Day page state, not the band's full attendance roster.
- A Gig Day RSVP shortcut that focuses the inline form instead of navigating away. Save refreshes the server state; band/session/gig guards prevent stale writes being rendered into another show.
- **Venue directions** using a map search for the recorded venue address (or name if no address was recorded). No location or travel-time claim is fabricated.
- An expandable **stage and audio reference** with the existing stage layout and channel-numbered input list; empty shows clearly say nothing is recorded.
- Desktop and mobile-focused regression assertions and member access coverage for the inline RSVP form; script syntax checks remain in CI.

Release gate: the original mobile build passed CI #998. These follow-on commits must pass their own final-head CI before preview use; production remains unchanged.
