# Backline — Band and Touring Management

Backline is a private development preview for band workspaces, shows, booking,
production packets, stage plots, touring itineraries, repertoire and finances.
The v0.4 integration branch is **not approved for commercial production use**.

## Local development with synthetic data

```bash
python -m pip install -r requirements-dev.txt
BACKLINE_LOCAL_DEV=1 BACKLINE_DEMO_SEED=1 BACKLINE_DB=/tmp/backline-demo.sqlite python -m uvicorn src.app:app --host 127.0.0.1 --port 8000
```

The demo seed creates fictional band/show information. Never enable the local
access bypass on publicly exposed hosting or use the demo for real private data.

## Checks

```bash
python -m playwright install --with-deps chromium
BACKLINE_LOCAL_DEV=1 python -m pytest -q
node --check src/static/app.js
python -m pip_audit -r requirements.txt
```

GitHub Actions runs API and Chromium tests, dependency auditing and syntax checks.
See [DEVELOPMENT.md](DEVELOPMENT.md) for current changes, compatibility and remaining
work, and [PRODUCT_ROADMAP.md](PRODUCT_ROADMAP.md) for release gates.

## Preview hosting

[PREVIEW_DEPLOY.md](PREVIEW_DEPLOY.md) describes the isolated, disposable
`backline-visual-preview` deployment using `fly.preview.toml`. This development
workflow never merges to or deploys production. Individual account mode is opt-in
and requires independent security and recovery certification before real use;
shared preview credentials are not per-member authorization.
