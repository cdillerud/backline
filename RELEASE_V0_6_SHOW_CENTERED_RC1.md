# Backline v0.6.0-rc.1 — Show-centered UX (isolated demo)

## Candidate and boundaries
Branch: `release/backline-v0.6-show-centered-rc1`; feature source `920f272d6c94bb0161638cf7a4341d9d01c69ab4`. Deploy **only** to `backline-auth-demo`, preserving `backline` production and `backline-visual-preview`. Do not use real band/private data or attach a volume.

## Changes
- Home, Calendar, Music, Band are the only four main destinations, including the mobile bottom navigation.
- Calendar leads with the next five upcoming dates, then preserves the monthly planning grid; opening a show displays saved essentials and gives direct access to RSVP and Gig Day.
- Management lives behind a separate Manage destination accessible only to authorized managers; treasurers see finances without tour/crew administration.
- Existing Show Packets, Tours, Bookings, Finance, AI Gig Studio, setlists, stage plots and other routes are retained.
- Member calendar editing controls are omitted, while the existing server-side role checks remain authoritative.
- API version `0.6.0-rc.1` and exact Git commit build SHA remain verified.

## Read-only preflight on Windows PowerShell 7
```powershell
cd C:\Users\ChadDillerud\backline
git fetch origin release/backline-v0.6-show-centered-rc1
git switch release/backline-v0.6-show-centered-rc1
git pull --ff-only origin release/backline-v0.6-show-centered-rc1
# Save the CURRENT known-good Fly image identifier before changing anything:
flyctl releases --image --app backline-auth-demo
flyctl status --app backline-auth-demo
.\scripts\deploy-auth-demo.ps1
```
Require a completed successful GitHub Actions CI run for the **exact final release HEAD**. The preflight also requires a clean tracked tree, matching remote head, isolated Fly config and existing deployed secret. Never bypass a failed gate.

## Isolated demo deployment
```powershell
.\scripts\deploy-auth-demo.ps1 -Deploy
```
This verifies `/api/health` reports `status=ok` and the expected `build_sha`, and unsigned `/api/bands` is HTTP 401. No production or preview app changes are authorized.

## Post-deploy signed-in acceptance
At 320px, 390px, tablet and desktop sizes:
1. Four main destinations exactly; no horizontal overflow, focus-trappable overlays, or lost navigation.
2. Home: next gig and assigned personal work first.
3. Calendar: upcoming agenda, monthly calendar, rehearsal availability; open the same show from agenda and grid, respond to RSVP, then open My Gig Day.
4. Gig Day: calls, venue, tasks, setlists, lodging and urgent changes visible appropriately; no fictitious confirmations.
5. Music: library, setlists, performance mode, Gig promotion and media accessible.
6. Band: conversations, personal tasks, notifications, settings accessible.
7. Manager account: separate Manage hub gives booking/touring/venue/production/finance routes. Member cannot see Manage or unauthorized calendar editing; treasurer only sees Finance management.
8. Switch band and log out with pending loads; old-band content must not reappear.
9. Record health SHA, one passing Fly machine and signed-out 401.

## Rollback
Record the verified previous Fly image and re-deploy it to the isolated app ONLY:
```powershell
flyctl deploy . --app backline-auth-demo --config fly.auth-demo.toml --ha=false --image '<VERIFIED-PRIOR-IMAGE>'
```
The synthetic database is ephemeral; rollback does not restore the database. Keep the known-good image reference until signed-in acceptance completes.
