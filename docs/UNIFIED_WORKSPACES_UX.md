# Backline unified workspace UX — development review

## Competitor baseline (October 2026)

- **BandHelper** organizes shows, rehearsals and custom event categories in one Schedule, with calendar/list modes and per-event availability. Backline's previous Shows & Rehearsals table plus separate Calendars duplicated scheduling navigation.
- **BandBrief** places shared calendars, RSVP, discussions, tasks and photos in a member-first experience. Backline's social tools existed but were spread across Band Hub, media, notifications and tasks.
- **RoadOps** emphasizes a tour/day workflow with a schedule, change feed, lodging and guest manifests; Backline's touring itinerary, show packets and show operations previously had distinct entry points.

Product references: https://www.bandhelper.com/tutorials/scheduling_events.html , https://bandbrief.com/features/ , https://www.roadops.app/

## Current integration increment

1. **Schedule** replaces the primary Shows & Rehearsals navigation and removes the duplicate Calendars sidebar item. Calendar, Shows, Rehearsals and Agenda are different views of existing event records. Calendar subscriptions, named calendars and iCal remain supported; no schema rewrite or event-ID migration.
2. **Band Hub** gets a collaboration landing panel that links discussions, bandmates, notifications, media, tasks and Schedule. Existing RSVP and thread permissions remain unchanged.
3. **Tours** is a unified entry point with Itinerary, Show production and Crew & logistics. Existing stage plots, PDF show packets, hotel rooming, imports, alerts and guests remain in their original permission-scoped workspaces; this increment provides clear navigation rather than falsely claiming a redesigned integrated tour-day document.

## Follow-up UX acceptance gaps

- Calendar grid event chips currently need direct, accessible event-detail navigation and contextual RSVP/production actions.
- Rehearsal-specific goals and preparation notes should appear within the event workspace.
- Tour tab content should progressively integrate day timelines, lodging and guest summaries rather than rely on links to other screens.
- Band Hub needs richer conversation and media activity feeds, privacy-scoped posts and easier mobile notification handling.
- True multi-band calendar conflict checks must be measured and tested, not inferred from shared views.
- Phone/tablet acceptance and screen-reader keyboard coverage are required before commercial release.

All work remains development-only. Existing role checks, scoped data access, public sharing defaults, and production service/data are unchanged.
