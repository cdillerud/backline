# Backline — musician-first UX RC3 development sprint

**Branch:** `integration/backline-v0-4-rc`; draft PR #5.  
**Deployment boundary:** No change to the already-live, isolated `backline-auth-demo` RC2 or production `backline`. New RC3 requires final-head CI, a separately pinned release branch, explicit isolated-demo deployment and signed-in acceptance.

## Problems discovered from live RC2 screenshot
- Home repeated the same next gig in a prominent spotlight, the Coming Up panel and the RSVP panel, while show preparation repeated the title again.
- Five creation/navigation quick actions competed with a crowded header (Notifications, My Tasks, Band Settings, Join band, Install app and Sign out).
- The attention panel mixed the musician's assigned tasks with all band tasks by due date.
- Demo dates appeared to move by one calendar day around an evening deployment even when the user was in Central Time.

## Changes
- Preserve accessible, always-visible Notifications and My Tasks. Move Band Settings, Join band, optional PWA installation and Sign out into a native `details` Account menu.
- Expose one immediate Add event action to managers and tuck Add song, Music, Schedule and Conversations into More actions; keep every original workflow reachable through existing routes.
- Native menu disclosures close on Escape or an outside click; Escape restores keyboard focus to the prior summary. Header and menu responsive styles avoid horizontal overflow.
- Next Gig shows its factual event date, venue, time and signed-in owner's RSVP if the scoped response was successfully loaded. Missing or unlinked RSVP is never reported as a positive answer. The RSVP button still opens the existing event editor.
- Omit the featured gig from the other upcoming-event and other RSVP lists. Keep other gigs and rehearsals as independent records. Remove the duplicated show title/date in preparation, preserving setlist, task, production, crew and readiness actions.
- Priority-order task rows actually assigned to the signed-in account's linked roster member before general band tasks. This is a presentation sort only, with no new server permissions or mutations.
- Synthetic fixture date offsets now use `America/Chicago` local calendar dates rather than the hosting machine's UTC calendar day. Demo events are still created relative to the day the disposable SQLite database is initialized; any later database regeneration can legitimately shift dates, and the demo sidebar now explains that limitation. Existing show dates are **not** silently rewritten on restart.

## Safety and test plan
- Existing API permissions, protected member/private data boundaries, invitations, persistence and financial model are unchanged.
- Authenticated Chromium verifies actionable next gig, RSVP context and no duplicated next-gig cards, role-aware menus, keyboard behavior, own-task-first ordering, and no horizontal scrolling at 320, 390, 768 and 1280 pixels.
- Demo database bootstrap tests verify Chicago-date offsets for two gigs, rehearsal and task, and restart remains non-destructive for an existing demo DB.
- Full CI repeats Gig Day / performance browser acceptance, collaboration regression, all Python tests, JavaScript parsing, dependency audit and compilation.

## Release acceptance
This document does not certify RC3 or authorize a Fly deployment. The final integration commit and final release-branch commit must each pass CI, screenshots should be reviewed, and authenticated demo login must work after any deploy. Production remains unchanged.
