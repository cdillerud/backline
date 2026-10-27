# Backline authenticated visual demo — isolated deployment runbook

Status: development only. **Never use the existing backline-visual-preview database for authenticated demo bootstrap.** Do not deploy this to production.

## Release prerequisites
1. GitHub Actions must pass on the exact integration-branch commit.
2. Use a **separate** Fly.io app (suggested name: backline-auth-demo), with an empty dedicated disposable database. Never reuse an existing app volume or copy user/band SQLite data.
3. The existing visual preview's Basic Auth settings do not automatically apply to the separate app. The new app relies on Backline individual-account authentication; limit access to authorized testers and do not advertise its URL. Review whether an additional edge authentication gate is required before wider sharing. Protect demo credentials; no credential values in Git, documentation, screenshots, or shell history.
4. The generated Fly config must point to the new app, use the repository-relative Dockerfile, omit all mounts, and set `BACKLINE_DB=/data/backline.db`. This is ephemeral test data by design.
5. Supply `BACKLINE_DEMO_PASSWORD` using a Fly secret. Require a randomly generated password of at least 12 characters.
6. Set `BACKLINE_DEMO_SEED=1`, `BACKLINE_DEMO_ACCOUNTS=1`, `BACKLINE_ACCOUNTS_ENABLED=1` only for the separate synthetic app. Leave public sharing, email providers, and external marketing disabled. Do not enable `BACKLINE_LOCAL_DEV` publicly.

## Acceptance gates
- API health passes; server identifies the expected release.
- Signed-out requests to private band APIs return 401.
- The designated synthetic owner can sign in and view only the seeded demo band's discussion and RSVP data.
- A restart neither creates extra accounts nor duplicates demo data.
- Synthetic demo login credentials are not reused elsewhere.
- Desktop and mobile browser smoke tests pass.
- No real band, user, contract, payment or guest data is introduced.

## Rollback
Do not migrate or import data into this disposable app. Roll back to the prior image or delete the isolated demo app if the new release fails; preserve the existing `backline-visual-preview` machine and configuration.

## Known limitations
The authenticated bootstrap intentionally rejects existing non-demo datasets. It currently seeds a single owner and one discussion/RSVP; richer member roles, messaging, full mobile acceptance, and operational security review remain outstanding. A passing HTTP health check alone does not prove UX acceptance.

## Operator sequence — Windows PowerShell (never production)

Only after the exact commit's GitHub CI succeeds:

```powershell
cd C:\Users\ChadDillerud\backline
git fetch origin
git switch integration/backline-v0-4-rc
git pull --ff-only origin integration/backline-v0-4-rc
git status --short
flyctl auth whoami
flyctl apps list
```

Check that `backline-auth-demo` does not already exist. If it does, stop and verify ownership, database contents and config; do not reuse it blindly. Then:

```powershell
flyctl apps create backline-auth-demo --org personal
```

Use the Fly dashboard's secure Secrets page for **this new app only** to configure `BACKLINE_DEMO_PASSWORD` with a freshly generated, unique 20+ character password. Do not paste it into chat or a committed file. Confirm it is set in the new app before deploying. Do not set the owner demo password in any other Fly app.

```powershell
flyctl deploy . --app backline-auth-demo --config .\fly.auth-demo.toml
flyctl status --app backline-auth-demo
flyctl logs --app backline-auth-demo
```

Because no volume is attached, Fly machine replacement may reset the demonstration data and invalidate active sessions. It is not a persistent database strategy. Deployment without a password secret is expected to fail closed, not fall back to an insecure default.

### Verification

Open the new app's HTTPS URL; the initial view must show individual-account login. `/api/health` may be public, but `/api/bands` must deny unsigned requests. Sign in with `demo-owner@example.test` and the newly generated secret; check Band Hub conversations/RSVP, Schedule rehearsal, Music songs/setlist, and Shows & Tours. Sign out and verify private records are no longer accessible. Do not share the new demo with real bands or enter real information.

**No background or automatic deployment occurs from adding this configuration.**
