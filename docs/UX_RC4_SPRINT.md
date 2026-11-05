# Backline v0.5 UX RC4 — musician-first Home and workspace acceptance

**Development status:** Integration branch only, draft PR #5; deployed authenticated demo RC2 stays untouched until a separately approved release.

## What changed

### Home uses recorded facts, not guesses
- The next *active* Gig is promoted to an action-first spotlight. Canceled/cancelled/completed events are excluded from this spotlight, active-event counters, Home's short upcoming list, and role-authorized readiness/RSVP retrieval.
- The next gig's signed-in-user RSVP is fetched even when three earlier rehearsals occupy the first three slots. The event-request budget is capped at **four**: first three active upcoming commitments plus the next gig if not already present.
- The spotlight reports **RSVP not loaded** if a fetch has not supplied it, **RSVP unavailable** if a request failed, and **Not linked** if the current account is not in the response. It never silently changes an unknown answer into Going.
- The same remaining upcoming event appears **once** in the Home event list; its recorded personal RSVP appears in that row. The separate, repetitive Other RSVPs card is removed. Event details/RSVP actions remain accessible.
- Open tasks keep the linked signed-in roster member first, sort by recorded due date, and visibly flag **Overdue** / **Due today** without inventing deadlines. Manager booking follow-ups remain scoped to manager roles.
- Music now shows actual song names and saved statuses needing attention, rather than simply counts of readiness labels. Ready/Performance Ready/Gig Ready/Finished songs are omitted. This is not an automated readiness assessment.
- The existing next-show production details remain in an optional disclosure, and all saved setlist/show-task information remains reachable.

### Security, semantics and state
- A pending dashboard load is invalidated on logout, and async load results must still match the originating session. Existing band/session guards and server-side authorization remain in force.
- The six top-level workspaces still map to all prior routes. Member navigation cannot offer Finance; the server independently rejects unauthorized finance operations.
- No database migrations, external providers, unapproved publish/notification actions, or background offline editing were added.

## Automated checks
1. Authenticated synthetic owner Home checks for action-first next gig, personal-task priority, rehearsal songs, menu controls, factual overdue badges and absence of duplicated RSVP cards.
2. Simulate three extra earlier rehearsals: the next gig RSVP must still be fetched and rendered from a real server response.
3. Simulate a canceled upcoming gig: Home must not promote it, display it as a commitment, or inflate the show count.
4. Verify Home has no document-wide horizontal overflow at 320, 390, 768 and 1280 pixels and tablet navigation exposes accessible labels.
5. Independently navigate Home, Music, Schedule, Shows & Tours, Band and Business at those widths; ensure no document-wide horizontal scrolling and no client-side errors. Capture synthetic screenshots.
6. Verify member role has no Finance navigation.
7. Run all existing collaboration, Gig Day, performance, tour, PWA, authorization, media, finance, PDF, syntax, compilation and dependency-audit tests.

## Preview acceptance after future release
Use **only** isolated `backline-auth-demo` with fictional credentials/data. Compare Home at laptop and a 320–390px phone, then click into the next gig, the RSVP editor, two personal tasks, the rehearsal-song library and each of the six workspaces. Verify logout and sign-in. The final release-branch SHA must have a green GitHub Actions run and the Fly deployment must report the exact build SHA. The existing RC2 is the rollback image until a newer candidate passes.

## Known limits
- The preview remains disposable and its sample dates are relative to the seed date in the band's Central time zone. Replacing Machines can regenerate examples; sample dates are not real bookings.
- RSVP status only covers bounded, authorized upcoming-event responses. A server failure is shown as unavailable instead of inventing an attendance answer.
- The Home view uses existing task, event, repertoire and discussion records; it is a curated summary, not a new recommendation engine or substitute for the full modules.
- Passing synthetic Chromium tests is not equivalent to testing on a real band's devices or enabling commercial use.
