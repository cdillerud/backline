# Approved development scope: private collaboration and explicit public sharing

Prepared for Chad Dillerud, October 26, 2026. Chad approved A, B and C in this
conversation on October 26. Implementation is confined to development and synthetic
testing. Public-page/feed exposure defaults off behind
`BACKLINE_PUBLIC_SHARING_ENABLED`; no live email transport is configured.
Production branch, deployment, database and secrets remain outside authorization.

## A. Authenticated member collaboration

Keep the existing band membership check. Add narrowly enumerated routes so active
members can write only their own RSVP/availability, their own discussion replies,
their own notification preferences/read states and short-lived typing presence.
Owners/managers retain event, venue, task, repertoire and membership administration.
Viewers remain read-only. Treasurers gain no general administration. A member must
not supply another user's identity or modify another person's RSVP, settings or
post. Use the authenticated session user as actor; test direct object-ID attacks.

Link roster identities to accounts only by owner/manager action, with unique
band/account membership validation. Names/instruments/profile photos can then be
consistent in tasks, discussions and attendance. Roster labels never grant roles.
Mentions resolve only active same-band memberships. Generate personal notifications
for task assignments, RSVP requests and mentions; store category preferences
(immediate/daily/none) and use a server-side, idempotent email outbox. Tests use a
fake transport; no live emails or production credentials are used during development.
Email activation/provider configuration remains a separate reviewable step.

## B. Private media and explicit public publishing

Add bounded JPEG/PNG uploads with decoded pixel/byte limits, metadata stripping,
per-band quotas, opaque identifiers and authorization on every private media read.
Add bounded recording uploads separately with safe content types and download
headers. No server-side fetching of arbitrary reference URLs. Serve media so
uploaded content cannot execute as application HTML/scripts. Test malformed files,
oversize payloads, media guessing and cross-band reads.

Build public band-page draft previews first. Only owner/manager publication enables
a read-only, no-login page with an explicit allowlist: approved bio/banner, selected
public photo albums and selected future gig titles/dates/public venue names.
Never serialize private event models. Exclude contacts, load-in/access/curfew notes,
RSVP/availability, discussions, tasks, finances and private galleries. Publishing an
album is explicit; members-only is the default. Provide preview, revoke and audit
history. No deployment or publication of real user content without approval.

## C. Explicit venue sharing and subscription calendars

Keep each band private by default. Reuse a venue across bands only when an
owner/manager who has access to both bands selects source and destination and sees
exactly which contact/notes fields will be copied or shared. Never grant destination
members access to unrelated source-band data. Keep private gig-specific advancement
separate from reusable venue data. Record the action and support revocation of
future shared access.

A calendar subscription is a capability URL and may expose private event details.
Issue random hashed, revocable tokens only for an explicitly selected calendar and
minimized export fields, with a warning about calendar-provider copies. Do not
place account/session bearer tokens in URLs. Downloads remain authenticated until
this design is approved. PWA work will avoid caching private API responses or
media; logout must clear any app-owned private state, and service-worker scope and
updates require regression coverage.

## Authorization record

Approved: implementing and testing A, B and C on `integration/backline-v0-4-rc` and
synthetic local/isolated preview data only. This does not authorize production
merge, production deployment, live email delivery, changing production roles/data,
or publishing real band pages or media. Only the enumerated member self-service writes and explicitly enabled public
capabilities change the existing policy. Production is still excluded.
