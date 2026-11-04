# Backline v0.5 UX RC2 — isolated authenticated demo release

**Scope:** synthetic-only `backline-auth-demo` Fly app. **Do not deploy to `backline` production or `backline-visual-preview`.**  
**Frozen source:** integration commit `1f926ac4d8a5865b12c0dfe81bf71778398249ce`, full CI #1174 PASS.  
**Release branch:** `release/backline-v0.5-ux-rc2`; deploy the **exact final release-branch HEAD** only after its own CI passes.  
**Release PR:** draft validation PR against integration, not production.

## What's new relative to deployed Gig Day RC1
- Less dashboard chrome: tighter typography, card spacing and standardized controls across all six primary workspaces.
- Next Gig hero with date, time, venue, **My Gig Day** and RSVP actions before summary counters.
- Action-first Home layout: visible outstanding tasks, upcoming calendar items and personal attendance; at most three next events on the overview.
- Optional production-readiness details in an accessible expandable disclosure, keeping setlists and tasks visible.
- Tablet sidebar buttons retain explicit accessible labels even when the visual labels are hidden; mobile context navigation marks current destination.

No new API, schema, public-account capability, secret, or customer data migration is introduced by the UX changes.

## Deploy with Windows PowerShell 7
Prerequisites: the existing Backline working copy, authenticated `gh` and `flyctl`, and a **working synthetic demo login**. The demo database has no persistent volume and may reset when Machines are replaced.

```powershell
cd C:\Users\ChadDillerud\backline
git fetch origin release/backline-v0.5-ux-rc2
git switch release/backline-v0.5-ux-rc2
git pull --ff-only origin release/backline-v0.5-ux-rc2

# Checks clean tracked working tree, branch/remote SHA, green CI, target app and no mount.
.\scripts\deploy-auth-demo.ps1

# Deploy only if preflight passes and RC2 was authorized for the demo.
.\scripts\deploy-auth-demo.ps1 -Deploy
```

If the working copy contains local modifications, preserve them with a scoped stash or use a clean worktree. **Do not reset or discard local changes** to bypass preflight.

Before deploying, capture the current isolated demo image, because RC1 is already live:

```powershell
flyctl releases --image --app backline-auth-demo
flyctl status --app backline-auth-demo
```

The script builds with `BACKLINE_BUILD_SHA`, requires a passing CI result for its exact HEAD, verifies `/api/health` reports the matching SHA, and requires HTTP 401 on signed-out `/api/bands`. It does **not** validate successful demo login.

## Signed-in acceptance
1. Confirm the synthetic owner can sign in (do not share or paste the password). Verify Home loads.
2. Check Next Gig and My Gig Day buttons and event RSVP dialog.
3. On mobile 320/390px, verify no sideways scroll, usable cards, bottom navigation and the collapsed production disclosure.
4. Expand and close production snapshot; verify recorded details are available and tasks/setlists remain accessible.
5. Open Music, Schedule, Shows & Tours, Band and Business (manager role), confirming each route and global tools remain usable.
6. Verify Gig Day, on-stage setlist, logout and sign-in again.

## Rollback
If authenticated smoke tests fail, redeploy the **verified prior RC1 image** identified above, to `backline-auth-demo` only:

```powershell
flyctl deploy . --app backline-auth-demo --config fly.auth-demo.toml --ha=false --image '<PRIOR-VERIFIED-RC1-IMAGE>'
```

Image rollback does not restore SQLite data or secret state. Do not assume synthetic data will survive Machine replacement. This demo is not approved for real accounts, private documents, or commercial use.

## Evidence
- Source integration CI #1174 full suite: PASS.
- Authenticated browser and viewport assertions on source: PASS.
- Chromium screenshots reviewed at 320px and 1280px. Full responsive synthetic artifact `gigday-responsive-synthetic` from CI #1174.
- **Release branch final-head CI and post-deploy signed-in acceptance still required.**
