# Backline v0.5 — Gig Day RC1

**Status:** Deployable release candidate for the **isolated synthetic authenticated demo**, not a public-production release.  
**Release branch:** `release/backline-v0.5-gigday-rc1`  
**Source:** frozen from integration commit `2f7e2c8bfa0f8e3f097e3c106c4ab929988c668a` (Backline CI #1154 PASS); the release script and this document are the only intended release-branch changes.  
**Target:** `backline-auth-demo`, using `fly.auth-demo.toml` and its **disposable no-volume synthetic SQLite** data.  
**Never deploy with:** `fly.toml`, app `backline`, or an existing production-data Fly volume.

## Included
- Band Home with scoped summaries and real conversation/event links
- Musician Gig Day: calls, contact/venue directions, recorded timeline and overnight offsets, RSVP, personal tasks, setlists, stage and inputs, linked room details and urgent acknowledgements
- Compact responsive priority checklist and field-ready one-screen navigation
- Performance view with scalable song titles, next-up cue, running-order navigation and optional best-effort screen wake lock
- Browser-printable call sheet, transparent refresh/offline state, member/manager isolation and safe band-switch behavior

## Deploy from PowerShell 7

Prerequisites: git, `gh`, `flyctl`; authenticated to GitHub and Fly. The target Fly app may already exist. **Use no real customer, guest, financial, or sensitive band data in the disposable demo.**

```powershell
git clone https://github.com/cdillerud/backline.git
cd backline
git fetch origin release/backline-v0.5-gigday-rc1
git switch release/backline-v0.5-gigday-rc1
git pull --ff-only origin release/backline-v0.5-gigday-rc1

# This performs an exact-HEAD CI/branch/config check; it does not deploy.
./scripts/deploy-auth-demo.ps1

# After verifying the preflight and making sure the isolated demo password is
# staged as BACKLINE_DEMO_PASSWORD on the correct Fly app:
./scripts/deploy-auth-demo.ps1 -Deploy
```

If the isolated app does not yet exist, use `-Deploy -CreateApp`; the script **stops after creation** and requires a separate pass to securely configure the password. Do not put passwords in terminal command arguments, repository files or chat. Credentials for a prior isolated demo may remain in Fly secrets and are not automatically replaced. On first deploy the script may require a securely prompted password.

The script checks the working tree, release branch and remote commit, a **passing CI run for the exact SHA**, and the no-volume target app. It deploys with `--ha=false` and `BACKLINE_BUILD_SHA` embedded in the image, then verifies the public health response matches the deployed SHA and private `/api/bands` denies signed-out access with HTTP 401.

### Post-deploy acceptance
1. Confirm `https://backline-auth-demo.fly.dev/api/health` reports `status=ok` and the exact deployed commit SHA.
2. Confirm signed-out `/api/bands` returns HTTP 401.
3. Log in with the **existing synthetic demo account** through the normal demo login UI. Never use real staff credentials.
4. At 320–390px, check Band Home → upcoming show → Gig Day, call times, sticky actions, RSVP, task completion and return navigation. Review timeline, stage plot and setlist.
5. At desktop width, open the on-stage performance dialog, test next/previous song, running order, font size and optional wake lock (if supported), then close.
6. Check print preview hides application navigation and contains the call sheet and expanded recorded details.
7. Check logout and band changes do not display the previous band's private records or leave stage dialogs open.

### Rollback and recoverability

Before deploying, capture the existing isolated demo image from:

```powershell
flyctl releases --image --app backline-auth-demo
flyctl status --app backline-auth-demo
```

If the release fails functional checks, redeploy the **known-good prior image** after confirming its digest from the release list:

```powershell
flyctl deploy . --app backline-auth-demo --config fly.auth-demo.toml --ha=false --image '<PRIOR-VERIFIED-IMAGE>'
```

An image rollback does **not** restore SQLite content, secrets or schema. This particular app deliberately has no volume and only synthetic data; it may reset on Machine replacement. Do not treat rollback as data recovery. Stop deployment if the app unexpectedly has a volume or contains non-demo data.

### Not included / not approved
Real production launch, new public accounts, real email/push delivery, confidential contracts/tax or banking data, payment processing, production migration, data backups or offsite restore are outside RC1. Product security and long-term data recovery gates remain before a commercial release. This release does not touch `backline` production or `backline-visual-preview`.

## Release validation
- Source integration commit `2f7e2c8`: CI #1154, authenticated demo acceptance, five-width mobile and three-width performance browser checks, full regression suite, JS syntax, dependency audit and Python compilation — all PASS.
- Release branch: **must have its own passing CI at the final release commit** before executing `-Deploy`. The deployment preflight checks that automatically.
- Human/device acceptance occurs **after** isolated deployment; a green synthetic Chromium test does not claim genuine phone-device acceptance.
