# Backline 0.6.0-rc.1 — show-first musician UX

This release is for the **isolated synthetic authenticated** `backline-auth-demo` application only. It is not a production rollout. Do not deploy to `backline` or `backline-visual-preview`, attach a persistent volume, reuse real band data, alter sharing permissions, or replace the existing demo secret.

## What changed
- Four everyday destinations: **Home / Calendar / Music / Band**. No management sidebar maze and no fifth mobile navigation tab.
- Authorized members have a separate **Manage band** destination accessible from the sidebar or Account menu. Booking, finance, production, touring, venues, logistics and promotion remain available where authorized.
- A show/rehearsal has an event overview linking to RSVP, Gig Day, setlists, tasks and production details. Click a featured gig title or choose **Open show overview** in the calendar event dialog.
- Members can inspect calendar events without edit/move/calendar administration controls. Managers retain the existing editor and drag-to-reschedule.
- Existing API endpoints and stored data are unchanged; no schema migration.
- Application identity `0.6.0-rc.1`; the Docker build is stamped with the Git SHA and the deploy script checks it after deployment.

## Exact-source release gate
The release HEAD includes a branch-pinned PowerShell deployment script, so it differs from the feature base. Require **completed passing** GitHub Actions for the **exact final release HEAD**: full pytest, Playwright authenticated desktop and phone flows, async workspace and calendar guards, JavaScript syntax, PowerShell validation and production-dependency audit. A successful feature-branch run is not sufficient.

## PowerShell 7 — read-only preflight
```powershell
cd C:\Users\ChadDillerud\backline
git fetch origin release/backline-v0.6-show-first-rc1
git switch release/backline-v0.6-show-first-rc1
git pull --ff-only origin release/backline-v0.6-show-first-rc1

# Save the current known-good image string before any change.
flyctl releases --image --app backline-auth-demo
flyctl status --app backline-auth-demo

# Fail-closed check: branch/commit/clean tracked files, passing exact CI,
# demo-only Fly config, deployed existing password.
.\scripts\deploy-auth-demo.ps1
```

## Deploy only if preflight passes
```powershell
.\scripts\deploy-auth-demo.ps1 -Deploy
```
This command stamps `BACKLINE_BUILD_SHA` and verifies HTTP 200 with matching build SHA, `status=ok`, and unauthenticated `/api/bands` HTTP 401. Record deployment image, machine health and timestamp.

## Signed-in acceptance after deployment
Using **synthetic** demo accounts at desktop 1280 and mobile 390/320:
1. Exactly four primary navigation destinations and no horizontal overflow.
2. Home next gig title opens the event overview; the event overview returns to Calendar.
3. Calendar event dialog opens show/rehearsal overview; RSVP and availability remain available.
4. Event overview links to Gig Day, setlists and tasks. Stage plot, load-in, contacts and urgent changes remain accessible inside Gig Day or full show production.
5. Managers can reach booking, finance, touring and production from Manage band.
6. Members never see manager-only finance/management destinations or event-edit controls.
7. Band switch and sign-out do not restore previous-band or logged-out private content.

## Rollback
Record the previously running image identifier *before* deploying. If live acceptance fails, redeploy that exact saved image only to `backline-auth-demo`:
```powershell
flyctl deploy . --app backline-auth-demo --config fly.auth-demo.toml --ha=false --image '<VERIFIED-PRIOR-IMAGE>'
```
This does not restore ephemeral SQLite state. Never use real user data in this synthetic demo.

## Acceptance record
- [ ] Exact release HEAD CI passed
- [ ] Preflight passed and previous image recorded
- [ ] Deploy status and build SHA verified
- [ ] Signed-in mobile/desktop flows accepted
