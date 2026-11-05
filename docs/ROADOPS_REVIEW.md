# RoadOps review — October 26, 2026

Source: https://www.roadops.app/ (public marketing site; signed-in behavior was not tested).

| RoadOps advertises | Proposed Backline addition |
|---|---|
| Item-level change history | Actor, before/after values and revision history on advances and travel. |
| Last-minute schedule notifications and read tracking | Urgent time-change alerts with acknowledgement. |
| Guest counts, passes, approvals and box-office PDFs | Show guest lists with cutoff, approver and printable export. |
| Multiple lodging arrangements and rooming PDFs | Structured hotels, room assignments, check-in/out and exports. |
| Offline editing with later synchronization | First deliver offline read access; design conflicts before queued edits. |
| Confirmation/itinerary imports | Import to a reviewable draft with source evidence and duplicate detection. |
| Travel-party visibility and connected teams | Explicit per-party audiences and shared show schedules. |

Backline priority recommendation: change history and urgent alerts first; guest lists
and structured lodging second; reviewed imports third. Maps/contact shortcuts and
copying day templates are useful smaller improvements. Keep broad offline editing,
airline integrations and AI-agent access behind later technical review. The original review above was a proposal, not a product-equivalence claim.
BandBrief’s minimum-feature checklist remains the acceptance baseline.

## Implementation follow-up

v0.4.0-rc.3 now implements scoped change history, in-app urgent acknowledgements,
guest requests/approvals and box-office PDFs, structured hotel rooming with private
PDFs, and reviewed CSV itinerary drafts. See `OPERATIONS_RC3.md` for behavior and
limits. Browser push, offline access/editing, travel-party sharing, confirmation
PDF/email/AI extraction and provider integrations remain proposed future work.
