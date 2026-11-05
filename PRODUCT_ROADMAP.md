# Backline — Product roadmap

## Vision
The operations home for working bands and touring acts. No classifieds, no musician matching. A band can manage the entire lifecycle of a show: inquiry → offer → agreement → availability → logistics → performance → settlement → reporting.

## Product principles
1. **One source of truth per band.** Workspaces are private, each user can belong to more than one band.
2. **Money must reconcile.** Monetary amounts are integer cents; adjustments are auditable and payments are never silently deleted.
3. **Mobile at the gig, desktop for planning.** Stage-friendly setlists, quick schedule access and offline-readiness are central UX requirements.
4. **No surprise costs.** Cost-aware deployments, exportable data, owner-controlled backups, optional premium functionality.
5. **The member experience matters.** Availability requests and payouts should require as few steps as possible.

## Release gates

### P0: secure multi-band foundations (required before inviting external users)
- Individual user accounts: securely hashed passwords or OIDC, account recovery, logout, session expiry.
- Invite-based membership with active/revoked memberships and separate manager, treasurer and musician roles.
- Server-side authorization on **every** band-scoped read and write; tests must demonstrate cross-band denial.
- CSRF protection for cookie sessions, login rate limiting and audit logging for privileged actions.
- Migration plan for existing single-band demo workspaces; do not automatically expose existing data to new accounts.
- Off-site encrypted SQLite backups and a tested restore drill. One Fly volume is not a backup.
- Private-by-default handling of tax, banking, contract and member contact information.
- Automated CI checks and a private staging environment. No production migration without a rollback plan.

### P1: professional workflow
- Gig pipeline: inquiry, tentative, offered, contracted, confirmed, completed, canceled.
- Availability polling, calendar feeds, venue contacts, contract attachments, load-in/soundcheck details.
- Setlist builder: reorder, duplicate, song transitions, total runtime, per-show overrides and printable PDF.
- Rehearsal agendas, attendance, song readiness, assignments.
- Financial ledger: categorized income and expenses, member contributions, receipts, reimbursements.
- Custom settlement rules: flat fees, substitutes, manager fees, reserve, percentage and equal splits.
- Settlement lock after approval with authorized adjustment history; explicit paid/pending amounts.
- Band-specific report exports and monthly reconciliation.

### P2: professional operations and growth
- Merchandise SKUs, inventory, cost of goods sold and show-level sales.
- Equipment, stage plots, input lists, technical rider and document history.
- Tour routing, lodging, travel budgets, contacts and per diem tracking.
- Event-to-event templates and notification preferences.
- Multi-band account UX with consistent role switching, reusable repertoire templates.
- Integrations: calendar, payments (only after compliance review), accounting exports and cloud storage.

## Current implementation
- v0.1.1 live private preview: gigs/rehearsals, members, songs, setlists, SQLite transaction ledger, equal settlement splits.
- `feature/finance-integrity-v0-2`: reconciliation safety fixes and regression tests.
- **Not production ready.** Shared preview credentials do not provide member-specific access. No automated disaster recovery is in place.

## Definition of done per feature
- Documented role matrix and data-access rules.
- API tests for normal, invalid and cross-band requests.
- Database migration/rollback plan if schema changes.
- Accessibility and mobile workflow check.
- No credentials or production data in commits.
- Staging verification before any production deployment.
