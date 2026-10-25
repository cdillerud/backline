# Backline — Band Management

Backline manages bands, gigs, rehearsals, songs, setlists, members, and band finances.

## Deployment status
**Scaffold only — not deployed yet.** This repository currently contains Fly.io and Docker configuration and CI scaffolding, but the application source in `src/` and tests must still be uploaded from the **Backline v0.1.1 deploy-ready** archive. Deployment cannot succeed until that step is complete.

## Local setup (after source upload)
```bash
pip install -r requirements.txt
BACKLINE_LOCAL_DEV=1 python -m uvicorn src.app:app --port 8000
```
Local-development bypass must never be enabled on publicly exposed hosting.

## Hosting
See [DEPLOY.md](DEPLOY.md). Intended host: Fly.io, one 512 MB VM, one persistent volume for SQLite, HTTPS, preview Basic Auth credentials in Fly secrets.

## Important security note
The MVP does not yet have per-member accounts or financial authorization. Do not use it to store real financial or private band data until those controls and independent backups are in place.
