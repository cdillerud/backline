# Backline 0.6.0-rc.5 — isolated authenticated demo deployment

**Target:** `backline-auth-demo` only. Never deploy to production or `backline-visual-preview` using this runbook.

## Included in RC5

- Show-first Home / Calendar / Music / Band navigation and role-aware Show overview inherited from RC2.
- Phone safe-area bottom padding, visible keyboard focus, and minimum 48px primary touch targets.
- Seven responsive owner/member acceptance cases at 320, 390, 768, and 1280px.
- Show overview displays linked setlist titles and only the current musician’s open assigned tasks with due dates.
- Wide desktop canvas (including 1920px and 2560px), larger call times and readable show cards with preparation/logistics hierarchy. Phone/tablet behavior remains unchanged.
- A separate CI gate for show-first browser tests, with the full suite still running once.

## Release identity

- Branch: `release/backline-v0.6-show-first-rc5`
- Version: `0.6.0-rc.5`
- **SHA:** obtain the actual final branch HEAD; never substitute an older feature-branch green run.
- Only proceed when GitHub Actions `Backline CI` **completed success** on that exact SHA.

## PowerShell 7 — local preflight, no deployment

```powershell
cd C:\Users\ChadDillerud\backline
git fetch origin release/backline-v0.6-show-first-rc5
git switch release/backline-v0.6-show-first-rc5
git pull --ff-only origin release/backline-v0.6-show-first-rc5
git status --short
git rev-parse HEAD
flyctl releases --image --app backline-auth-demo
flyctl status --app backline-auth-demo
.\scripts\deploy-auth-demo.ps1
```

Save the **exact prior immutable image** shown by Fly, for rollback. The release script checks the branch, exact remote SHA, clean tracked files, CI success, demo-specific Fly config and existing deployed password; it never creates or replaces a demo password.

## Deploy after all preflight checks pass

```powershell
.\scripts\deploy-auth-demo.ps1 -Deploy
```

The script checks the deployed build SHA, health status and that an unsigned call to `/api/bands` is denied (401). Do not claim release success until those checks pass.

## Signed-in visual acceptance — disposable demo data only

1. On 320/390px phones, inspect Home, Calendar, Music, and Band bottom tabs for visible and reachable 48px controls, safe-area clearance, keyboard focus and no horizontal overflow.
2. On 768/1280px tablet/desktop, verify desktop navigation is shown and mobile navigation hidden. At 1920px and 2560px, confirm the show overview uses the available canvas without sideways scrolling, enlarged call-time cards are readable and action rows stay accessible.
3. As member and owner, open a gig from Calendar to Show, confirm time/venue are only populated when stored, linked setlist titles appear, and the member sees their own tasks without showing another member’s assignments; then enter Gig Day and return.
4. Check personal RSVP, setlists and show tasks. Members cannot see owner/manager Manage, billing or private financial data.
5. Owners can access management, guest operations and show production. Cross-band and stale-response guards must hold.
6. Sign out during a pending private request; ensure no private content reappears.
7. Check mobile overflow, focus order, calendar event details and task actions.

## Rollback

Use only the immutable image recorded before release:

```powershell
flyctl deploy . --app backline-auth-demo --config fly.auth-demo.toml --ha=false --image '<VERIFIED-PRIOR-IMAGE>'
```

The synthetic SQLite database is disposable, with no attached persistent Fly volume. Image rollback does not restore DB contents.

## Release gates

- [ ] Exact RC5 final SHA has completed passing GitHub Actions CI
- [ ] Local preflight passes; previous immutable Fly image recorded
- [ ] Deploy verifies exact build SHA, healthy endpoint and private unsigned 401
- [ ] Signed-in phone, tablet and desktop acceptance passes
