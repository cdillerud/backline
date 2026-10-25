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
