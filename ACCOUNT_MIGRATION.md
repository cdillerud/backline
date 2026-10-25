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
