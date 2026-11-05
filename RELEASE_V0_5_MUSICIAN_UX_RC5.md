# Backline v0.5.0-rc.5 — Musician-first UX authenticated demo release

## Release scope
Deploy **only** to the existing disposable `backline-auth-demo` Fly app. The production `backline` app and separate `backline-visual-preview` remain unchanged. Never use `fly.toml`, mount volumes, expose real private band data or alter the established Fly demo password.

Feature source: `1c99d1e035d9872e0deabb48d1687d4a618c151a`. The release commit will be newer because the deployment script is branch-pinned and this runbook was added. Require passing GitHub Actions on the **exact release HEAD**, not just on the feature source.

## Changes
- Home places the upcoming show and personal tasks before lower-priority band metrics; personal assignments precede other band work.
- Musician-facing navigation labels use Shows and Bandmates; existing destinations and permissions remain intact.
- Gig Day has prominent **Load-in / Showtime / Where / My RSVP** cards using saved records; missing information is labelled rather than invented.
- Schedule explains that it contains shows and rehearsals together. Members do not see a manager-only Add event control.
- Calendar requests reject stale band/session/selection results and expose no previous-band events after switching.
- Tests cover desktop and phone workspace navigation, synthetic authenticated demo, Gig Day essentials and four calendar race conditions; existing security, API, syntax and dependency checks remain enabled.
- API version: `0.5.0-rc.5`; Fly build SHA must match the precise deployed commit.

## Prepare and verify (PowerShell 7)
```powershell
cd C:\Users\ChadDillerud\backline
git fetch origin release/backline-v0.5-musician-ux-rc5
git switch release/backline-v0.5-musician-ux-rc5
git pull --ff-only origin release/backline-v0.5-musician-ux-rc5

# Capture known-good RC4 image identifier and check current state before deploying.
flyctl releases --image --app backline-auth-demo
flyctl status --app backline-auth-demo

# Read-only preflight: clean tracked files, exact branch/SHA, completed CI PASS,
# existing deployed demo secret, isolated config and no mounts.
.\scripts\deploy-auth-demo.ps1
```

Do not continue on preflight failure. No untracked preview configuration should be deleted to force a pass.

## Deploy isolated authenticated demo
```powershell
.\scripts\deploy-auth-demo.ps1 -Deploy
```
The script stamps `BACKLINE_BUILD_SHA` into the image and verifies `/api/health` returns `status=ok` and the matching build SHA; unsigned `/api/bands` must be HTTP 401. Record the machine image and health status.

## Required signed-in visual acceptance
At desktop and phone (320px/390px), using only the existing fictional demo account:
1. Confirm Home shows the next gig, correct personal RSVP, personal assignments before band tasks, and nonessential metrics lower on the page.
2. Open Schedule; select both a gig and rehearsal; verify availability/RSVP and links to Gig Day.
3. Open Gig Day. Ensure four essentials cards show real recorded facts, unavailable values say so, and the refresh and directions actions work.
4. Verify stage plot, setlists, alert acknowledgements, assigned tasks, all six workspaces, menu dismissal and logout.
5. Verify member accounts do not see unauthorized event creation or finance data.
6. Verify no stale old-band content can reappear after switching bands or signing out.

## Rollback
Only use the verified prior RC4 image identifier recorded above:
```powershell
flyctl deploy . --app backline-auth-demo --config fly.auth-demo.toml --ha=false --image '<VERIFIED-PRIOR-RC4-IMAGE>'
```
No persistent database or data rollback is implied. The synthetic demo has no mounted volume. Never test with real private material.

## Gate
- [ ] Exact RC5 release HEAD GitHub CI passing (Playwright, pytest, Node race tests, PowerShell parser, dependency audit)
- [ ] Local and Fly read-only preflight passing
- [ ] Previous image identified
- [ ] SHA and unsigned API verified immediately after deploy
- [ ] Signed-in desktop and mobile acceptance
