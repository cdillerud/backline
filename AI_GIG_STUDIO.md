# AI Gig Intelligence & Marketing Studio — technical plan

## Scope of this PR
This increment provides durable, band- and gig-scoped **market evidence**, **editable draft storage**, and explicit **human approval** with a review log. No external event provider, AI model or social media account is connected in this release. No autonomous publishing or background scanning is claimed.

## Proposed end-to-end workflow
1. A band manager picks a confirmed gig (venue, city, event date and times).
2. An approved data-provider adapter queries concerts, neighborhood festivals, large sporting events and other public happenings within a configurable radius and time window.
3. Normalize data to title, venue, coordinates, start/end, source URL, provider, retrieval time, availability and certainty. De-duplicate by identifiers, venue, date and similarity.
4. Present findings with clickable evidence and **reported** vs **inferred** explanations. Never claim a particular audience will attend without supporting data.
5. Produce messaging angles using the band's saved voice guide, venue details, genre and **verified** nearby event context. Generated copy must never invent discounts, collaborators, ticket prices, cover charge, accessibility or times.
6. Save drafts as versioned records, require manager review, and separately opt in to any eventual social publishing integration.
7. Capture engagement, ticket clicks (when tracking is available), audience estimates and settlement outcomes; distinguish correlation from causation.

## Provider/AI integration
- A constrained, server-side integration account fetches public event data from licensed sources, with explicit API keys in Fly secrets. **No arbitrary URL fetches.**
- Recommended initial source: Ticketmaster Discovery API (concert listings and dates) plus a second provider for city/civic events. Geographic coverage, venue granularity, quotas, commercial terms and current pricing must be verified before committing.
- Cache provider responses by gig/date/area and record `retrieved_at`; provide refresh controls and per-gig budget ceilings.
- AI model calls remain server-side with structured prompts, source references, token ceilings, quality checks and human review.
- Provider content is untrusted data, never instructions. Strip HTML and do not insert retrieved content into privileged tool prompts as executable directions.
- Daily cost and error metrics. No default paid model calls without an explicit owner-enabled limit.

## Privacy and safety
- **Release blocker:** Current live Backline has only shared preview authentication. Implement individual identities and per-band permission checks before any multi-band marketing launch.
- Do not scrape private social profiles, reuse protected content, or contact audiences without consent.
- No automatic sending/posting until approved content, platform OAuth and revocable permissions exist.
- Don't imply venue approval or affiliation based only on nearby events.
- Off-site SQLite backup and restore tests required before data migrations.
- Source provenance and timestamps must remain visible in the user interface.

## Next development passes
1. UX: show per-gig Market Intelligence tab with source cards, draft editor, variant comparison and approval controls.
2. Event-adapter contract plus mocked integration tests and duplicate detection.
3. First licensed provider and model connector behind disabled-by-default feature flags.
4. Campaign calendar, revision history, tone guide and scheduled review reminders.
5. Read-only social metrics; delayed publishing integrations after auth and permissions are certified.
