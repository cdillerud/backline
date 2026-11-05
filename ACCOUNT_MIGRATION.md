# Account-mode migration gate

`BACKLINE_ACCOUNTS_ENABLED` is **OFF** by default. The current Fly private-preview app remains unchanged.

## Implemented
- Login API with scrypt password hashes and randomly generated, hashed bearer sessions
- Logout endpoint invalidating the active session
- Browser login and logout views; session held in tab-scoped sessionStorage
- Role and band-scoped API access checks for finance, booking, marketing
- Cross-band denial tests, member write-denial tests, logout revocation tests

## Production blockers
1. No secure first-owner bootstrap or invitation management. **Do not set BACKLINE_ACCOUNTS_ENABLED=1 on Fly.** The owner would be locked out.
2. Existing SQLite band records must be explicitly claimed by a verified account. Never grant unclaimed bands to the first person who signs up.
3. Require rate-limited login attempts and account recovery; browser bearer tokens need security review (prefer HttpOnly, Secure, SameSite cookies plus CSRF controls).
4. Add authenticated role matrix tests for every endpoint and nested resource.
5. Backup and restore the existing mounted SQLite DB, then dry-run schema migration on a *copy* in isolated staging.
6. Add invitation acceptance, membership revocation, password reset and expiration.
7. Staging QA with a real browser; current automated checks cover API and JavaScript syntax but not a complete browser journey.
8. Ensure HTTPS, caching, restrictive CSP and audit trail for privileged operations.

No external OAuth, email sending, public account registration or social posting is enabled in this branch.

## Verified on-host snapshot utility
For a running deployment, obtain a consistent SQLite backup using the SQLite online backup API:
```sh
python -m src.backup_db \\
  --source /data/backline.db \\
  --destination /data/backline-snapshot-YYYYMMDD-HHMM.db
```
This prints the absolute path, byte count, SHA-256 hash, and integrity result. The utility refuses to overwrite previous snapshots. The snapshot is **on the same Fly volume** until transferred elsewhere. It is not disaster recovery by itself.

Before release, establish an encrypted off-site destination, a lifecycle/retention policy, periodic scheduling, alerting, and a rehearsed restore on an isolated machine. Never publish snapshots or secrets into the GitHub repository.

## Explicit owner setup (staging only)
After the account schema is initialized against a *backup copy* and verified, an administrator may run:
```sh
BACKLINE_DB=/path/to/staging.db \\
BACKLINE_OWNER_EMAIL=owner@example.com \\
BACKLINE_OWNER_NAME='Band Owner' \\
BACKLINE_OWNER_PASSWORD='<secure unique password>' \\
python -m src.bootstrap_owner --band-id 1
```
Do not paste a real password into shell history; the inline form above is for documentation only. Prefer a secure secret injection method or an interactive prompt wrapper. The command refuses unknown bands, pre-owned bands and existing user email addresses. It does not assign ownership to all bands. It is not suitable for production until the administrator identity and existing records are verified.

## Staging-only invitations
- An authenticated band owner or manager can POST `/api/bands/{band_id}/invitations` with an email and role. The response contains a one-time token for **manual delivery**. Automatic emails are not configured.
- `POST /api/auth/accept-invite` with token, matching email, display name and a new password creates an account and membership. Tokens expire in seven days; only token hashes are stored.
- Managers cannot invite other managers or owners; owner accounts cannot be created through the invitation endpoint.
- Existing-user invitations intentionally return a conflict for now, rather than altering an existing account without authentication.
- Before production release, implement invite revocation, email delivery and confirmation, existing-user acceptance, anti-abuse controls and a secure invite UX. Treat returned invite tokens like credentials.

## Owner-assisted member recovery (staging)
An authenticated band owner can request a one-time, 30-minute recovery code using `POST /api/bands/{band_id}/account-recovery` with a member email. The owner must verify the requester's identity through a trusted channel before sharing this code. The response contains the token once, for secure manual delivery; **there is no email integration**. Any public exposure of the code allows an account takeover.

A user can redeem a valid token using `POST /api/auth/recover` with `token` and `password`. Redemption invalidates all existing sessions and deletes outstanding recovery codes for that account. Expired tokens, reused tokens and tokens superseded by a new issuance are rejected. Owners cannot reset other owners through this flow.

**Production blockers:** verified out-of-band identity confirmation, recovery audit events, delivery channel, access to the recovery UX, per-user and per-IP throttling, and a separate high-assurance owner recovery process. Do not activate account mode in production solely on the strength of passing API tests.

## Rehearsal on a representative database
Run on a machine with the exact intended release code and Python dependencies:
```sh
python -m src.rehearse_migration --source /path/to/existing/backline.db
```
This reads the source, makes a verified snapshot in a temporary directory, invokes schema initialization on that copy and checks that row counts of preexisting tables are preserved, expected feature tables exist, and SQLite integrity checks pass. It prints a summary, not a migrated production database.

**Limitations:** The current check compares table row counts, not every existing cell value or every foreign-key relationship, and assumes schema initialization is additive. Do not treat a passing rehearsal as complete data-integrity certification. Before any production rollout, perform a representative full-data diff, `PRAGMA foreign_key_check`, application workflow tests, browser acceptance testing, offsite backup confirmation and a timed recovery drill. No live volume was accessed by the CI test.
