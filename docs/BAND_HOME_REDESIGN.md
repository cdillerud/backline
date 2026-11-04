# Backline Band Home redesign — implementation specification
Status: approved design direction, development-only. Reference: user-supplied screenshot of RiffPile /the-drunk-uncles (November 2026). This is an information-architecture reference, not permission to reproduce branding, assets or code.

## Product principle
**Band life first; tools second.** A musician opening a band should immediately see the next commitment, what needs attention, who has responded, the music being prepared, and the most useful next action. Preserve Backline's more advanced show-production and touring workflows. Do not create a duplicate record or alternative permissions system to power the home.

## Navigation — six primary destinations
| Destination | Existing routes / capabilities | Notes |
| Home | dashboard | Default after band selection; all roles see a useful, role-safe view |
| Music | songs, setlists, recordings, media, studio | Song catalogue, writing status, music attachments, setlists; AI Gig Studio kept as scoped utility |
| Schedule | schedule; events and calendars retained as compatibility routes | One calendar for shows, rehearsals, meetings, availability and RSVP; contextual event dialog |
| Shows & Tours | touring, showops, operations, venues, bookings | Itinerary, day of show, stage, rider, contract, guests, rooming, bookings; avoid duplicating entities |
| Band | collaboration, notifications, tasks, members | Conversations and member workflow; global alerts remain top-right |
| Business | finance | Owner/manager/treasurer only; future merchandise/billing behind actual role and entitlement checks |

Do not restore independent Shows/Rehearsals/Agenda/Calendars primary tabs. Do not reintroduce tabs under the chat composer. Secondary destinations are only displayed in-context, not as another primary navigation row. Preserve existing route identifiers in the first migration; change labels and grouping without schema changes.

## Home layout
1. Band identity: selected band's name, compact subtitle, single visible band-switcher, quick actions.
2. Quick actions (actual supported destinations only): Add song, Add show/rehearsal, Songs & recordings, Set availability, Open conversations. Never display an unsupported form as implemented.
3. Stat cards, band scoped: Songs, upcoming shows, rehearsals, open tasks, recordings; links to their source views. Counts must be derived from fetched, authorized records. No fabricated availability, dollars, storage quotas or activity.
4. Coming up: next five chronological authorized events, local event details link; empty state opens Schedule.
5. What needs attention: open tasks and authorized booking follow-ups, due dates; no invented urgency and no leaking member-only financial data.
6. Availability / RSVP: show real responses or an honest 'Open Schedule to respond' placeholder until a scoped, authorized aggregation endpoint exists. No fake counts.
7. Conversation highlights: latest band-scoped threads from the collaboration source, with deep link; never display messages from another band.
8. Music / writing pipeline: current song statuses and rehearsal goals from existing records, avoiding invented workflow states.
9. Recent activity: audit-backed, band-scoped feed only after source and cursor semantics exist; meanwhile show explicitly labelled latest recorded events, not a simulated 'live' feed.
10. Show readiness: upcoming show's recorded advancement, setlist, guest and lodging state, with 'not recorded' rather than guessed completion.

## Interactions and empty states
- A card navigates to its relevant existing route; a dated event opens its contextual dialog, not an unrelated management screen.
- All links and quick actions are buttons with discernible names and keyboard focus.
- Responsive: desktop side nav, mobile condensed nav; cards collapse 5 -> 2 -> 1 columns. Important actions must be visible without horizontal scrolling.
- After creating/editing a record, refresh both its source view and the Home summary without full reload. Preserve calendar focus and current band.
- Fetches must reject stale band/session changes. Never put member financial figures, room confirmations, private guests or other-band messages into Home.
- Clear empty states offer one genuine action (e.g. Add first song or Add event), without pressure to purchase.
- No RiffPile logos, copied artwork, visual assets, plans, or paywall claims.

## Implementation plan and acceptance gates
### P1 — Home foundation (first)
- Rename dashboard to Home and Band Hub to Band; reorganize primary workspaces, preserve all underlying route IDs.
- Show selected band name, working quick actions, role-safe metric cards, coming events, tasks and booking follow-ups.
- Existing event, task and song records remain the source of truth; no migration.
- Desktop/mobile navigation and member/owner role tests pass; empty band and multi-band behavior verified.

### P2 — contextual data cards
- Populate recording/rehearsal counts from authorized sources.
- Surface scoped RSVP gaps and highlights, collaboration previews, and song-status pipeline. Add minimal aggregation endpoints only where needed with explicit role tests.
- Test first-run/empty band, stale sessions, and cross-band isolation.

### P3 — seamless workflow
- Event detail dialog deep links to RSVP, preparation, setlists, show packet, guest operations and related tasks without copying data.
- Home quick-action modal accepts show/rehearsal defaults; save returns to useful context; no full-page reload.
- Tour readiness cards use only confirmed stored fields.

### P4 — product polish / release gate
- Mobile real-device UX, focus order/screen-reader support, performance with large bands, off-site recovery, independent permission review and CI.
- Preview deployment requires successful CI and access; production remains explicitly unauthorized.

## Non-goals and safeguards
No production merge/deploy, live email/push, public sharing, billing/paywall, calendar schema rewrite, or fake data. User screenshot is layout inspiration only. Measure feature parity by tasks completed, not by visual similarity.
