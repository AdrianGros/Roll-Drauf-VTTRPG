# Robot testing research — strict browser journeys for Roll Drauf VTT

> **Einordnung:** Dieses Dokument ist der Tiefen-Annex für Robot R1 (Journey-Robot). Der Dachplan der gesamten Flotte inkl. Regelwerk und Klick-Verträgen ist [ROBOT_FLEET_AND_RULEBOOK_2026-08-24.md](ROBOT_FLEET_AND_RULEBOOK_2026-08-24.md).

**Date:** 2026-08-24
**Scope:** research and design guidance only; no application or robot code was changed for this note.
**Question:** why can the current browser run report zero findings while the login-to-dashboard journey visibly contains several design defects, and what must a stricter robot test?

## Executive summary

The current green result is valid only as a narrow disposable-stack smoke result. It is not evidence that the live login-to-dashboard experience is visually correct.

The main causes are:

1. The runner boots a throwaway local Flask/PostgreSQL stack, while the supplied evidence is from `https://vtt.roll-drauf.de/dashboard`. The two environments are not the same test target ([`stack.py`](../tools/robots/stack.py#L90-L160)).
2. The `views` suite visits routes independently. It does not perform the complete logged-out login → redirect → settled dashboard journey. Registration also logs the robot in directly, so the normal login form is not exercised in that suite ([`views.py`](../tools/robots/views.py#L64-L115), [`session.py`](../tools/robots/session.py#L52-L114)).
3. A view pin checks that selectors exist in the DOM, not that they are visible, correctly positioned, readable, reachable, non-overlapping, or part of the intended active scene ([`views.py`](../tools/robots/views.py#L30-L41), [`views.py`](../tools/robots/views.py#L105-L115)). A hidden or stale legacy node can therefore satisfy the robot while the user sees a broken composition.
4. The harness has no dashboard visual baseline/diff, no general geometry invariant, no accessibility scan, no keyboard-focus journey, no performance budget, and no durable trace/evidence contract. It records console errors and only HTTP responses at `>=500` ([`session.py`](../tools/robots/session.py#L46-L50), [`session.py`](../tools/robots/session.py#L130-L162)).
5. Reports count string findings but do not identify severity, checkpoint, viewport, browser, expected versus actual geometry, or mandatory evidence. A zero count is therefore easy to misread as “zero design defects” ([`report.py`](../tools/robots/report.py#L30-L80)).

The stricter design should be a layered journey robot:

```text
real target + real role
        ↓
checkpointed user journey
        ↓
functional + visual geometry + accessibility + runtime + performance gates
        ↓
baseline/diff + trace + DOM/ARIA/metrics evidence
        ↓
severity-aware report: passed / failed / blocked / inconclusive
```

The user-provided screenshot is exactly the class of failure that DOM-presence pins cannot catch: a page can contain the expected dashboard nodes while an overlay, clipping boundary, fixed layer, or incorrect page composition makes the visible journey wrong.

## Source-backed principles

### 1. Test user-observable states, not DOM existence

Playwright recommends locators that reflect how a user perceives the page, especially role and label locators, and its Locator API is strict and retryable ([Playwright locators](https://playwright.dev/docs/locators)). Playwright’s web-first assertions retry until the expected state is true, including visibility, viewport intersection, text, CSS, and URL assertions ([Playwright assertions](https://playwright.dev/docs/test-assertions); [actionability and assertions](https://playwright.dev/docs/actionability)).

The implication for Roll Drauf is that every journey checkpoint needs assertions such as:

- the expected route and active scene are reached;
- the primary landmark, heading, form, navigation, and CTA are visible;
- the CTA is enabled, receives events, and is inside the intended viewport or scroll container;
- the visible page contains the intended content, not merely a hidden duplicate node.

The current Python suite uses Playwright’s library API rather than the Playwright Test runner. The library has no built-in web-first assertions, reporting, retries, or test-runner trace policy; those responsibilities are currently custom ([Playwright Library vs Test runner](https://playwright.dev/docs/library)). This is not automatically wrong, but it explains why the current harness must explicitly build the missing contracts.

### 2. Replace arbitrary sleeps with readiness assertions

Playwright marks `waitForTimeout`, `waitForSelector`, and `networkidle` as discouraged for test readiness. The documented alternative is to assert the web state that means “ready” ([Playwright Page API](https://playwright.dev/docs/api/class-page)).

The current suite uses fixed delays after navigation and mobile rendering, including 300 ms, 500 ms, 1.2 s, 1.5 s, and 2.5 s ([`session.py`](../tools/robots/session.py#L116-L128), [`views.py`](../tools/robots/views.py#L93-L99), [`mobile.py`](../tools/robots/mobile.py#L197-L220)). The future journey should define named readiness conditions—for example `dashboard-route-active`, `dashboard-scene-visible`, `dashboard-data-settled`, and `primary-actions-ready`—and fail if a condition is never reached.

### 3. Visual correctness needs both invariants and reviewed screenshots

Playwright supports screenshot assertions through `toHaveScreenshot()`, with reference images, configurable pixel-difference thresholds, and masking/style controls for dynamic content ([Playwright visual comparisons](https://playwright.dev/docs/test-snapshots)). It also warns that rendering varies with browser, OS, browser version, hardware, power mode, and headless mode; baselines must therefore be generated and compared in a controlled environment.

Screenshots alone are insufficient: a bad baseline can bless a bad design. Use two layers:

- deterministic geometry and visibility invariants for defects such as clipping, overlap, off-screen controls, and horizontal overflow;
- reviewed screenshot baselines for composition, spacing, unwanted slabs, incorrect layering, typography, and visual hierarchy.

The screenshot evidence must be taken at named journey checkpoints, especially login initial, login submitting/loading, dashboard immediately after redirect, dashboard after data settles, and the first navigation action.

### 4. A failure must be diagnosable, not just counted

Playwright’s Trace Viewer records action timelines, DOM snapshots, source, console output, and network information. Its documented CI recommendation is to retain traces on failure or on the first retry; screenshots and video are not substitutes for the full trace ([Trace Viewer](https://playwright.dev/docs/trace-viewer); [trace test option](https://playwright.dev/docs/api/class-testoptions); [Playwright best practices](https://playwright.dev/docs/best-practices)).

The minimum failure bundle should include the actual screenshot, expected/baseline screenshot where applicable, diff image, trace archive, URL/role/viewport/browser metadata, DOM or ARIA snapshot, layout measurements, console records, failed/unexpected network records, and the exact checkpoint.

### 5. Runtime monitoring must distinguish HTTP errors from transport failures

Playwright documents separate `response` and `requestfailed` events. A 404 or 503 is still an HTTP response and will not appear as `requestfailed`; network failures can occur without a response ([Playwright Request API](https://playwright.dev/docs/api/class-request); [Playwright Network guide](https://playwright.dev/docs/network)).

Therefore the nominal login-to-dashboard journey should fail on unexpected 4xx/5xx responses, failed CSS/JS/font/image requests, request failures, uncaught page errors, and console errors. Expected negative-test responses must be explicitly allowlisted by checkpoint so the allowlist cannot hide a real failure.

### 6. Accessibility automation is a required layer, not a complete audit

Playwright’s official accessibility guidance demonstrates integrating `@axe-core/playwright`, scanning the page or a revealed state, and asserting no violations. It explicitly warns that automated checks find only common issues and must be combined with manual assessment and inclusive user testing ([Playwright accessibility testing](https://playwright.dev/docs/accessibility-testing)).

The robot should scan the settled login and dashboard states, and again after opening menus or sheets. It should also execute a keyboard path: tab through the primary controls, activate the login action, verify focus is visible and not fully obscured, and close persistent overlays with Escape where applicable.

WCAG 2.2 gives concrete acceptance anchors:

- non-exempt content must reflow without loss of information or two-dimensional scrolling at a 320 CSS-pixel equivalent width ([W3C SC 1.4.10 Reflow](https://www.w3.org/WAI/WCAG22/Understanding/reflow.html)); maps and other genuinely two-dimensional workspaces may be exceptions, but surrounding headings, controls, and chrome are not automatically exempt;
- normal text needs at least 4.5:1 contrast and large text at least 3:1 ([W3C SC 1.4.3 Contrast](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html));
- focused components must not be entirely hidden by author-created content ([W3C SC 2.4.11 Focus Not Obscured](https://www.w3.org/WAI/WCAG22/Understanding/focus-not-obscured-minimum.html));
- text must remain usable when resized to 200% ([W3C SC 1.4.4 Resize Text](https://www.w3.org/WAI/WCAG22/Understanding/resize-text.html));
- WCAG 2.2’s minimum pointer target is 24 × 24 CSS pixels with spacing/equivalent-control exceptions ([W3C SC 2.5.8 Target Size](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html)). The repository’s 44 px touch-target rule is a stronger product choice, not the WCAG minimum.

### 7. Responsive coverage must vary device profile, engine, viewport, and input model

Playwright’s emulation API can apply a device profile including user agent, screen size, viewport, touch, locale, and related settings; it provides named device descriptors such as iPhone profiles ([Playwright emulation](https://playwright.dev/docs/emulation)).

The current mobile helper only sets viewport, DPR, `is_mobile`, and touch ([`mobile.py`](../tools/robots/mobile.py#L48-L53)). It does not run a named device descriptor or user-agent/browser-engine matrix. It also checks the play table much more deeply than the login/dashboard book journey. Phone coverage must include the same login-to-dashboard journey, not only a separately prepared play surface.

### 8. Performance needs standardized measurements before hard budgets

The W3C Navigation Timing specification defines `PerformanceNavigationTiming` values such as `domContentLoadedEventEnd`, `loadEventEnd`, `responseEnd`, and `domInteractive` ([Navigation Timing Level 2](https://www.w3.org/TR/navigation-timing-2/)). These should be captured per checkpoint rather than treating an arbitrary sleep as proof of readiness.

Largest Contentful Paint and Long Tasks are useful instrumentation for visual readiness and main-thread blocking. Their current W3C documents are working drafts, so they should initially be reported and trended, then promoted to hard product budgets after a controlled baseline is established ([W3C Largest Contentful Paint](https://www.w3.org/TR/largest-contentful-paint/); [W3C Long Tasks API](https://www.w3.org/TR/longtasks-1/)).

### 9. Reports need explicit status, severity, and evidence

Playwright supports JSON, HTML, JUnit, tags, and annotations, allowing results to be filtered and enriched with categories or issue information ([Playwright reporters](https://playwright.dev/docs/test-reporters); [annotations and tags](https://playwright.dev/docs/test-annotations)). The Roll Drauf report should adopt the same concepts even if the repository remains on the Python library API.

“Zero findings” is acceptable only when every required gate ran and produced evidence. A run with skipped visual checks, missing screenshots, an untested role, or an unavailable target must be `inconclusive` or `blocked`, not green.

## Current-harness gap analysis

| Area | What exists now | Specific gap and consequence |
|---|---|---|
| Target environment | `disposable_stack()` creates a fresh local app and database; the live-database guard intentionally prevents accidental live writes ([`stack.py`](../tools/robots/stack.py#L90-L160)). | The supplied screenshot is from the live hostname, but the green run is local. Production-only CSS, asset, deployment, cache, font, or configuration defects cannot be found. Add a read-only staging/live visual mode with explicit environment metadata and no mutating setup. |
| Login journey | `RobotSession.login()` exists, but `views.py` registers the account and receives the authenticated redirect; it then clears/restores cookies to pin routes independently ([`views.py`](../tools/robots/views.py#L64-L115), [`session.py`](../tools/robots/session.py#L52-L114)). | The key journey—logged out login form → submit → dashboard redirect → settled dashboard—is not an acceptance test. A login form can be broken while route pins remain green. |
| Checkpoint model | Suites have phase functions in flows/fullsession, but the report stores a flat list of strings ([`fullsession.py`](../tools/robots/fullsession.py#L543-L564), [`report.py`](../tools/robots/report.py#L30-L80)). | No mandatory ordered checkpoint manifest; no proof that every journey stage ran; early return can look like a clean result if setup is not classified separately. |
| DOM/visibility | `VIEW_PINS` requires a few selectors and checks visible text for debris ([`views.py`](../tools/robots/views.py#L27-L41), [`views.py`](../tools/robots/views.py#L105-L115)). | `count() > 0` does not assert visibility, active scene, viewport position, enabled state, accessible name, or layout. Hidden/stale nodes can satisfy the check. |
| Geometry/layout | Mobile has a few measured play-table rules: map share, overlap, target height, thumb zone, input size, and dice viewport fit ([`mobile.py`](../tools/robots/mobile.py#L56-L131)). | There is no equivalent desktop or book-page geometry contract: no body overflow rule, no critical-region bounds, no clipping detection, no overlap checks for dashboard layers/cards/nav, no focus-obscuration check, and no assertion that the visible screenshot is the intended composition. |
| Visual evidence | Some flow scripts take screenshots on selected states; `views.py` takes none. `flows.py` deletes its temporary workdir after writing JSON ([`views.py`](../tools/robots/views.py#L121-L130), [`flows.py`](../tools/robots/flows.py#L591-L599)). | Passing login/dashboard states have no screenshot evidence. Failure screenshots can be deleted with their temp workdir, leaving only a filename or string in JSON. There is no baseline, diff, or trace. |
| Runtime/network | `RobotSession` records page errors, console errors, and response statuses only at `>=500` ([`session.py`](../tools/robots/session.py#L130-L162)). | Unexpected 4xx, failed requests, broken fonts/images/stylesheets, and WebSocket transport failures may pass. Console warnings and allowlist provenance are not reported. |
| Waiting | Multiple suites use fixed `wait_for_timeout` delays ([`views.py`](../tools/robots/views.py#L93-L99), [`mobile.py`](../tools/robots/mobile.py#L197-L220)). | Timing can hide a race or let a partially rendered page be judged. Readiness must be a named, asserted state. |
| Accessibility | No axe scan, ARIA snapshot, contrast assertion, keyboard journey, or focus-obscuration assertion exists. | A visually plausible but inaccessible login/dashboard can pass. Automated accessibility must be added at settled and revealed states, with manual-audit residuals recorded. |
| Responsive matrix | Mobile uses one Chromium context with hand-set phone-like properties; the role-aware phone flow uses the same pattern ([`mobile.py`](../tools/robots/mobile.py#L48-L53), [`mobile_session.py`](../tools/robots/mobile_session.py#L27-L36)). | No named device descriptors, WebKit/Safari engine, Firefox, desktop narrow widths, 320 CSS-pixel reflow, 200% text resize, or phone login/dashboard journey. |
| Roles | `fullsession` and `mobile_session` cover DM/player table behavior, including player visibility of DM-only tokens ([`fullsession.py`](../tools/robots/fullsession.py#L367-L405), [`mobile_session.py`](../tools/robots/mobile_session.py#L247-L291)). | Role coverage begins after API-created campaign/session setup and focuses on Play. It does not run the book login/dashboard journey separately as DM and player, nor assert role-specific dashboard chrome and next actions. |
| Reporting | `run_all.py` maps exit codes and counts findings; `report.py` emits a small Markdown table ([`run_all.py`](../tools/robots/run_all.py#L27-L54), [`report.py`](../tools/robots/report.py#L53-L80)). | No severity, checkpoint, browser, viewport, role, expected/actual, evidence links, baseline hash, test version, skipped/inconclusive state, or defect taxonomy. A green zero is too lossy to support design review. |

## Recommended acceptance gates

These are proposed contracts, not implemented changes.

### Gate A — harness integrity and target identity

- Record run ID, commit SHA, target URL/environment, browser engine/version, viewport, device profile, DPR, locale, color scheme, reduced-motion setting, and role.
- Fail or mark `blocked` if the declared target cannot be reached, the browser/device profile is unavailable, or the disposable/live safety boundary is not proven.
- Every journey declares an ordered checkpoint list. Missing or skipped checkpoints are not a pass.
- Keep disposable-stack functional tests and read-only staging/live visual tests as different modes with different permissions and reports.

### Gate B — real login → dashboard journey

For each required role, start logged out and execute the real user path:

1. Open the login page and assert route, document language, page title, primary heading, form visibility, labels/names, primary button visibility/enabled state, and initial screenshot.
2. Fill the real form and click the real submit control. Do not use API login for this checkpoint.
3. Assert the expected redirect URL and authenticated dashboard state using web-first readiness assertions.
4. Assert the settled dashboard: one visible main surface, one intended primary navigation, visible current-page indicator, visible user identity, visible next action, no loading/transition overlay, and expected dynamic data state.
5. Capture dashboard screenshot and layout metrics at the redirect and settled checkpoints. Then keyboard-tab through the primary navigation and perform logout/re-login as a second auth seam.

The dashboard contract should include explicit selectors or test IDs for the intended active surface, not just legacy nodes such as `#campaignsGrid`, `#stats`, and `#username`.

### Gate C — visual and geometry invariants

At every book-page checkpoint, measure and report:

- non-exempt document horizontal overflow (`scrollWidth` versus `clientWidth`);
- critical landmark and CTA rectangles against the viewport and their intended scroll container;
- visible critical controls not clipped by an ancestor, fixed layer, or viewport edge;
- no overlap among critical navigation, headings, cards, buttons, form fields, and overlays, except explicitly documented intentional containment;
- no duplicate visible active navigation or scene layers;
- focused control remains visible and not entirely obscured;
- text containers do not collide or truncate at the tested size and at 200% text scaling.

The map/table may be a documented two-dimensional exception under WCAG Reflow, but its surrounding navigation, controls, headings, and status surfaces remain subject to one-direction reflow and visibility checks.

### Gate D — reviewed screenshot comparisons

- Maintain versioned baselines for login initial, login validation/loading, dashboard post-redirect, dashboard settled, dashboard narrow desktop, dashboard phone portrait, and dashboard phone landscape.
- Use a fixed browser/OS/container for baseline generation; do not auto-update snapshots in CI.
- Mask only intentionally volatile data such as timestamps or random IDs, never layout regions or controls.
- On visual failure, retain baseline, actual, diff, checkpoint metadata, and trace. On a passing run, retain at least the comparison result, baseline identity, and screenshot hash.
- Require a human review for baseline updates and record why the design change is intended.

### Gate E — runtime and network health

Nominal journey rules:

- no uncaught page errors;
- no `console.error` and no unclassified console warnings;
- no `requestfailed` events;
- no unexpected 4xx/5xx response, especially for CSS, JS, font, image, API, and Socket.IO resources;
- all critical fonts, stylesheets, images, and primary API responses load successfully;
- WebSocket/Socket.IO connection reaches the expected state for pages that require realtime behavior.

Negative tests may expect a 4xx, but the expected response must be scoped to that named negative checkpoint and shown in the report.

### Gate F — accessibility and keyboard journey

- Run an automated axe scan against settled login and dashboard states, and after opening every persistent menu/sheet used by the journey; initially use WCAG A/AA tags and record any temporary, reviewed exclusions.
- Use role/label/name-based locators for primary actions where possible.
- Verify `lang="de"`, form labels, landmark structure, heading order, accessible names, unique IDs, and visible focus.
- Tab through the login and dashboard primary paths; activate controls with Enter/Space; close persistent overlays with Escape; assert focus is not entirely hidden.
- Check contrast against WCAG thresholds and keep the stronger 44 px product touch-target rule for primary phone controls.
- Treat automated accessibility as a gate for detectable violations, not as a substitute for manual and assistive-technology assessment.

### Gate G — responsive and browser matrix

At minimum, run the login→dashboard journey at:

- 320 CSS px wide for Reflow-oriented checks;
- 390×844 portrait and 844×390 landscape phone states;
- 768, 1024, and 1280 wide breakpoint probes;
- 1440×900 and 1920×1080 desktop states.

Use named Playwright device descriptors for mobile profiles and run the critical visual journey in Chromium plus WebKit and Firefox where supported. Track physical iOS/Android and real Safari/Chrome as a separate release gate; emulation is not a physical-device proof.

### Gate H — performance and readiness

First collect, without failing release builds, Navigation Timing, an application-defined `dashboard-ready` mark, LCP where supported, resource failures, and long-task counts. After a stable baseline exists, set product-specific p75/p95 budgets for login-to-dashboard readiness and critical asset loading. Keep draft-spec metrics such as LCP and Long Tasks clearly labeled as instrumentation rather than WCAG conformance.

### Gate I — severity and evidence contract

Every finding should contain:

```json
{
  "severity": "blocker|high|medium|low",
  "category": "journey|visual|layout|a11y|runtime|network|performance|responsive",
  "checkpoint": "dashboard-settled",
  "role": "dm",
  "viewport": "1440x900",
  "expected": "primary navigation is visible and non-overlapping",
  "actual": "navigation is clipped by the lower page boundary",
  "evidence": ["actual.png", "diff.png", "trace.zip", "metrics.json"]
}
```

Severity proposal:

- **Blocker:** the target or login journey cannot run, the primary surface is absent, a critical action is unreachable, or evidence is missing for a required gate.
- **High:** visible overlap/clipping, wrong page composition, inaccessible primary auth/navigation action, role leak, failed critical resource, or unexpected server/runtime failure.
- **Medium:** secondary layout defect, contrast or keyboard issue outside the primary path, performance regression beyond the agreed budget, or non-critical console warning.
- **Low:** cosmetic drift or non-blocking polish issue that is still reproducible and evidenced.

The run status must distinguish `passed`, `failed`, `blocked`, and `inconclusive`. `passed` means all mandatory gates ran; zero findings alone is not sufficient.

## Phased implementation plan

### Phase 0 — establish the contract and target split

Inventory the login/dashboard visual states, declare the primary DM/player journeys, identify the exact production/staging target, and define the safety boundary for read-only visual runs. Triage the supplied screenshot into named defects and turn each into a measurable invariant or reviewed visual state. Do not change baselines until the target design is explicitly accepted.

### Phase 1 — build the strict login/dashboard journey

Add one ordered, logged-out journey for desktop and phone. Replace route sweeps as the primary proof. Add readiness checkpoints, visible/accessible assertions, critical geometry metrics, unexpected 4xx/request-failure capture, and a self-test fixture containing deliberately injected defects: hidden primary CTA, off-screen content, overlapping layers, clipped control, and console error. The robot must fail its own canaries.

### Phase 2 — make evidence durable and reviewable

Adopt screenshot baselines for the named checkpoints, a stable artifact directory, diff images, trace-on-failure, DOM/ARIA snapshots, and structured findings. Ensure cleanup never deletes referenced evidence. Expand the run report with role, viewport, browser, checkpoint, severity, expected/actual, and artifact links.

### Phase 3 — add accessibility, responsive, and role depth

Run axe scans and keyboard journeys at settled and revealed states. Add device descriptors and browser-engine projects. Repeat the entire book journey as logged-out, DM, and player; then keep the existing Play table role/session tests as the realtime layer rather than treating them as book-UI coverage.

### Phase 4 — establish performance budgets and deployment confidence

Collect Navigation Timing, application readiness marks, resource timing/failure data, LCP, and long tasks across repeated runs. Convert observed p75/p95 baselines into explicit budgets. Run the visual journey against staging or a production-safe read-only target and include target commit/assets/configuration in the evidence.

### Phase 5 — release-gate operation

Require all mandatory checkpoints and all critical matrix cells to be `passed`; block on missing evidence, unavailable browsers, unreviewed snapshot changes, or unclassified exceptions. Keep a manual visual/accessibility review for design baselines and real-device checks for release claims.

## Research conclusion

The current robot suite is useful for API-backed VTT behavior and selected realtime flows, but it is not yet a strict browser design-jury robot. The immediate missing capability is a target-correct, ordered login-to-dashboard journey with visible geometry assertions and durable visual evidence. Adding more API scenarios without that layer would not address the defect shown in the screenshot.

No application or robot implementation was performed as part of this research note. Secrets, registration keys, cookies, and passwords were intentionally omitted.

## Sources

All external sources used here are primary sources from Playwright or W3C:

- [Playwright locators](https://playwright.dev/docs/locators)
- [Playwright assertions](https://playwright.dev/docs/test-assertions)
- [Playwright actionability](https://playwright.dev/docs/actionability)
- [Playwright Page API](https://playwright.dev/docs/api/class-page)
- [Playwright Library versus Test runner](https://playwright.dev/docs/library)
- [Playwright visual comparisons](https://playwright.dev/docs/test-snapshots)
- [Playwright Trace Viewer](https://playwright.dev/docs/trace-viewer)
- [Playwright test trace option](https://playwright.dev/docs/api/class-testoptions)
- [Playwright best practices](https://playwright.dev/docs/best-practices)
- [Playwright Request API](https://playwright.dev/docs/api/class-request)
- [Playwright Network guide](https://playwright.dev/docs/network)
- [Playwright accessibility testing](https://playwright.dev/docs/accessibility-testing)
- [Playwright emulation](https://playwright.dev/docs/emulation)
- [Playwright reporters](https://playwright.dev/docs/test-reporters)
- [Playwright annotations and tags](https://playwright.dev/docs/test-annotations)
- [W3C WCAG 2.2 Reflow](https://www.w3.org/WAI/WCAG22/Understanding/reflow.html)
- [W3C WCAG 2.2 Contrast](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html)
- [W3C WCAG 2.2 Focus Not Obscured](https://www.w3.org/WAI/WCAG22/Understanding/focus-not-obscured-minimum.html)
- [W3C WCAG 2.2 Resize Text](https://www.w3.org/WAI/WCAG22/Understanding/resize-text.html)
- [W3C WCAG 2.2 Target Size](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html)
- [W3C Navigation Timing Level 2](https://www.w3.org/TR/navigation-timing-2/)
- [W3C Largest Contentful Paint](https://www.w3.org/TR/largest-contentful-paint/)
- [W3C Long Tasks API](https://www.w3.org/TR/longtasks-1/)
