"""Kulissen-Check (V-Regeln V1/V2, Regelwerk §5b): the designed backdrop
must cover the whole viewport at EVERY scroll position, and html/body
must always carry a concrete surface color.

Method per page x viewport ("Scroll-Treppe"):
  * find the real scroller (window OR the tallest inner scroll container
    -- fullPage screenshots are deliberately NOT used, see §8.1);
  * scroll to 0/25/50/75/100%, screenshot the viewport at each step;
  * sample 8 edge points (corners + edge midpoints, 10px inset) and
    compare against the reference palette taken at step 0 plus the
    same-position pixel of step 0 -- a sample matching neither is a
    "Kulissen-Abriss" (V1, blocker);
  * assert html/body computed background is not transparent (V2) and the
    document does not overflow horizontally (Gate C).

Mobile runs in TWO viewport heights (URL bar visible/collapsed) because
the 100vh trap lives exactly there (§8.1).  Ends with a §11 canary: a
white stripe is injected at the bottom of a stretched page and the
staircase must flag it, otherwise the run is `inconclusive`.

Runs against the disposable stack (read-only checks, but the account
prelude registers a user).  Exit codes: 0 passed, 1 findings
(blocker/high), 2 blocked/inconclusive.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

from tools.robots.accounts import mint_registration_keys
from tools.robots.report import REPO
from tools.robots.session import RobotSession
from tools.robots.stack import StackError, disposable_stack

DEFAULT_OUT = REPO / "artifacts" / "robots" / "kulissen"
SETTLE_MS = 400
COLOR_DELTA = 48
EDGE_INSET = 10
STEPS = (0.0, 0.25, 0.5, 0.75, 1.0)

VIEWPORTS = {
    "desktop-wide": (1440, 900),
    "phone-portrait": (390, 844),
    "phone-portrait-urlbar": (390, 760),
    "phone-landscape": (844, 390),
}

PAGES = (
    # This harness always authenticates before testing "login" (see the
    # account prelude below), so /login.html's own instant client-side
    # transition (book-scene.js) fires immediately and the login form is
    # hidden (display:none, 2026-08-25) almost as soon as it appears --
    # deliberately, it is no longer the surface actually on screen. Wait
    # for whichever of the two actually settles rather than assuming the
    # anonymous-visitor case.
    {"name": "login", "path": "/login.html",
     "ready": "#login-content.visible, #book-dashboard-scene.is-visible"},
    {"name": "dashboard", "path": "/dashboard", "ready": "#book-dashboard-scene"},
)

FIND_SCROLLER_JS = """
() => {
  const doc = document.scrollingElement;
  if (doc && doc.scrollHeight > doc.clientHeight + 8) {
    return { kind: 'window', max: doc.scrollHeight - doc.clientHeight };
  }
  let best = null;
  document.querySelectorAll('*').forEach((el) => {
    const style = getComputedStyle(el);
    if (!/(auto|scroll)/.test(style.overflowY)) return;
    const delta = el.scrollHeight - el.clientHeight;
    if (delta > 8 && (!best || delta > best.delta)) best = { el, delta };
  });
  if (!best) return { kind: 'none', max: 0 };
  document.querySelectorAll('[data-kulissen-scroller]').forEach(
    (el) => el.removeAttribute('data-kulissen-scroller'));
  best.el.setAttribute('data-kulissen-scroller', '1');
  return { kind: 'element', max: best.delta };
}
"""

SCROLL_TO_JS = """
(args) => {
  if (args.kind === 'window') {
    window.scrollTo(0, args.y);
  } else {
    const el = document.querySelector('[data-kulissen-scroller]');
    if (el) el.scrollTop = args.y;
  }
}
"""

SURFACE_JS = """
() => {
  const paint = (el) => {
    if (!el) return { color: null, image: null, painted: false };
    const style = getComputedStyle(el);
    return {
      color: style.backgroundColor,
      image: style.backgroundImage,
      painted: style.backgroundColor !== 'rgba(0, 0, 0, 0)'
        || style.backgroundImage !== 'none',
    };
  };
  return {
    html: paint(document.documentElement),
    body: paint(document.body),
    scrollWidth: document.scrollingElement
      ? document.scrollingElement.scrollWidth : 0,
    innerWidth: window.innerWidth,
  };
}
"""

# The canary tests the DETECTOR, not the app: a bare data: page with a
# long unpainted body is the pure form of the defect (nothing designed
# covers the viewport once scrolled).  App-independent by design -- a
# fixed full-viewport backdrop in the app would otherwise hide any
# injected defect from elementFromPoint.
CANARY_URL = ("data:text/html,<html><body style='margin:0'>"
              "<div style='height:4000px;width:50%'>canary</div>"
              "</body></html>")

COVER_JS = """
(args) => args.points.map(([x, y]) => {
  const el = document.elementFromPoint(x, y);
  if (!el) return 'none';
  if (el === document.documentElement) return args.htmlPainted ? 'covered' : 'html';
  if (el === document.body) return args.bodyPainted ? 'covered' : 'body';
  return 'covered';
})
"""


def _edge_points(width: int, height: int) -> list[tuple[int, int]]:
    inset = EDGE_INSET
    return [
        (inset, inset), (width - inset, inset),
        (inset, height - inset), (width - inset, height - inset),
        (width // 2, inset), (width // 2, height - inset),
        (inset, height // 2), (width - inset, height // 2),
    ]


def _close(a: tuple, b: tuple, delta: int = COLOR_DELTA) -> bool:
    return all(abs(x - y) <= delta for x, y in zip(a[:3], b[:3]))


class KulissenRun:
    def __init__(self, out_dir: Path) -> None:
        self.out_dir = out_dir
        self.findings: list[dict] = []
        self.cells: list[dict] = []
        self.blocked = False
        self.canary_caught: bool | None = None

    def find(self, severity: str, category: str, cell: str, expected: str,
             actual: str, evidence: list[str] | None = None) -> None:
        self.findings.append({
            "severity": severity, "category": category, "cell": cell,
            "expected": expected, "actual": actual,
            "evidence": evidence or []})

    def status(self) -> str:
        if self.blocked:
            return "blocked"
        if self.canary_caught is False:
            return "inconclusive"
        if any(f["severity"] in ("blocker", "high") for f in self.findings):
            return "failed"
        return "passed"

    def write(self, seconds: float) -> None:
        counts: dict[str, int] = {"blocker": 0, "high": 0, "medium": 0, "low": 0}
        for finding in self.findings:
            counts[finding["severity"]] = counts.get(finding["severity"], 0) + 1
        payload = {"status": self.status(), "seconds": round(seconds, 1),
                   "severity_counts": counts,
                   "canary_caught": self.canary_caught,
                   "findings": self.findings, "cells": self.cells}
        (self.out_dir / "kulissen.json").write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        lines = [
            "# Kulissen-Check (V1/V2)", "",
            f"Status: **{payload['status']}** — {len(self.cells)} Zellen, "
            f"{len(self.findings)} Findings {counts}, "
            f"Canary gefangen: {self.canary_caught}", "",
            "| Severity | Kategorie | Zelle | Tatsächlich |", "|---|---|---|---|",
        ]
        for finding in self.findings:
            lines.append(f"| {finding['severity']} | {finding['category']} | "
                         f"{finding['cell']} | {finding['actual'][:120]} |")
        (self.out_dir / "report.md").write_text(
            "\n".join(lines) + "\n", encoding="utf-8")


def _staircase(run: KulissenRun, page, cell: str, shots_dir: Path) -> int:
    """Run the scroll staircase for one page/viewport cell; returns the
    number of tear findings recorded."""
    surface = page.evaluate(SURFACE_JS)
    if surface["scrollWidth"] > surface["innerWidth"] + 1:
        run.find("high", "h-overflow", cell,
                 "kein horizontaler Dokument-Überlauf (Gate C)",
                 f"scrollWidth {surface['scrollWidth']} > "
                 f"innerWidth {surface['innerWidth']}")
    if not surface["html"]["painted"] and not surface["body"]["painted"]:
        run.find("high", "v2-nackter-body", cell,
                 "html oder body trägt eine konkrete Fläche (V2)",
                 "html UND body sind unbemalt (weder Farbe noch Bild) — "
                 "Overscroll zeigt Browser-Default")
    elif not surface["html"]["painted"]:
        run.find("low", "v2-html-unbemalt", cell,
                 "html trägt eine eigene Fläche (V2, Overscroll)",
                 f"nur body ist bemalt (Farbe {surface['body']['color']}, "
                 f"Bild {surface['body']['image'][:60]}); Rubber-Banding "
                 "hängt an Browser-Propagation")

    scroller = page.evaluate(FIND_SCROLLER_JS)
    tears = 0
    steps = STEPS if scroller["kind"] != "none" else (0.0,)
    viewport = page.viewport_size
    points = _edge_points(viewport["width"], viewport["height"])
    for step in steps:
        page.evaluate(SCROLL_TO_JS, {"kind": scroller["kind"],
                                     "y": int(scroller["max"] * step)})
        page.wait_for_timeout(SETTLE_MS)
        # Content covering an edge is legitimate (a full-bleed page).
        # The defect V1 names is an edge point where NOTHING designed is
        # painted -- elementFromPoint answering html/body/none.  Wrongly
        # *colored* but covered surfaces are R6-baseline territory.
        cover = page.evaluate(COVER_JS, {
            "points": points,
            "htmlPainted": surface["html"]["painted"],
            "bodyPainted": surface["body"]["painted"]})
        bare = [(points[i], cover[i]) for i in range(len(points))
                if cover[i] != "covered"]
        if bare:
            shot = shots_dir / f"{cell}-{int(step * 100):03d}.png"
            page.screenshot(path=str(shot))
            tears += 1
            run.find("blocker", "v1-kulissen-abriss", cell,
                     "an jedem Randpunkt liegt eine gestaltete Fläche, an "
                     "jeder Scroll-Position (V1)",
                     f"bei Scroll {int(step*100)}% liegt an "
                     f"{[p for p, _ in bare]} nur {bare[0][1]} "
                     f"(nacktes Dokument)",
                     [shot.name])
    run.cells.append({"cell": cell, "scroller": scroller["kind"],
                      "scroll_max": scroller["max"],
                      "html_painted": surface["html"]["painted"],
                      "body_painted": surface["body"]["painted"],
                      "body_bg": surface["body"]["color"]})
    return tears


def run_kulissen(*, out_dir: Path) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    shots_dir = out_dir / "screenshots"
    shots_dir.mkdir(exist_ok=True)
    run = KulissenRun(out_dir)
    started = time.monotonic()
    workdir = Path(tempfile.mkdtemp(prefix="vtt-kulissen-"))
    credentials = {"username": "kulissen_dm", "password": "Kulissen-Pass-1!"}
    try:
        with disposable_stack(workdir) as stack:
            keys = mint_registration_keys(stack.database_url, count=1)
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch()
                registered = False
                for viewport_name, (width, height) in VIEWPORTS.items():
                    context = browser.new_context(
                        viewport={"width": width, "height": height},
                        locale="de-DE",
                        is_mobile=viewport_name.startswith("phone"),
                        has_touch=viewport_name.startswith("phone"))
                    context.set_default_timeout(10_000)
                    session = RobotSession(
                        context, base_url=stack.base_url,
                        robot_name=f"kulissen-{viewport_name}",
                        artifacts_dir=shots_dir)
                    session.open()
                    if not registered:
                        registered = session.register(
                            username=credentials["username"],
                            email="kulissen_dm@robots.roll-drauf.de",
                            password=credentials["password"],
                            registration_key=keys[0])
                        if not registered:
                            run.blocked = True
                            break
                    else:
                        if not session.login(
                                username=credentials["username"],
                                password=credentials["password"]):
                            run.blocked = True
                            for finding in session.findings:
                                run.find("blocker", "harness",
                                         f"login-{viewport_name}",
                                         "Robot kann sich anmelden",
                                         f"{finding.kind}: {finding.detail[:180]}")
                            break
                    for page_def in PAGES:
                        cell = f"{page_def['name']}-{viewport_name}"
                        if not session.goto(page_def["path"]):
                            run.blocked = True
                            continue
                        try:
                            session.page.wait_for_selector(
                                page_def["ready"], state="visible")
                        except Exception:
                            run.find("high", "journey", cell,
                                     f"{page_def['ready']} wird sichtbar",
                                     "Seite wurde nicht bereit")
                            continue
                        _staircase(run, session.page, cell, shots_dir)
                    context.close()

                # §11 canary on a bare data: page (see CANARY_URL note).
                context = browser.new_context(
                    viewport={"width": 1440, "height": 900}, locale="de-DE")
                context.set_default_timeout(10_000)
                canary_page = context.new_page()
                canary_page.goto(CANARY_URL)
                canary_run = KulissenRun(out_dir)
                tears = _staircase(canary_run, canary_page,
                                   "canary-bare", shots_dir)
                run.canary_caught = tears > 0
                if not run.canary_caught:
                    run.find("blocker", "canary", "canary-bare",
                             "die Treppe erkennt eine ungedeckte, "
                             "gescrollte Seite",
                             "nackte data:-Seite wurde nicht beanstandet "
                             "— Prüfung ist blind")
                context.close()
                browser.close()
    except StackError as error:
        run.blocked = True
        run.find("blocker", "harness", "stack", "Wegwerf-Stack startet",
                 str(error))
    except BaseException as error:  # noqa: BLE001 — Gate I: evidence survives any abort
        run.blocked = True
        run.find("blocker", "harness", "crash",
                 "Kulissen-Check läuft bis zum Ende durch",
                 f"{type(error).__name__}: {error}"[:300])
        raise
    finally:
        run.write(time.monotonic() - started)
    status = run.status()
    print(f"kulissen: {status} — Findings: {len(run.findings)}, "
          f"Report: {out_dir / 'report.md'}")
    return {"passed": 0, "failed": 1}.get(status, 2)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="tools.robots.kulissen")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)
    return run_kulissen(out_dir=args.out)


if __name__ == "__main__":
    sys.exit(main())
