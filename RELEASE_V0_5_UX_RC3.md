# Backline v0.5 UX RC3 — release and deployment runbook

**Deployment scope:** `backline-auth-demo` only (isolated, synthetic-data Fly demo). **Not** the `backline` production app or `backline-visual-preview`. No production merge, real-account migration or confidential data.

**Feature source:** frozen integration commit `12cdba5f0ea98f399a0e3e3e1ff86487b19e0c0b`; Backline CI #1214 PASS.  
**Release branch:** `release/backline-v0.5-ux-rc3`. Run its own **final HEAD CI**; do not deploy a newer commit using an older check.

## Changes from the live UX RC2

- Header now retains Notifications and My Tasks while Account groups Band Settings, Join band, optional installation and Sign out.
- Home keeps one manager Add event control, with Add song/Music/Schedule/Conversations in a compact More actions menu. All existing routes remain intact.
- The featured gig owns its RSVP status and immediate Gig Day/RSVP buttons. Other upcoming events and Other RSVPs omit this featured gig. Next show preparation retains production/setlist/tasks without repeating the featured gig heading.
- Assigned personal tasks lead the attention feed before other band tasks. All underlying task records and permissions are unchanged.
- Menu Escape restores focus and outside clicks close transient menus.
- New synthetic demo data uses the band's `America/Chicago` calendar date rather than the server's UTC date; Python `tzdata` is bundled for container reliability. **Existing dates are never rewritten on app restart.** Because the authenticated demo has no volume, newly generated sample dates may change when the demo database is recreated. The sidebar explains this.
- API version now reports `0.5.0-rc.3`; deployment health also exposes the exact commit via `BACKLINE_BUILD_SHA`.
- Release script fixes a PowerShell array matching issue that could falsely claim an existing Fly secret was missing. It fails closed on secret-list network errors and never requests the secret merely because the CLI printed several lines.

## Safe deployment using PowerShell 7

Use the existing Windows checkout with authenticated `git`, `gh` and `flyctl`.

```powershell
cd C:\Users\ChadDillerud\backline
git fetch origin release/backline-v0.5-ux-rc3
git switch release/backline-v0.5-ux-rc3
git pull --ff-only origin release/backline-v0.5-ux-rc3

# Preserve the currently live RC2 image identifier for recovery.
flyctl releases --image --app backline-auth-demo
flyctl status --app backline-auth-demo

# Preflight verifies the remote branch SHA, clean tracked tree,
# completed passing GitHub CI on this exact release commit,
# destination app, and absence of volume mounts.
.\scripts\deploy-auth-demo.ps1

# On explicit go-ahead, deploy to the synthetic authenticated demo only.
.\scripts\deploy-auth-demo.ps1 -Deploy
```

The script prompts for a demo password **only if Fly confirms that no `BACKLINE_DEMO_PASSWORD` secret exists**. Never disclose passwords in chat, a commit, or terminal arguments. Existing deployed Fly secrets should not be reimported. Stop on any DNS/secret-list failure rather than attempting a reset.

If the local tracked tree is dirty, preserve modifications with a scoped stash or clean worktree. Do not discard local files to bypass preflight.

## Acceptance after deployment

1. Confirm the machine reports one passing health check.
2. Confirm `/api/health` returns `status=ok`, `version=0.5.0-rc.3` and the exact RC3 release commit as `build_sha`.
3. Confirm unauthenticated `/api/bands` returns HTTP 401, and the synthetic demo owner can sign in using the existing demo secret.
4. At desktop and phone widths, inspect one Next Gig with its factual own RSVP; its title must not repeat in the Coming Up or Other RSVPs cards.
5. Test Add event, More actions → Add song, Account → Band Settings, Account → Sign out, including Escape/keyboard and outside-click menu dismissal.
6. Test personal task prioritization, My Gig Day, setlist/performance view, production disclosure, and navigation across all six workspaces.
7. Confirm synthetic dates reflect Central Time when the demo DB was initialized. Do not interpret the fictional schedule as a real commitment.

## Recovery

Before deployment, save the known-good RC2 image digest from `flyctl releases --image --app backline-auth-demo`. If live signed-in acceptance fails, redeploy that **verified prior image** to the isolated target only:

```powershell
flyctl deploy . --app backline-auth-demo --config fly.auth-demo.toml --ha=false --image '<VERIFIED-PREVIOUS-RC2-IMAGE>'
```

A rollback of the image cannot restore a disposable SQLite database or secret state. The demo has no permanent volume and must never contain real band financial, tax, private-rooming or contract records.

## Evidence

- Feature-source integration CI #1214 passed authenticated demo, responsive Gig Day and on-stage browsers, full regression, JS syntax, dependency audit and Python compilation.
- Synthetic desktop and 320px Chromium screenshots inspected; no horizontal clipping and featured gig was removed from repeated panels.
- **Release branch exact-commit CI and post-deploy signed-in acceptance are separate gates**. No production rollout is authorized.
