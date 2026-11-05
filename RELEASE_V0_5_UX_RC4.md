# Backline v0.5 UX RC4 — isolated authenticated demo release

## Scope and freeze
- Deploy **only** to `backline-auth-demo` using `fly.auth-demo.toml`.
- Do **not** deploy to `backline` or `backline-visual-preview`, merge production, attach a volume, reuse production data, or enable external publication.
- Source base: `e7ae0ea4cc416d10f5c4046504ba9fd4b84e2ef5` from `integration/backline-v0-4-rc`. Release script is pinned to `release/backline-v0.5-ux-rc4`.
- **Deploy the exact final release HEAD, not the integration base.** Require a passing completed GitHub Actions CI run for that HEAD.

## Release changes
- Keeps the musician-first Home, Account, Gig Day and six-workspace v0.5 UX.
- Prevents stale AI Gig Studio and Tours network responses from overwriting data or unexpectedly redirecting users after a band, session, selection, or navigation change.
- Clears an outdated route when the selected tour is cleared.
- Escapes the event type in the event-table renderer.
- Adds a seven-scenario synthetic Node request-isolation regression executed in CI.
- Stamps the built Docker image with the exact Git SHA and checks that `/api/health` reports the same SHA after deployment. The deployment fails closed on mismatch.

## Release preparation (PowerShell 7)
```powershell
cd C:\Users\ChadDillerud\backline
git fetch origin release/backline-v0.5-ux-rc4
git switch release/backline-v0.5-ux-rc4
git pull --ff-only origin release/backline-v0.5-ux-rc4

# Capture the running, known-good image before making any change.
flyctl releases --image --app backline-auth-demo
flyctl status --app backline-auth-demo

# Read-only safety and exact-source-CI preflight:
.\scripts\deploy-auth-demo.ps1

# Only after the preflight passes and the previous image is recorded:
.\scripts\deploy-auth-demo.ps1 -Deploy
```

The script requires clean tracked files, the correct branch and matching remote SHA, passing CI on the exact final release HEAD, an isolated Fly config without mounts, and an existing deployed demo password. It does not request or overwrite the secret. A successful deploy must report HTTP 200, `status=ok`, matching `build_sha`, and unauthenticated `/api/bands` HTTP 401.

## Signed-in acceptance — required after deployment
Use the existing synthetic demo owner login only (do not paste credentials into chat). At desktop and phone widths:
1. Verify Home shows a single featured Next Gig with truthful own RSVP, no duplicate in Coming Up/Other RSVPs, and useful personal-task ordering.
2. Navigate all six workspaces; use Account → Band Settings and Sign out.
3. Use Calendar → event/show and a rehearsal availability response, checking that navigation preserves band selection.
4. Open a Gig Day, show production, stage plot and setlist, and verify mobile scrolling and call time visibility.
5. Switch bands while Studio or Tours is loading; confirm no old-band content appears. Sign out during a pending request; no private content should reappear.
6. Confirm all content is fictional and no real band tax, contract, rooming, finance or member records are included.

## Recovery
Record and preserve the currently running image ID **before** deployment. If signed-in checks fail, redeploy that verified prior image to `backline-auth-demo` only:
```powershell
flyctl deploy . --app backline-auth-demo --config fly.auth-demo.toml --ha=false --image '<VERIFIED-PRIOR-IMAGE>'
```
A source rollback cannot restore ephemeral demo DB state or secrets. Never use real private records in this app.

## Final certification checklist
- [ ] CI passes on exact release HEAD (including the seven new Node scenarios, full pytest suite, Playwright, JS syntax, pip-audit and PowerShell parse).
- [ ] No local tracked file changes; Fly app, secrets and config inspected successfully.
- [ ] Prior running image recorded.
- [ ] Deployment SHA and signed-out private API verified.
- [ ] Signed-in desktop and mobile acceptance completed.
