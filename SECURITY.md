# Security and deployment policy

## Current risk
Backline v0.1.1 uses a single shared Basic Auth password as a **private preview gate**. All users of that password can access all band records. The database includes band finances and member contact information. Do not invite unrelated bands, upload sensitive records, or treat this as a multi-tenant production service.

## Minimum controls before public release
- Account authentication, per-band authorization and invitations.
- Explicit policy for manager, treasurer, member, guest and former member roles.
- Server-side authorization on all endpoints, not just hiding buttons.
- Secure sessions with CSRF defenses, rate limiting and anti-enumeration protections.
- Immutable audit history for financial activity.
- Data retention and export/delete lifecycle.
- Encrypted off-site backups with restore drills and an incident-response procedure.

## Fly deployment safeguards
- Store preview credentials only with Fly secrets.
- Keep BACKLINE_LOCAL_DEV disabled in Fly.
- Persist SQLite at /data/backline.db on the attached volume.
- A volume is a single-machine persistence layer, not a backup. Never scale SQLite to two independent writers.
- Avoid automatic production deployment for schema changes. Review migration and backup evidence first.
- Use staging for all authentication and accounting changes.

## Reporting vulnerabilities
Open a private security advisory or contact the repository maintainer. Do not publish working exploits or secrets in GitHub issues.

## Experimental account work (v0.2 branch)
The account middleware, membership tables and bearer-token endpoints are **API-only development infrastructure**. The existing browser frontend does not have a login flow, logout flow, token storage strategy, invitations or account recovery. Do not enable `BACKLINE_ACCOUNTS_ENABLED` in the deployed Fly service: doing so would break the current frontend.

Tests create sample users directly in an isolated temporary database. There is no public self-registration or administrator bootstrap command. Before promoting account mode, add a secure one-time owner-claim process for legacy bands, manager-controlled invitations, secure browser sessions (prefer HttpOnly cookies with CSRF protections), and an explicit migration/recovery plan.

Do not merge the current branch or deploy it until these release blockers are resolved.
