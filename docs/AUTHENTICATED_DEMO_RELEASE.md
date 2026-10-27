# Backline authenticated visual demo — isolated deployment runbook

Status: development only. **Never use the existing backline-visual-preview database for authenticated demo bootstrap.** Do not deploy this to production.

## Release prerequisites
1. GitHub Actions must pass on the exact integration-branch commit.
2. Use a **separate** Fly.io app (suggested name: backline-auth-demo), with an empty dedicated disposable database. Never reuse an existing app volume or copy user/band SQLite data.
3. Keep the existing Basic Auth preview gate. Protect demo credentials; no credential values in Git, documentation, screenshots, or shell history.
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
