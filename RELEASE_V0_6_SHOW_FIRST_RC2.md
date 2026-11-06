# Backline v0.6.0-rc.2 — Show-first UX authenticated demo release

## Goal
Replace the application shell with four musician-first destinations — Home, Calendar, Music and Band — without removing established production, touring, finance, setlist, guest or collaboration capabilities.

**This candidate targets only the isolated synthetic `backline-auth-demo` Fly.io application.** Production and the separate visual preview must not be deployed, restarted, or modified.

## Included
- A genuinely four-item primary navigation on desktop and mobile.
- Calendar agenda gives immediate access to each gig's central Show overview, with a unified route to Gig Day.
- The Show view places venue calls, date, location, personal RSVP, assigned tasks, setlists, bandmates, directions and guest requests together. Actual recorded facts are used; missing facts remain explicit.
- Management tools remain available to owners/managers in **Manage** and privileged financial details remain hidden from standard members. Treasurer access is finance-only within Manage.
- Member guest requests and urgent show updates are reachable via Band and Show, rather than requiring the admin area.
- Music retains contextual links to setlists, studio and media without adding primary tabs.
- Calendar creation, edits and new-calendar controls are hidden from members who cannot manage the band; the backend remains the authorization boundary.
- Responsive layouts and synthetic owner/member browser acceptance, including overflow checks and stale-request regressions.
- Frontend syntax is verified early in CI.
- API identity `0.6.0-rc.2`.

## Release source and certification
Feature branch: `feature/backline-v0-6-show-first-navigation`.
Release branch: `release/backline-v0.6-show-first-rc2`.

The release branch has its own deploy-script pin and this runbook. **Do not rely on a feature-branch or older RC's CI pass**: require GitHub Actions completed success on the precise final release SHA.

## PowerShell 7 — prepare and read-only preflight
```powershell
cd C:\Users\ChadDillerud\backline
git fetch origin release/backline-v0.6-show-first-rc2
git switch release/backline-v0.6-show-first-rc2
git pull --ff-only origin release/backline-v0.6-show-first-rc2

# Preserve the exact previously working image identifier before replacement.
flyctl releases --image --app backline-auth-demo
flyctl status --app backline-auth-demo

# Checks branch, remote commit, tracked-tree cleanliness, exact-head CI,
# isolated Fly config, mounted volume absence, and existing deployed demo secret.
.\scripts\deploy-auth-demo.ps1
```
The release script must not create or overwrite the existing `BACKLINE_DEMO_PASSWORD`.

## Deploy (only after all preflight checks pass)
```powershell
.\scripts\deploy-auth-demo.ps1 -Deploy
```
The script stamps the image with the exact HEAD as `BACKLINE_BUILD_SHA`, then asserts `/api/health` has HTTP 200, status ok and matching build SHA, and unsigned `/api/bands` returns HTTP 401.

## Post-deployment signed-in acceptance
Use only the disposable demo identities and synthetic data:
1. At 320, 390, 768 and 1280px, confirm bottom navigation is Home / Calendar / Music / Band with no horizontal overflow.
2. Home next gig → Open show → correct date and available time data → Gig Day. Return to Calendar and confirm the same gig; check no duplicate featured events.
3. Calendar upcoming list contains rehearsals and shows and opens the appropriate detailed view. Confirm a member sees no unauthorized Add event / New calendar / Edit controls.
4. Owner Manage displays bookings, production, tours, venues, crew/guest operations and finances. Confirm a member sees no Manage entry or finance data.
5. Band conversations and member show updates/guest-pass requests remain accessible.
6. Verify setlists, performance view, RSVP, and task completion. Sign out while an API request is pending; no private content may reappear.
7. Validate mobile touch controls and accessibility focus, including account and disclosure menus.

## Recovery
If signed-in validation fails, use **only** the prior immutable image identifier captured before deployment:
```powershell
flyctl deploy . --app backline-auth-demo --config fly.auth-demo.toml --ha=false --image '<VERIFIED-PRIOR-IMAGE>'
```
The demo SQLite database is disposable and not attached to a persistent volume. Image rollback does not restore database contents.

## Release gate
- [ ] Exact final release HEAD CI: all jobs passed
- [ ] Read-only preflight passed on deployment machine
- [ ] Prior image recorded
- [ ] Exact build SHA, health and unsigned API verified
- [ ] Signed-in desktop/mobile acceptance passed
