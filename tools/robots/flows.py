"""Real scenarios, not just page pins — the human half views.py cannot
see: does the flow actually make sense end to end.

First flow: the real-time layer itself. A DM creates a campaign and a
session through the real API (page.request, so the browser's own auth
cookies are used — same effect as filling forms, less brittle for
multi-step JSON flows), opens /play for that session, and rolls dice
through the actual dice-roller UI. The interesting part is not the
roll -- it is that the result has to travel client -> Socket.IO ->
server -> broadcast -> back to the SAME client's own socket and land in
the DOM (#diceLog, #activityLog), proving the whole real-time round
trip most VTT features (map/token sync, session snapshots, initiative)
build on top of.

    python -m tools.robots.flows
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

from tools.robots.accounts import mint_registration_keys
from tools.robots.stack import disposable_stack


def _dice_roll_flow(stack, workdir: Path) -> list[str]:
    from playwright.sync_api import sync_playwright
    from tools.robots.session import RobotSession

    findings: list[str] = []
    keys = mint_registration_keys(stack.database_url, count=1)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = browser.new_context(viewport={"width": 1280, "height": 900})
        session = RobotSession(context, base_url=stack.base_url,
                               robot_name="spielleitung",
                               artifacts_dir=workdir)
        session.open()
        registered = session.register(
            username="spielleitung_bot",
            email="spielleitung_bot@robots.roll-drauf.de",
            password="Ro8ot-Test-Passw0rd!", registration_key=keys[0])
        if not registered:
            findings.extend(f"[setup] {f.detail}" for f in session.findings)
            browser.close()
            return findings

        page = session.page
        api = context.request
        # JWT_COOKIE_CSRF_PROTECT is on (vtt/config.py) -- Flask-JWT-Extended's
        # double-submit pattern needs the csrf_access_token cookie echoed
        # back as a header on every mutating request. page.request shares
        # the browser context's cookies automatically but does NOT read
        # them into headers for you (that is normally the frontend JS's
        # job, e.g. auth.js) -- do it explicitly for the same effect.
        csrf_token = next((c["value"] for c in context.cookies()
                           if c["name"] == "csrf_access_token"), None)
        if not csrf_token:
            findings.append("[setup] no csrf_access_token cookie after "
                            "registration — cannot make authenticated API calls")
            browser.close()
            return findings
        json_headers = {"Content-Type": "application/json",
                        "X-CSRF-TOKEN": csrf_token}

        campaign_response = api.post(
            f"{stack.base_url}/api/campaigns",
            data=json.dumps({"name": "Robotertestkampagne", "max_players": 6}),
            headers=json_headers)
        if campaign_response.status != 201:
            findings.append(
                f"[campaign] POST /api/campaigns returned "
                f"HTTP {campaign_response.status}: {campaign_response.text()[:300]}")
            browser.close()
            return findings
        campaign_id = campaign_response.json()["campaign"]["id"] \
            if "campaign" in campaign_response.json() \
            else campaign_response.json()["id"]

        session_response = api.post(
            f"{stack.base_url}/api/campaigns/{campaign_id}/sessions",
            data=json.dumps({"name": "Robotertestsitzung"}),
            headers=json_headers)
        if session_response.status != 201:
            findings.append(
                f"[session] POST /api/campaigns/{campaign_id}/sessions "
                f"returned HTTP {session_response.status}: "
                f"{session_response.text()[:300]}")
            browser.close()
            return findings
        body = session_response.json()
        session_id = body["session"]["id"] if "session" in body else body["id"]

        if not session.goto(f"/play?campaign_id={campaign_id}&session_id={session_id}"):
            findings.extend(f"[play] {f.detail}" for f in session.findings)
            browser.close()
            return findings

        try:
            page.wait_for_selector("#diceInput", state="visible", timeout=15_000)
            # The socket join (session:join, emitted automatically on
            # connect by play-socket.js) is itself a round trip -- give it
            # a moment to land before rolling, rather than racing it.
            page.wait_for_timeout(1_500)
            page.fill("#diceInput", "1d20+5")
            page.click("#btnRoll")
            # The roll has to complete a full client -> server -> broadcast
            # -> client round trip before #diceLog shows a line -- this is
            # the actual thing under test, not just a UI click.
            page.wait_for_selector("#diceLog div", state="attached", timeout=10_000)
        except Exception as error:
            findings.append(
                f"[dice] roll never produced a #diceLog entry within "
                f"10s (real-time round trip failed or was too slow): {error}")
            findings.extend(f"[{f.kind}] {f.detail}" for f in session.findings)
            try:
                shot = workdir / "dice-roll-timeout.png"
                page.screenshot(path=str(shot))
                findings.append(f"[dice] screenshot: {shot.name}")
            except Exception:
                pass
            browser.close()
            return findings

        log_text = page.locator("#diceLog").inner_text()
        if "gewuerfelt" not in log_text:
            findings.append(f"[dice] #diceLog updated but text looks wrong: {log_text[:200]!r}")

        activity_text = page.locator("#activityLog").inner_text() \
            if page.locator("#activityLog").count() else ""
        if "gewuerfelt" not in activity_text:
            findings.append(
                f"[dice] #diceLog updated but #activityLog was not "
                f"(only one of the two broadcast handlers fired): {activity_text[:200]!r}")

        findings.extend(f"[{f.kind}] {f.detail}" for f in session.findings)
        browser.close()
    return findings


FLOWS = {
    "dice_roll_realtime": _dice_roll_flow,
}


def main(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(prog="tools.robots.flows")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)

    workdir = Path(tempfile.mkdtemp(prefix="vtt-flows-"))
    print(f"Flows: disposable stack in {workdir} …")
    all_findings: dict[str, list[str]] = {}
    with disposable_stack(workdir) as stack:
        for name, runner in FLOWS.items():
            print(f"  running {name} …")
            all_findings[name] = runner(stack, workdir)

    total = sum(len(v) for v in all_findings.values())
    print(f"\n{len(FLOWS)} flow(s) · {total} finding(s)")
    for name, findings in all_findings.items():
        for finding in findings:
            print(f"  - [{name}] {finding}")

    report = args.out or workdir.parent / "vtt-flows.json"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(
        {"status": "failed" if total else "passed", "flows": all_findings},
        indent=2), encoding="utf-8")
    print(f"JSON: {report}")
    import shutil
    shutil.rmtree(workdir, ignore_errors=True)
    return 0 if not total else 1


if __name__ == "__main__":
    sys.exit(main())
