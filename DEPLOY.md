# Fly.io private preview deployment

**Not production-ready.** This version has a shared Basic Auth password, not user-level permissions or band isolation. Do not store sensitive financial records before tenant authorization and tested backups are implemented.

1. Upload all Backline v0.1.1 source files to this repository.
2. Install flyctl and run `fly auth login`.
3. Run `fly launch --no-deploy`, choosing a unique app name and Chicago region (ord).
4. Run `fly volumes create backline_data --region ord --size 1`.
5. Run `fly secrets set BACKLINE_PREVIEW_USER=... BACKLINE_PREVIEW_PASSWORD=...`. Never put passwords in GitHub or fly.toml.
6. Run `fly deploy`, then `fly status`.

Use just one Fly Machine with its attached volume for SQLite. Keep `BACKLINE_LOCAL_DEV` disabled on the public internet. Configure off-site backups and recovery testing before storing financial data. Hosting charges start only once you provision service resources.
