"""Per-view pins: every page carries its own executable audit.

Same idea as the Goblin Delve sister suite's views.py -- for every real
page a manifest of elements that MUST exist (the page's skeleton) and of
debris that must NEVER appear in its visible text. A refactor that
hollows out a page now fails a robot run instead of a player.

The real page inventory (confirmed 2026-08-22 by reading
vtt/__init__.py's catch-all route): static HTML files under
vtt/templates/, served by path (extensionless routes like /dashboard
serve dashboard.html). This is NOT server-rendered Jinja beyond that --
each page is a client-side app that calls the JSON API under /api/.

    python -m tools.robots.views
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

from tools.robots.accounts import mint_registration_keys
from tools.robots.stack import disposable_stack

# Text fragments that mean a template hole, on ANY page.
DEBRIS = ("undefined", "[object", "{{", "}}", "NaN", "null,")

# path → (label, [required CSS selectors], needs_auth)
VIEW_PINS: dict[str, tuple[str, list[str], bool]] = {
    "/login.html": ("Login", ["#passwordLoginForm"], False),
    "/register.html": ("Registrierung", ["#registerForm", "#key",
                                         "#username", "#password"], False),
    "/dashboard": ("Dashboard", ["#campaignsGrid", "#stats", "#username"], True),
    "/campaigns": ("Kampagnen", ["#campaignCreateForm",
                                 "#campaignCreateSubmit"], True),
    "/characters": ("Charaktere", ["#backBtn"], True),
    "/play": ("Play", ["#activityLog"], True),
    "/lobby": ("Lobby", ["#campaigns"], True),
}


def main(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(prog="tools.robots.views")
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--canary", action="store_true",
                        help="inject a pin that CANNOT hold, to prove the "
                             "negative path: the run must exit 1 with a "
                             "finding. A green canary is a broken robot.")
    args = parser.parse_args(argv)
    pins = dict(VIEW_PINS)
    if args.canary:
        label, selectors, needs_auth = pins["/dashboard"]
        pins["/dashboard"] = (f"{label} [CANARY]",
                              [*selectors, "#robot-canary-must-not-exist"],
                              needs_auth)

    workdir = Path(tempfile.mkdtemp(prefix="vtt-views-"))
    print(f"View pins: disposable stack in {workdir} …")
    findings: list[str] = []
    checked = 0
    with disposable_stack(workdir) as stack:
        keys = mint_registration_keys(stack.database_url, count=1)

        from playwright.sync_api import sync_playwright
        from tools.robots.session import RobotSession
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            context = browser.new_context(viewport={"width": 1920, "height": 1080})
            session = RobotSession(context, base_url=stack.base_url,
                                   robot_name="pruefer", artifacts_dir=workdir)
            session.open()
            registered = session.register(
                username="pruefer_bot", email="pruefer_bot@robots.roll-drauf.de",
                password="Ro8ot-Test-Passw0rd!", registration_key=keys[0])
            if not registered:
                detail = "; ".join(f.detail for f in session.findings)
                findings.append(f"[setup] could not register the checking robot: {detail}")

            page = session.page
            authenticated_cookies = context.cookies() if registered else []
            for path, (label, selectors, needs_auth) in pins.items():
                if needs_auth and not registered:
                    findings.append(f"[{label}] skipped: no authenticated robot available")
                    continue
                if not needs_auth and registered:
                    # /login.html and /register.html redirect an already-
                    # authenticated session straight to /dashboard -- these
                    # two pins are only meaningful logged OUT.
                    context.clear_cookies()
                try:
                    response = page.goto(f"{stack.base_url}{path}",
                                         wait_until="domcontentloaded",
                                         timeout=30_000)
                    page.wait_for_timeout(500)
                except Exception as error:
                    findings.append(f"[{label}] did not load: {error}")
                    continue
                finally:
                    if not needs_auth and registered:
                        # Restore the session for whatever pin comes next.
                        context.add_cookies(authenticated_cookies)
                checked += 1
                if response is not None and response.status >= 400:
                    findings.append(f"[{label}] HTTP {response.status}")
                    continue
                for selector in selectors:
                    if page.locator(selector).count() == 0:
                        findings.append(f"[{label}] pin missing: {selector}")
                visible = page.evaluate("() => document.body.innerText")
                for debris in DEBRIS:
                    if debris in visible:
                        findings.append(f"[{label}] debris in visible text: {debris!r}")
            browser.close()

    print(f"\n{checked} views · {len(findings)} finding(s)")
    for finding in findings:
        print(f"  - {finding}")
    report = args.out or workdir.parent / "vtt-view-pins.json"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(
        {"status": "failed" if findings else "passed",
         "views_checked": checked, "canary": args.canary,
         "findings": findings}, indent=2), encoding="utf-8")
    print(f"JSON: {report}")
    import shutil
    shutil.rmtree(workdir, ignore_errors=True)
    return 0 if not findings else 1


if __name__ == "__main__":
    sys.exit(main())
