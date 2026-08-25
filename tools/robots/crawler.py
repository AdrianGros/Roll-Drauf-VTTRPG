"""Button-Crawler (Robot R2): click every registered control for real and
verify its declared, observable postcondition -- plus flag what the
registry does not know about.

Three passes per contract page (tools/robots/contracts/*.json):

  1. Inventory: enumerate every interactive element in the DOM (visible
     and hidden separately) and write it to inventory.json -- the
     work-list for extending the registry.
  2. Coverage diff: a visible interactive element no contract selector
     matches is an "undocumented-button" finding (medium -- becomes
     blocking once the registry is declared complete, Regelwerk §1).
  3. Contract execution: really click (and, where declared, activate by
     keyboard) each registered element and wait for its postcondition
     with Playwright's retrying waits.  Mouse and keyboard must land in
     the same result (Ein-Engine-Invariante, Regelwerk §3).  A contract
     expecting `effect: "any"` fails as a dead button when neither the
     URL, the DOM signature, nor the network moved.

Field-research hardening baked in (ROBOT_FLEET_AND_RULEBOOK §8.3):
execution order is seeded and the seed is in the report; reset between
clicks is a fresh navigation over the reach-path, never browser-back;
popups are contained and reported, not crashed on; every execution keeps
a before/after screenshot.  The run ends with a §11 canary: a dead
button is injected and the crawler must catch it, otherwise the whole
run is `inconclusive` -- a robot that cannot fail proves nothing.

Runs ONLY against the disposable stack (mutating robot, Regelwerk §12).

Exit codes: 0 = passed (possibly with medium/low findings),
1 = blocker/high findings, 2 = blocked or inconclusive.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
import tempfile
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

from tools.robots.accounts import mint_registration_keys
from tools.robots.report import REPO
from tools.robots.session import RobotSession
from tools.robots.stack import StackError, disposable_stack

CONTRACTS_DIR = Path(__file__).resolve().parent / "contracts"
DEFAULT_OUT = REPO / "artifacts" / "robots" / "crawler"
READY_TIMEOUT_MS = 15_000
POSTCONDITION_TIMEOUT_MS = 10_000
EFFECT_SETTLE_MS = 1_500

# Enumeration mirrors Crawljax's candidate-clickable scan: anything a user
# could plausibly activate, judged from the DOM, visible or not.
ENUMERATE_JS = """
() => {
  const candidates = document.querySelectorAll(
    'a[href], button, input, select, textarea, [onclick], [role=button], ' +
    '[role=link], [role=tab], [role=menuitem], [tabindex]');
  const seen = new Set();
  const out = [];
  for (const el of candidates) {
    if (seen.has(el)) continue;
    seen.add(el);
    const rect = el.getBoundingClientRect();
    out.push({
      tag: el.tagName.toLowerCase(),
      id: el.id || null,
      classes: (el.className && el.className.baseVal !== undefined)
        ? String(el.className.baseVal) : (el.className || null),
      text: (el.innerText || el.value || '').trim().slice(0, 60) || null,
      role: el.getAttribute('role'),
      aria_label: el.getAttribute('aria-label'),
      book_route: el.getAttribute('data-book-route'),
      onclick: el.getAttribute('onclick'),
      href: el.getAttribute('href'),
      disabled: el.disabled === true,
      visible: !!(rect.width && rect.height &&
                  getComputedStyle(el).visibility !== 'hidden' &&
                  el.closest('[hidden]') === null),
    });
  }
  return out;
}
"""

MATCH_JS = """
(args) => {
  const el = document.querySelectorAll(
    'a[href], button, input, select, textarea, [onclick], [role=button], ' +
    '[role=link], [role=tab], [role=menuitem], [tabindex]')[args.index];
  if (!el) return false;
  return args.pairs.some((pair) => {
    try {
      const hit = el.matches(pair.sel) || el.closest(pair.sel) !== null;
      if (!hit) return false;
      if (!pair.text) return true;
      const txt = (el.innerText || '').trim().toLowerCase();
      if (pair.exact) return txt === pair.text.trim().toLowerCase();
      return txt.includes(pair.text.toLowerCase());
    } catch (error) { return false; }
  });
}
"""

SIGNATURE_JS = """
() => {
  const body = document.body ? document.body.innerHTML : '';
  let scrolled = Math.round(window.scrollY);
  document.querySelectorAll('*').forEach((el) => {
    if (el.scrollTop) scrolled += Math.round(el.scrollTop);
  });
  return { length: body.length, url: location.href, scrolled };
}
"""

IN_VIEWPORT_JS = """
(selector) => {
  const el = document.querySelector(selector);
  if (!el) return false;
  const rect = el.getBoundingClientRect();
  const height = window.innerHeight;
  return rect.height > 0 && rect.top > -rect.height * 0.5
    && rect.top < height * 0.85;
}
"""


def _signature(page, request_count: int) -> dict:
    raw = page.evaluate(SIGNATURE_JS)
    return {
        "dom_hash": hashlib.sha256(
            str(raw["length"]).encode() + page.url.encode()).hexdigest()[:16],
        "dom_length": raw["length"],
        "url": page.url,
        "requests": request_count,
        "scrolled": raw["scrolled"],
    }


def _idle_noise(page, request_counter: list[int]) -> tuple[int, int, dict]:
    """Measure how much the page mutates on its own (status regions,
    socket polling) so the dead-button oracle compares against real
    idle drift instead of assuming a silent page -- the Crawljax
    normalizer lesson (Regelwerk §8.3).  Returns (dom_noise,
    request_noise, settled_signature)."""
    first = _signature(page, request_counter[0])
    page.wait_for_timeout(EFFECT_SETTLE_MS)
    second = _signature(page, request_counter[0])
    return (abs(second["dom_length"] - first["dom_length"]),
            second["requests"] - first["requests"], second)


def _is_dead(before: dict, after: dict, dom_noise: int,
             request_noise: int) -> bool:
    # A pure scroll (scrollIntoView navigation aids) counts as an effect:
    # the user sees the page move even though DOM, URL and network stay put.
    return (after["url"] == before["url"]
            and abs(after["dom_length"] - before["dom_length"])
            <= max(2 * dom_noise, 64)
            and (after["requests"] - before["requests"])
            <= max(2 * request_noise, 0)
            and abs(after["scrolled"] - before["scrolled"]) <= 4)


class CrawlerRun:
    def __init__(self, out_dir: Path, seed: int) -> None:
        self.out_dir = out_dir
        self.seed = seed
        self.findings: list[dict] = []
        self.executions: list[dict] = []
        self.inventories: dict[str, dict] = {}
        self.blocked = False
        self.canary_caught: bool | None = None

    def find(self, severity: str, category: str, contract: str, expected: str,
             actual: str, evidence: list[str] | None = None) -> None:
        self.findings.append({
            "severity": severity, "category": category, "contract": contract,
            "expected": expected, "actual": actual,
            "evidence": evidence or [],
        })

    def status(self) -> str:
        if self.blocked:
            return "blocked"
        if self.canary_caught is False:
            return "inconclusive"
        if any(f["severity"] in ("blocker", "high") for f in self.findings):
            return "failed"
        return "passed"

    def write(self, seconds: float) -> None:
        counts = {"blocker": 0, "high": 0, "medium": 0, "low": 0}
        for finding in self.findings:
            counts[finding["severity"]] = counts.get(finding["severity"], 0) + 1
        payload = {
            "status": self.status(),
            "seed": self.seed,
            "seconds": round(seconds, 1),
            "severity_counts": counts,
            "canary_caught": self.canary_caught,
            "findings": self.findings,
            "executions": self.executions,
        }
        (self.out_dir / "crawler.json").write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        lines = [
            "# Button-Crawler",
            "",
            f"Status: **{payload['status']}** — seed {self.seed}, "
            f"{len(self.executions)} Ausführungen, "
            f"{len(self.findings)} Findings "
            f"(blocker:{counts['blocker']} high:{counts['high']} "
            f"medium:{counts['medium']} low:{counts['low']}), "
            f"Canary gefangen: {self.canary_caught}",
            "",
            "| Severity | Kategorie | Vertrag | Erwartet | Tatsächlich |",
            "|---|---|---|---|---|",
        ]
        for finding in self.findings:
            lines.append(
                f"| {finding['severity']} | {finding['category']} | "
                f"{finding['contract']} | {finding['expected'][:80]} | "
                f"{finding['actual'][:120]} |")
        (self.out_dir / "report.md").write_text(
            "\n".join(lines) + "\n", encoding="utf-8")


def _load_contract_pages(names: list[str]) -> list[dict]:
    pages = []
    for path in sorted(CONTRACTS_DIR.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if not names or data["page"] in names:
            pages.append(data)
    return pages


def _goto_ready(session: RobotSession, path: str, ready: str) -> bool:
    if not session.goto(path):
        return False
    try:
        session.page.wait_for_selector(ready, state="visible",
                                       timeout=READY_TIMEOUT_MS)
    except Exception:
        return False
    return True


def _run_inventory(run: CrawlerRun, session: RobotSession, contract: dict) -> None:
    elements = session.page.evaluate(ENUMERATE_JS)
    pairs = [{"sel": entry["selector"], "text": entry.get("text"),
              "exact": bool(entry.get("text_exact"))}
             for entry in contract.get("elements", [])]
    uncovered = []
    seen_keys: set[tuple] = set()
    for index, element in enumerate(elements):
        if not element["visible"]:
            continue
        covered = session.page.evaluate(
            MATCH_JS, {"index": index, "pairs": pairs})
        if not covered:
            key = (element["tag"], element["text"], element["classes"])
            if key in seen_keys:
                continue
            seen_keys.add(key)
            uncovered.append(element)
    run.inventories[contract["page"]] = {
        "total": len(elements),
        "visible": sum(1 for element in elements if element["visible"]),
        "uncovered_visible": len(uncovered),
        "elements": elements,
    }
    for element in uncovered:
        name = element["id"] or element["text"] or element["onclick"] or element["tag"]
        run.find(
            "medium", "undocumented-button", f"{contract['page']}:{name}",
            "jedes sichtbare interaktive Element hat einen Klick-Vertrag (§1)",
            f"kein Vertrag deckt <{element['tag']}> id={element['id']} "
            f"text={element['text']!r} onclick={element['onclick']!r}")


def _await_postcondition(page, expect: dict) -> str | None:
    """Return None when satisfied, otherwise a description of the miss."""
    try:
        if "route" in expect:
            page.wait_for_url(f"**{expect['route']}*",
                              timeout=POSTCONDITION_TIMEOUT_MS)
        if "visible" in expect:
            page.wait_for_selector(expect["visible"], state="visible",
                                   timeout=POSTCONDITION_TIMEOUT_MS)
        if "hidden" in expect:
            page.wait_for_selector(expect["hidden"], state="hidden",
                                   timeout=POSTCONDITION_TIMEOUT_MS)
        if "in_viewport" in expect:
            deadline = time.monotonic() + POSTCONDITION_TIMEOUT_MS / 1000
            while not page.evaluate(IN_VIEWPORT_JS, expect["in_viewport"]):
                if time.monotonic() > deadline:
                    return (f"Scroll-Ziel {expect['in_viewport']} ist nicht "
                            f"im Viewport angekommen")
                page.wait_for_timeout(200)
    except Exception:
        return f"Nachbedingung nicht erreicht (URL ist {page.url})"
    return None


def _locate(page, element: dict):
    locator = page.locator(element["selector"])
    text = element.get("text")
    if text:
        if element.get("text_exact"):
            import re
            locator = locator.filter(has_text=re.compile(
                rf"^\s*{re.escape(text)}\s*$", re.IGNORECASE))
        else:
            locator = locator.filter(has_text=text)
    if "nth" in element:
        locator = locator.nth(element["nth"])
    return locator


def _execute_contract(run: CrawlerRun, session: RobotSession, contract: dict,
                      element: dict, engine: str, request_counter: list[int],
                      credentials: dict) -> str | None:
    """Run one contract with one engine; returns the landing URL or None."""
    name = f"{contract['page']}:{element['id']}:{engine}"
    if not _goto_ready(session, contract["path"], contract["ready"]):
        run.find(element["severity"], "journey", name,
                 f"Seite {contract['path']} erreichbar und bereit",
                 "Reach-Path scheiterte — Vertrag nicht ausführbar")
        return None

    locator = _locate(session.page, element)
    try:
        count = locator.count()
    except Exception as error:
        run.find(element["severity"], "contract", name,
                 "Selektor ist auswertbar", f"Selektor-Fehler: {error}")
        return None
    if count != 1:
        run.find(element["severity"], "contract", name,
                 f"Selektor trifft genau 1 Element: {element['selector']}",
                 f"trifft {count} Elemente")
        return None

    if element.get("expect_disabled"):
        # The contract IS "this control is visibly present but inactive"
        # (e.g. the primary-guild marker).  No click.
        if locator.is_visible() and locator.is_disabled():
            run.executions.append({"contract": name, "engine": engine,
                                   "landing_url": session.page.url,
                                   "before": "", "after": ""})
        else:
            run.find(element["severity"], "contract", name,
                     "Element ist sichtbar und deaktiviert",
                     f"visible={locator.is_visible()} "
                     f"disabled={locator.is_disabled()}")
        return None

    if not locator.is_visible() or locator.is_disabled():
        run.find(element["severity"], "contract", name,
                 "Element ist sichtbar und aktiv",
                 f"visible={locator.is_visible()} disabled={locator.is_disabled()}")
        return None

    before_png = run.out_dir / "screenshots" / f"{name.replace(':', '-')}-before.png"
    after_png = run.out_dir / "screenshots" / f"{name.replace(':', '-')}-after.png"
    session.page.screenshot(path=str(before_png))
    expect = element.get("expect", {})
    if "effect" in expect:
        dom_noise, request_noise, before = _idle_noise(
            session.page, request_counter)
    else:
        dom_noise = request_noise = 0
        before = _signature(session.page, request_counter[0])
    findings_before = len(session.findings)

    try:
        if engine == "mouse":
            locator.click()
        else:
            locator.focus()
            session.page.keyboard.press("Enter")
    except Exception as error:
        run.find(element["severity"], "contract", name,
                 f"Aktion ({engine}) ist ausführbar", f"Aktion scheiterte: {error}")
        return None

    landing_url = None
    if "effect" in expect:
        session.page.wait_for_timeout(EFFECT_SETTLE_MS)
        after = _signature(session.page, request_counter[0])
        if _is_dead(before, after, dom_noise, request_noise):
            session.page.screenshot(path=str(after_png))
            run.find(element["severity"], "dead-button", name,
                     "Klick erzeugt einen beobachtbaren Effekt (§2)",
                     "keine DOM-Mutation, keine Navigation, kein Request",
                     [before_png.name, after_png.name])
        landing_url = session.page.url
    else:
        miss = _await_postcondition(session.page, expect)
        session.page.screenshot(path=str(after_png))
        if miss:
            run.find(element["severity"], "contract", name,
                     json.dumps(expect, ensure_ascii=False), miss,
                     [before_png.name, after_png.name])
        landing_url = session.page.url

    for finding in session.findings[findings_before:]:
        run.find("high", "runtime", name,
                 "keine Console-/Server-/JS-Fehler während der Aktion (Gate E)",
                 f"{finding.kind}: {finding.detail[:200]}")

    run.executions.append({
        "contract": name, "engine": engine, "landing_url": landing_url,
        "before": before_png.name, "after": after_png.name,
    })

    if element.get("resets_auth"):
        if not session.login(username=credentials["username"],
                             password=credentials["password"]):
            run.blocked = True
            run.find("blocker", "harness", name,
                     "Robot kann sich nach Abmelde-Vertrag wieder anmelden",
                     "Re-Login scheiterte — Folgeverträge liefen sonst "
                     "unbemerkt ausgeloggt weiter")
    return landing_url


def _run_canary(run: CrawlerRun, session: RobotSession, contract: dict,
                request_counter: list[int], credentials: dict) -> None:
    """Regelwerk §11: inject a dead button; the crawler must flag it."""
    if not _goto_ready(session, contract["path"], contract["ready"]):
        run.blocked = True
        return
    session.page.evaluate(
        "() => { const b = document.createElement('button');"
        " b.id = 'canaryDeadBtn'; b.type = 'button';"
        " b.textContent = 'Canary'; document.body.appendChild(b); }")
    # The canary must be clicked on the injected page -- _execute_contract
    # would re-navigate and lose the injection, so inline the click here.
    locator = session.page.locator("#canaryDeadBtn")
    dom_noise, request_noise, before = _idle_noise(session.page, request_counter)
    # force: the canary sits under the scene overlay by construction; it
    # tests the dead-button oracle, not actionability.
    locator.click(force=True)
    session.page.wait_for_timeout(EFFECT_SETTLE_MS)
    after = _signature(session.page, request_counter[0])
    run.canary_caught = _is_dead(before, after, dom_noise, request_noise)
    if not run.canary_caught:
        run.find("blocker", "canary", "canary-dead",
                 "der Crawler erkennt einen wirkungslosen Knopf",
                 "Canary-Klick wurde nicht als effektlos erkannt — "
                 "Totmann-Orakel ist blind, Lauf ist inconclusive")


def run_crawler(*, out_dir: Path, seed: int, page_names: list[str]) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "screenshots").mkdir(exist_ok=True)
    run = CrawlerRun(out_dir, seed)
    contracts = _load_contract_pages(page_names)
    if not contracts:
        print("Keine Vertrags-Seiten gefunden.", file=sys.stderr)
        return 2

    def progress(message: str) -> None:
        print(f"crawler: {message}", flush=True)

    started = time.monotonic()
    workdir = Path(tempfile.mkdtemp(prefix="vtt-crawler-"))
    try:
        with disposable_stack(workdir) as stack:
            progress("Stack läuft, minte Registrierungsschlüssel …")
            keys = mint_registration_keys(stack.database_url, count=1)
            # Register-form rules: username only [A-Za-z0-9_], password
            # needs upper+lower+digit+special (seen 2026-08-24 via the
            # crawler's own before-screenshot).
            credentials = {"username": "crawler_dm",
                           "password": "Crawler-Pass-12345!"}
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch()
                context = browser.new_context(
                    viewport={"width": 1440, "height": 900}, locale="de-DE")
                # A control Playwright cannot act on within 10s is a
                # finding, never an endless actionability retry.
                context.set_default_timeout(10_000)
                request_counter = [0]
                context.on("request", lambda _: request_counter.__setitem__(
                    0, request_counter[0] + 1))

                session = RobotSession(
                    context, base_url=stack.base_url,
                    robot_name="crawler", artifacts_dir=out_dir / "screenshots")
                session.open()

                def _contain_popup(page) -> None:
                    if page is session.page:
                        return
                    run.find("high", "containment", "popup",
                             "keine unerwarteten Popups/Tabs (§8.3 Containment)",
                             f"neue Seite geöffnet: {page.url}")
                    page.close()

                context.on("page", _contain_popup)
                if not session.register(
                        username=credentials["username"],
                        email="crawler_dm@robots.roll-drauf.de",
                        password=credentials["password"],
                        registration_key=keys[0]):
                    run.blocked = True
                    for finding in session.findings:
                        run.find("blocker", "harness", "register",
                                 "Robot-Konto ist anlegbar",
                                 f"{finding.kind}: {finding.detail[:200]}",
                                 [finding.screenshot] if finding.screenshot else [])
                else:
                    progress("registriert und eingeloggt")
                    rng = random.Random(seed)
                    for contract in contracts:
                        if not _goto_ready(session, contract["path"],
                                           contract["ready"]):
                            run.blocked = True
                            continue
                        progress(f"Inventur {contract['page']} …")
                        _run_inventory(run, session, contract)

                        jobs = [(element, engine)
                                for element in contract.get("elements", [])
                                for engine in element.get("engines", ["mouse"])]
                        rng.shuffle(jobs)
                        landings: dict[str, dict[str, str]] = {}
                        for element, engine in jobs:
                            progress(f"Vertrag {element['id']} ({engine}) …")
                            landing = _execute_contract(
                                run, session, contract, element, engine,
                                request_counter, credentials)
                            if landing:
                                landings.setdefault(
                                    element["id"], {})[engine] = landing

                        # Ein-Engine-Invariante (§3): every engine of the
                        # same contract must land on the same route.
                        for element_id, by_engine in landings.items():
                            routes = {url.split("?")[0]
                                      for url in by_engine.values()}
                            if len(routes) > 1:
                                run.find(
                                    "blocker", "engine-divergence",
                                    f"{contract['page']}:{element_id}",
                                    "Maus und Tastatur landen im selben "
                                    "Ergebnis (§3)",
                                    f"abweichende Ziele: {by_engine}")

                        _run_canary(run, session, contract,
                                    request_counter, credentials)
                browser.close()
    except StackError as error:
        run.blocked = True
        run.find("blocker", "harness", "stack",
                 "Wegwerf-Stack startet", str(error))
    except BaseException as error:  # noqa: BLE001 — Gate I: evidence survives any abort
        run.blocked = True
        run.find("blocker", "harness", "crash",
                 "Crawler läuft bis zum Ende durch",
                 f"{type(error).__name__}: {error}"[:300])
        raise
    finally:
        (out_dir / "inventory.json").write_text(
            json.dumps(run.inventories, indent=2, ensure_ascii=False),
            encoding="utf-8")
        run.write(time.monotonic() - started)
    status = run.status()
    print(f"crawler: {status} — Findings: {len(run.findings)}, "
          f"Report: {out_dir / 'report.md'}")
    return {"passed": 0, "failed": 1}.get(status, 2)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="tools.robots.crawler")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--seed", type=int, default=1234)
    parser.add_argument("--pages", default="",
                        help="Komma-Liste von Vertrags-Seiten (leer = alle)")
    args = parser.parse_args(argv)
    return run_crawler(
        out_dir=args.out, seed=args.seed,
        page_names=[name for name in args.pages.split(",") if name])


if __name__ == "__main__":
    sys.exit(main())
