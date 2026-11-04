# Band Home & Gig Day — real browser screenshot acceptance

Date: November 3–4, 2026. Source: authenticated **synthetic** Playwright fixtures (not customer accounts), Backline CI run [#1060](https://github.com/cdillerud/backline/actions/runs/41764316780), screenshot artifact `gigday-responsive-synthetic` (GitHub Actions artifact 13291688917).

## Viewports reviewed
Screenshots were produced at **320, 375, 390, 768 and 1280 pixels** for Home and the focused Gig Day view. The 320/375/390 pixel tests also recorded the mid-page scrolled viewport. These are real Chromium renderings from synthetic data, not illustrative mockups. Assertions check document horizontal overflow, screen content, scrolling, navigation focus and gig switching.

## Observations
- Home is responsive: desktop left rail with overview cards; mobile uses 2-column metrics and stacked panels, with the six-destination bottom workspace navigation.
- Gig Day clearly foregrounds the band, selected gig, five recorded call times, venue/contact information and the musician's assignments. **TBD** remains visible for unrecorded call times and the venue time zone is called out as missing.
- The new mobile sticky horizontal shortcut strip remained in the scroll viewport at narrow widths; horizontal swiping is confined to the strip, not the full document.
- The screenshots exposed a UX regression: redundant secondary `Booking Tracker / Show Packets / Show Operations` pills appeared immediately above the musician-facing Gig Day view. This contradicts our one-screen, band-life-first navigation goal. The dedicated Gig Day route now suppresses that mobile context navigation, while the full features remain accessible within Shows & Tours and from the Gig Day production links. The change must be revalidated in a later CI run.
- The synthetic show has deliberately incomplete venue, setlist and lodging records; the empty states are factual and do not imply that every real show lacks this information.
- Desktop production links remain in the left secondary navigation. They are not repeated as a separate gig-day subnav on mobile.

## Acceptance decisions
- **Passed on run #1060:** five widths, automated desktop/mobile browser assertions, artifact capture. Screen design is usable at phone widths, though subjective musician usability still requires actual device feedback.
- **Remediated, pending newer green CI:** remove redundant Gig Day mobile module pills; ensure no off-screen navigation after show switching; keep sticky shortcut bar within the viewport and preserve keyboard focus.
- **Pending:** inspect updated post-remediation screenshots, complete final-head CI, then perform authenticated preview deployment and human/mobile acceptance. Draft branch remains separate from production. Never equate a green older commit with approval of a later branch head.

## Release criteria
1. CI on the **final integration branch head** is green across authenticated demo, five-width mobile acceptance, complete regression suite, JS syntax, dependency audit and Python compile.
2. Latest artifact shows no duplicate mobile module pills or offscreen/overlapping controls, especially around the sticky action bar and fixed bottom workspace nav.
3. Band owner and normal member behavior verified; only authorized private guest, rooming and task data shown.
4. Explicit preview release approval where required. **Do not merge/deploy production** as part of visual acceptance.

## Post-remediation visual review
The new five-viewport synthetic screenshots from [CI #1066](https://github.com/cdillerud/backline/actions/runs/41764681463), artifact `gigday-responsive-synthetic` (ID 13292066281), were downloaded and visually inspected. At 390px the previous Booking Tracker / Show Packets / Show Operations pill strip is absent; the page proceeds from the workspace header to the show context and sticky Gig Day shortcuts. The 390px full-page image remains within the phone viewport and the call cards, personal-task panel and fixed bottom workspace nav render without apparent horizontal clipping. The scrolled 390px image also shows the shortcut strip remaining onscreen above music/lodging/stage sections.

The screenshot review is **visual evidence, not a real device performance or accessibility certification**. The CI run's five-width acceptance step passed; final comprehensive regression and the latest branch-head checks remain the release gates. The inline alert shortcut is now explicitly labeled `Urgent changes` to distinguish it from the full `All notifications` inbox.

## Additional 320px screenshot remediation (extended sprint)
A subsequent synthetic 320px full-page screenshot (from CI #1128's archived partial artifact) showed correct horizontal fit and successful sticky controls, but too much vertical scrolling when every missing show fact and schedule warning was expanded. The narrower design has now been adjusted to:
- Render five milestone call cards in **two columns at 320px** rather than one.
- Show the first three prioritized factual reminders, with the remainder in an accessible expandable list. Urgent acknowledgements appear before routine information where present; no warning is removed.
- Show the first two timeline warnings with additional recorded warnings behind an explicit disclosure. The full running order remains visible.
- Preserve the top-to-bottom information hierarchy: show identity, shortcuts, call times, venue/personal assignments, checklist, RSVP, changes, timeline, music, lodging and stage reference.
- Offer a cleaner paper call sheet, optional offline warning/freshness timestamp, and a mobile-accessible on-stage view with optional screen wake lock.

A five-viewport test now asserts the 320px two-column call layout, expandable reminders and timeline warnings, no horizontal overflow, on-stage performance accessibility and the print layout. These fixes have **not** been marked visually accepted or production-ready without the latest CI and updated screenshot review.

## Validation notes
- Older green CI #1076 is the certified base for the original mobile redesign.
- New extended-sprint CI runs may be canceled when superseded, as intended. Only the **latest branch-head run** is a candidate for certification.
- A synthetic print-click test intermittently observed duplicate invocations; the print handler now suppresses overlapping actions and the test records call stacks when it fails. Treat an unresolved recurrence as a release blocker.
- No production or preview deployment has occurred.
