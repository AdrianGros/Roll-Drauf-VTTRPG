"""Strict, evidence-producing browser journey for the book UI.

The existing robot modules are intentionally narrow behaviour probes.  This
module is the deep acceptance seam for the user-visible login-to-dashboard
journey: one interface produces an ordered checkpoint record and structured
findings, while the implementation owns target setup, browser telemetry,
geometry, visual evidence, accessibility probes, and matrix execution.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from PIL import Image, ImageChops

from tools.robots.accounts import mint_registration_keys
from tools.robots.report import REPO
from tools.robots.session import RobotSession
from tools.robots.stack import StackError, disposable_stack


BASELINE_DIR = REPO / "tools" / "robots" / "snapshots" / "strict_journey"
DEFAULT_OUT = REPO / "artifacts" / "robots" / "strict-journey"
PHONE_VIEWPORTS = {
    "phone-portrait": {"width": 390, "height": 844},
    "phone-landscape": {"width": 844, "height": 390},
}
DESKTOP_VIEWPORTS = {
    "desktop-wide": {"width": 1440, "height": 900},
    "desktop-large": {"width": 1920, "height": 1080},
    "desktop-narrow": {"width": 1024, "height": 900},
}
REQUIRED_CHECKPOINTS = (
    "login-initial",
    "login-ready",
    "login-recovery",
    "login-submitted",
    "dashboard-redirect",
    "dashboard-settled",
    "dashboard-keyboard",
    "logout-return",
)
CRITICAL_SELECTORS = {
    "login-initial": (
        ("login-content", "#login-content"),
        ("login-book", "#book"),
        ("login-entry", ".book-cover"),
    ),
    "login-ready": (
        ("login-form", "#passwordLoginForm"),
        ("login-username", "#loginUsername"),
        ("login-password", "#loginPassword"),
        ("login-submit", "#passwordLoginSubmitBtn"),
    ),
    "dashboard-settled": (
        ("dashboard-scene", "#book-dashboard-scene"),
        ("dashboard-page", ".book-dashboard-page"),
        ("primary-nav", ".book-dashboard-ribbon"),
        ("dashboard-heading", ".book-spread-page-title"),
        ("dashboard-identity", ".book-dashboard-crest"),
    ),
}
CRITICAL_OVERLAP_PAIRS = (
    ("primary-nav", "dashboard-heading"),
    ("dashboard-heading", "dashboard-identity"),
)


@dataclass(frozen=True)
class Rect:
    left: float
    top: float
    right: float
    bottom: float

    @property
    def width(self) -> float:
        return max(0.0, self.right - self.left)

    @property
    def height(self) -> float:
        return max(0.0, self.bottom - self.top)

    def contains(self, other: "Rect", tolerance: float = 1.0) -> bool:
        return (
            other.left >= self.left - tolerance
            and other.top >= self.top - tolerance
            and other.right <= self.right + tolerance
            and other.bottom <= self.bottom + tolerance
        )


@dataclass
class Finding:
    severity: str
    category: str
    checkpoint: str
    role: str
    viewport: str
    expected: str
    actual: str
    evidence: list[str] = field(default_factory=list)
    detail: str = ""

    def as_dict(self) -> dict[str, Any]:
        payload = {
            "severity": self.severity,
            "category": self.category,
            "checkpoint": self.checkpoint,
            "role": self.role,
            "viewport": self.viewport,
            "expected": self.expected,
            "actual": self.actual,
            "evidence": list(self.evidence),
        }
        if self.detail:
            payload["detail"] = self.detail
        return payload


def check_document_geometry(
    *,
    viewport: Rect,
    document: Rect,
    scroll_container: Rect,
    checkpoint: str,
    role: str,
    viewport_name: str,
) -> list[Finding]:
    """Check one-direction document reflow without rejecting normal scrolling."""
    del scroll_container  # vertical document growth is expected for book pages
    findings: list[Finding] = []
    if document.left < viewport.left - 1 or document.right > viewport.right + 1:
        findings.append(Finding(
            severity="high",
            category="layout",
            checkpoint=checkpoint,
            role=role,
            viewport=viewport_name,
            expected="document fits the viewport horizontally without scrolling",
            actual=(
                f"document bounds {document.left:.0f}..{document.right:.0f} "
                f"exceed viewport {viewport.left:.0f}..{viewport.right:.0f}"
            ),
        ))
    return findings


def check_critical_geometry(
    *,
    elements: dict[str, Rect],
    viewport: Rect,
    checkpoint: str,
    role: str,
    viewport_name: str,
    overlap_pairs: Iterable[tuple[str, str]] = (),
) -> list[Finding]:
    findings: list[Finding] = []
    for first, second in overlap_pairs:
        a = elements.get(first)
        b = elements.get(second)
        if not a or not b:
            continue
        if a.left < b.right and b.left < a.right and a.top < b.bottom and b.top < a.bottom:
            findings.append(Finding(
                severity="high",
                category="visual",
                checkpoint=checkpoint,
                role=role,
                viewport=viewport_name,
                expected=f"critical regions {first} and {second} do not overlap",
                actual=f"overlap: {first}={a} and {second}={b}",
            ))

    # The book is a vertically scrollable document.  A page extending below
    # the fold is expected; only horizontal overflow makes a critical region
    # unreachable without changing the page's scroll model.
    for name, rect in elements.items():
        if rect.left < viewport.left - 1 or rect.right > viewport.right + 1:
            findings.append(Finding(
                severity="high",
                category="visual",
                checkpoint=checkpoint,
                role=role,
                viewport=viewport_name,
                expected=f"critical region {name} fits horizontally within the viewport",
                actual=f"{name} exceeds viewport horizontally: {rect}",
            ))
    return findings


def classify_response(
    status: int,
    url: str,
    *,
    expected: bool = False,
    checkpoint: str = "runtime",
    role: str = "unknown",
    viewport_name: str = "unknown",
) -> Finding | None:
    if expected or status < 400:
        return None
    severity = "high" if status >= 500 or _is_critical_resource(url) else "medium"
    return Finding(
        severity=severity,
        category="network",
        checkpoint=checkpoint,
        role=role,
        viewport=viewport_name,
        expected="critical page and asset requests return below 400",
        actual=f"HTTP {status}: {url}",
    )


def _is_critical_resource(url: str) -> bool:
    lowered = url.lower().split("?", 1)[0]
    return lowered.endswith((".css", ".js", ".woff", ".woff2", ".ttf", ".png", ".jpg", ".jpeg", ".svg"))


def _rect(raw: dict[str, Any]) -> Rect:
    return Rect(float(raw["left"]), float(raw["top"]), float(raw["right"]), float(raw["bottom"]))


def _viewport_rect(page) -> Rect:
    return Rect(0, 0, float(page.evaluate("() => window.innerWidth")), float(page.evaluate("() => window.innerHeight")))


def _safe_filename(value: str) -> str:
    return "".join(char if char.isalnum() or char in "-_" else "_" for char in value)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def compare_screenshot(actual: Path, baseline: Path, diff: Path, *, max_diff_ratio: float = 0.015) -> tuple[bool, dict[str, Any]]:
    """Compare deterministic PNGs and write a diagnostic diff image."""
    if not baseline.is_file():
        return False, {"status": "missing", "baseline": str(baseline)}
    actual_image = Image.open(actual).convert("RGBA")
    baseline_image = Image.open(baseline).convert("RGBA")
    if actual_image.size != baseline_image.size:
        return False, {
            "status": "size-mismatch",
            "actual": actual_image.size,
            "baseline": baseline_image.size,
        }
    diff_image = ImageChops.difference(actual_image, baseline_image)
    changed = sum(1 for pixel in diff_image.getdata() if pixel != (0, 0, 0, 0))
    total = max(1, actual_image.width * actual_image.height)
    ratio = changed / total
    diff.parent.mkdir(parents=True, exist_ok=True)
    diff_image.save(diff)
    return ratio <= max_diff_ratio, {
        "status": "matched" if ratio <= max_diff_ratio else "different",
        "changed_pixels": changed,
        "total_pixels": total,
        "diff_ratio": round(ratio, 6),
        "actual_sha256": _sha256(actual),
        "baseline_sha256": _sha256(baseline),
    }


class StrictJourney:
    """Run one real login-to-dashboard journey with layered gates."""

    def __init__(self, *, out_dir: Path, baseline_dir: Path, update_baselines: bool = False,
                 browser_names: Iterable[str] | None = None,
                 viewport_names: Iterable[str] | None = None,
                 role_names: Iterable[str] | None = None) -> None:
        self.out_dir = out_dir
        self.baseline_dir = baseline_dir
        self.update_baselines = update_baselines
        self.browser_names = tuple(browser_names or ("chromium", "firefox", "webkit"))
        self.viewport_names = tuple(viewport_names or (*DESKTOP_VIEWPORTS, *PHONE_VIEWPORTS))
        self.role_names = tuple(role_names or ("dm", "player"))
        self.findings: list[Finding] = []
        self.checkpoints: list[dict[str, Any]] = []
        self.telemetry: list[dict[str, Any]] = []
        self._active_checkpoint = "setup"
        self._active_role = "unknown"
        self._active_viewport = "unknown"
        self._page = None

    def run(self, *, target_url: str, credentials: dict[str, dict[str, str]], stack=None) -> dict[str, Any]:
        from playwright.sync_api import sync_playwright

        self.out_dir.mkdir(parents=True, exist_ok=True)
        started = time.time()
        with sync_playwright() as playwright:
            browsers = self._browser_matrix(playwright)
            for browser_name, browser, devices in browsers:
                try:
                    for role, identity in credentials.items():
                        if role not in self.role_names:
                            continue
                        self._run_role(browser_name, browser, devices, target_url, role, identity)
                finally:
                    browser.close()
        self._write_evidence(started, target_url)
        return self.result()

    def result(self) -> dict[str, Any]:
        statuses = {finding.severity for finding in self.findings}
        status = "failed" if self.findings else "passed"
        if any(f.category == "evidence" for f in self.findings):
            status = "blocked"
        return {
            "status": status,
            "findings": [finding.as_dict() for finding in self.findings],
            "checkpoints": self.checkpoints,
            "telemetry": self.telemetry,
            "required_checkpoints": list(REQUIRED_CHECKPOINTS),
            "severity_counts": {severity: sum(1 for f in self.findings if f.severity == severity) for severity in ("blocker", "high", "medium", "low")},
            "unresolved_severities": sorted(statuses),
        }

    def _browser_matrix(self, playwright):
        # WebKit and Firefox are release-matrix cells. They are run when the
        # installed browser is available; an unavailable cell is evidence, not
        # an implicit pass.
        launchers = {
            "chromium": playwright.chromium,
            "firefox": playwright.firefox,
            "webkit": playwright.webkit,
        }
        for name in self.browser_names:
            launcher = launchers[name]
            self._active_role = "unknown"
            self._active_viewport = f"{name}-setup"
            try:
                yield name, launcher.launch(), playwright.devices
            except Exception as error:
                self._finding(
                    severity="blocker", category="evidence", checkpoint="setup",
                    expected=f"{name} browser is available for the required matrix",
                    actual=str(error),
                )

    def _run_role(self, browser_name: str, browser, devices, target_url: str, role: str, identity: dict[str, str]) -> None:
        all_viewports = dict(DESKTOP_VIEWPORTS)
        all_viewports.update(PHONE_VIEWPORTS)
        for viewport_name in self.viewport_names:
            viewport = all_viewports[viewport_name]
            context = None
            try:
                context_options = {
                    "viewport": viewport,
                    "locale": "de-DE",
                    "color_scheme": "light",
                    "reduced_motion": "reduce",
                }
                if viewport_name.startswith("phone"):
                    device_name = "iPhone 13" if browser_name == "webkit" else "Pixel 5"
                    device = devices.get(device_name)
                    if device:
                        context_options.update(device)
                        context_options["viewport"] = viewport
                    else:
                        context_options.update({"device_scale_factor": 3, "is_mobile": True, "has_touch": True})
                context = browser.new_context(**context_options)
                context.tracing.start(screenshots=True, snapshots=True)
                page = context.new_page()
                self._page = page
                self._active_role = role
                cell_name = f"{browser_name}-{viewport_name}"
                self._active_viewport = cell_name
                self._attach_telemetry(page)
                self._journey(page, target_url, role, identity, cell_name)
            except Exception as error:
                self._finding(
                    severity="blocker", category="journey", checkpoint=self._active_checkpoint,
                    expected="strict journey completes without an unhandled harness error",
                    actual=f"{type(error).__name__}: {error}",
                    detail=traceback.format_exc(limit=4),
                )
            finally:
                if context is not None:
                    trace_path = self.out_dir / "traces" / f"{_safe_filename(self._active_role)}-{_safe_filename(self._active_viewport)}.zip"
                    try:
                        context.tracing.stop(path=str(trace_path))
                    except Exception:
                        pass
                    context.close()

    def _journey(self, page, target_url: str, role: str, identity: dict[str, str], viewport_name: str) -> None:
        page.goto(f"{target_url.rstrip('/')}/login.html", wait_until="domcontentloaded", timeout=15_000)
        self._wait_for(page, "#book", "login book surface is initialized")
        self._checkpoint(page, "login-initial", role, viewport_name, path="/login.html")
        self._assert_login_initial(page)
        self._capture(page, "login-initial", role, viewport_name)

        try:
            page.click(".book-cover", timeout=5_000)
        except Exception as error:
            self._finding("blocker", "journey", "login-ready", "login cover opens the form", str(error))

        self._checkpoint(page, "login-ready", role, viewport_name)
        self._wait_for(page, "#passwordLoginForm:not([hidden])", "password login form is visible")
        self._assert_login_ready(page)
        self._capture(page, "login-ready", role, viewport_name)

        self._checkpoint(page, "login-recovery", role, viewport_name)
        try:
            page.fill("#loginUsername", "strict_invalid_user", timeout=5_000)
            page.fill("#loginPassword", "wrong-password", timeout=5_000)
            page.click("#passwordLoginSubmitBtn", timeout=5_000, no_wait_after=True)
        except Exception as error:
            self._finding("blocker", "journey", "login-recovery", "invalid login can be submitted once", str(error))
        self._wait_for(page, "#passwordLoginError:not(:empty)", "invalid login exposes a readable recovery message")
        self._assert_login_recovery(page)
        self._capture(page, "login-recovery", role, viewport_name)

        try:
            page.fill("#loginUsername", identity["username"], timeout=5_000)
            page.fill("#loginPassword", identity["password"], timeout=5_000)
        except Exception as error:
            self._finding("blocker", "journey", "login-submitted", "login fields are editable", str(error))
        try:
            # Do not let Playwright's implicit navigation wait hide the
            # checkpoint. The successful form deliberately exposes a short,
            # readable status before navigation records the redirect seam.
            page.click("#passwordLoginSubmitBtn", timeout=5_000, no_wait_after=True)
        except Exception as error:
            self._finding("blocker", "journey", "login-submitted", "login submit is actionable", str(error))
        self._checkpoint(page, "login-submitted", role, viewport_name)
        self._wait_for(page, "#passwordLoginStatus:not([hidden])", "successful login exposes a submission status")
        self._capture(page, "login-submitted", role, viewport_name)
        try:
            page.click("#passwordLoginContinueBtn", timeout=5_000)
        except Exception as error:
            self._finding("blocker", "journey", "login-submitted", "successful login exposes an actionable dashboard CTA", str(error))
        self._wait_for_url(page, "**/dashboard*")
        self._checkpoint(page, "dashboard-redirect", role, viewport_name)
        self._assert_route(page, "/dashboard")
        self._wait_for(page, "#dashboardSceneStatus:not([hidden])", "dashboard redirect exposes its loading status")
        self._capture(page, "dashboard-redirect", role, viewport_name)

        self._wait_for(page, "#book-dashboard-scene.is-visible")
        self._wait_for(page, ".book-dashboard-page")
        self._wait_until_hidden(page, "#dashboardSceneStatus", "dashboard loading status is hidden")
        self._checkpoint(page, "dashboard-settled", role, viewport_name)
        self._assert_dashboard(page, role, viewport_name)
        self._capture(page, "dashboard-settled", role, viewport_name)
        self._run_keyboard_gate(page, role, viewport_name)

        logout = page.locator("button:visible").filter(has_text="Abmelden").first
        if logout.count() == 0:
            self._finding("high", "journey", "dashboard-keyboard", "visible logout control exists", "no visible logout control")
            return
        logout.click()
        self._wait_for_url(page, "**/login.html*")
        self._checkpoint(page, "logout-return", role, viewport_name)
        self._assert_route(page, "/login.html")
        self._wait_for(page, ".book-cover", "logout returns to the readable login cover")
        self._capture(page, "logout-return", role, viewport_name)

    def _attach_telemetry(self, page) -> None:
        page.on("pageerror", lambda error: self._page_error(error))
        page.on("console", lambda message: self._console(message))
        page.on("requestfailed", lambda request: self._request_failed(request))
        page.on("response", lambda response: self._response(response))

    def _page_error(self, error) -> None:
        self.telemetry.append({"type": "pageerror", "checkpoint": self._active_checkpoint, "message": str(error)})
        self._finding("high", "runtime", self._active_checkpoint, "no uncaught page errors", str(error))

    def _request_failed(self, request) -> None:
        payload = {"type": "requestfailed", "checkpoint": self._active_checkpoint, "url": request.url, "failure": request.failure}
        self.telemetry.append(payload)
        self._finding("high", "network", self._active_checkpoint, "critical requests do not fail", f"requestfailed: {request.url} ({request.failure})")

    def _console(self, message) -> None:
        if (
            message.type == "warning"
            and "Layout was forced before the page was fully loaded" in message.text
            and "chrome://juggler/content/" in message.text
        ):
            self.telemetry.append({
                "type": "console",
                "level": message.type,
                "checkpoint": self._active_checkpoint,
                "message": message.text[:500],
                "ignored": "known-playwright-firefox-harness-warning",
            })
            return
        if (
            message.type == "error"
            and self._active_checkpoint == "login-recovery"
            and "Failed to load resource" in message.text
            and "401" in message.text
        ):
            self.telemetry.append({
                "type": "console",
                "level": message.type,
                "checkpoint": self._active_checkpoint,
                "message": message.text[:500],
                "ignored": "expected-invalid-login-response",
            })
            return
        if message.type in {"error", "warning"}:
            severity = "high" if message.type == "error" else "medium"
            self.telemetry.append({"type": "console", "level": message.type, "checkpoint": self._active_checkpoint, "message": message.text[:500]})
            self._finding(severity, "runtime", self._active_checkpoint, f"no console.{message.type} in nominal journey", message.text[:500])

    def _response(self, response) -> None:
        self.telemetry.append({"type": "response", "checkpoint": self._active_checkpoint, "status": response.status, "url": response.url, "resource_type": response.request.resource_type})
        expected_auth_failure = (
            self._active_checkpoint == "login-recovery"
            and response.status in {400, 401, 403}
            and "/api/auth/login" in response.url
        )
        finding = classify_response(response.status, response.url, expected=expected_auth_failure, checkpoint=self._active_checkpoint, role=self._active_role, viewport_name=self._active_viewport)
        if finding:
            self.findings.append(finding)

    def _assert_login_initial(self, page) -> None:
        self._assert_visible(page, "#login-content", "login surface is visible")
        if self._visible_count(page, "#book") != 1:
            self._finding("blocker", "journey", self._active_checkpoint, "the login book surface exists", "#book is missing")
        self._assert_html(page, "html", "lang", "de", "document language is German")
        self._assert_visible(page, ".book-cover", "login cover exposes the entry action")
        self._assert_no_duplicate_ids(page)

    def _assert_login_ready(self, page) -> None:
        for selector, expected in (("#loginUsername", "username input is visible"), ("#loginPassword", "password input is visible"), ("#passwordLoginSubmitBtn", "login submit is visible")):
            self._assert_visible(page, selector, expected)
        for control in ("#loginUsername", "#loginPassword"):
            self._assert_labelled(page, control)
        self._assert_accessibility_shape(page, checkpoint="login-ready")

    def _assert_login_recovery(self, page) -> None:
        error = page.locator("#passwordLoginError").first
        message = error.inner_text().strip() if error.count() else ""
        if not message:
            self._finding("high", "journey", "login-recovery", "invalid login presents a visible error message", "#passwordLoginError is empty")
        if error.get_attribute("role") != "alert":
            self._finding("high", "a11y", "login-recovery", "login error is announced as an alert", f"role={error.get_attribute('role')!r}")
        for control in ("#loginUsername", "#loginPassword"):
            described_by = (page.locator(control).get_attribute("aria-describedby") or "").split()
            if "passwordLoginError" not in described_by:
                self._finding("high", "a11y", "login-recovery", f"{control} is associated with the login error", f"aria-describedby={described_by!r}")
        if page.locator("#loginUsername").input_value() != "strict_invalid_user":
            self._finding("medium", "journey", "login-recovery", "the username remains available for correction", "username value was cleared")
        try:
            page.wait_for_function(
                "selector => { const node = document.querySelector(selector); return node && !node.disabled; }",
                arg="#passwordLoginSubmitBtn",
                timeout=5_000,
            )
        except Exception as error:
            self._finding("high", "journey", "login-recovery", "login can be retried after an invalid submit", str(error))
        self._assert_accessibility_shape(page, checkpoint="login-recovery")

    def _assert_dashboard(self, page, role: str, viewport_name: str) -> None:
        if self._visible_count(page, ".book-dashboard-scene") != 1:
            self._finding("blocker", "visual", "dashboard-settled", "exactly one dashboard scene is visible", "dashboard scene count is not exactly one")
        if self._visible_count(page, ".book-dashboard-page") != 1:
            self._finding("blocker", "visual", "dashboard-settled", "exactly one dashboard page is visible", "dashboard page count is not exactly one")
        for name, selector in CRITICAL_SELECTORS["dashboard-settled"]:
            self._assert_visible(page, selector, f"{name} is visible on settled dashboard")
        self._assert_no_duplicate_ids(page)
        self._assert_accessibility_shape(page, checkpoint="dashboard-settled")
        self._assert_dashboard_geometry(page, role, viewport_name)
        self._assert_document_geometry(page, role, viewport_name)

    def _assert_dashboard_geometry(self, page, role: str, viewport_name: str) -> None:
        raw = page.evaluate(
            """() => {
                const rect = (selector) => {
                    const node = document.querySelector(selector);
                    if (!node) return null;
                    const r = node.getBoundingClientRect();
                    return {left:r.left, top:r.top, right:r.right, bottom:r.bottom};
                };
                return {
                    viewport: {width: innerWidth, height: innerHeight},
                    elements: {
                        'book-surface': rect('#book'),
                        'dashboard-scene': rect('#book-dashboard-scene'),
                        'dashboard-page': rect('.book-dashboard-page'),
                        'primary-nav': rect('.book-dashboard-ribbon'),
                        'dashboard-heading': rect('.book-spread-page-title'),
                        'dashboard-identity': rect('.book-dashboard-crest'),
                        'primary-cta': rect('.book-home-stack .book-scene-action-btn, .book-home-quick-links .book-scene-action-btn'),
                    },
                    visibleLayers: [...document.querySelectorAll('#book-dashboard-scene, #login-content, #book-scene-turn-leaf, .book-route-turn-overlay')]
                        .filter(node => { const s=getComputedStyle(node); const r=node.getBoundingClientRect(); return s.display !== 'none' && s.visibility !== 'hidden' && parseFloat(s.opacity || '1') > 0.05 && r.width > 0 && r.height > 0; })
                        .map(node => node.id || node.className),
                };
            }"""
        )
        viewport = Rect(0, 0, raw["viewport"]["width"], raw["viewport"]["height"])
        elements = {name: _rect(value) for name, value in raw["elements"].items() if value}
        if len(raw["visibleLayers"]) > 1:
            self._finding("high", "visual", "dashboard-settled", "only the settled dashboard layer is visible", f"visible layers: {raw['visibleLayers']}")
        self.findings.extend(check_critical_geometry(
            elements=elements,
            viewport=viewport,
            checkpoint="dashboard-settled",
            role=role,
            viewport_name=viewport_name,
            overlap_pairs=CRITICAL_OVERLAP_PAIRS,
        ))
        book_surface = elements.get('book-surface')
        page = elements.get('dashboard-page')
        if book_surface and page and book_surface.bottom < page.bottom - 1:
            self._finding(
                "high",
                "visual",
                "dashboard-settled",
                "the book paper surface extends to the bottom of the page content",
                (
                    f"book surface ends at y={book_surface.bottom:.0f}, "
                    f"page content ends at y={page.bottom:.0f}"
                ),
            )

    def _assert_document_geometry(self, page, role: str, viewport_name: str) -> None:
        raw = page.evaluate(
            """() => ({
                viewport: {width: innerWidth, height: innerHeight},
                document: {left: 0, top: 0, right: document.documentElement.scrollWidth, bottom: document.documentElement.scrollHeight},
                container: {left: 0, top: 0, right: innerWidth, bottom: innerHeight}
            })"""
        )
        self.findings.extend(check_document_geometry(
            viewport=_rect(raw["viewport"] | {"left": 0, "top": 0, "right": raw["viewport"]["width"], "bottom": raw["viewport"]["height"]}),
            document=_rect(raw["document"]),
            scroll_container=_rect(raw["container"]),
            checkpoint="dashboard-settled",
            role=role,
            viewport_name=viewport_name,
        ))

    def _run_keyboard_gate(self, page, role: str, viewport_name: str) -> None:
        self._checkpoint(page, "dashboard-keyboard", role, viewport_name)
        page.keyboard.press("Tab")
        for _ in range(12):
            focus = page.evaluate(
                """() => {
                    const node = document.activeElement;
                    if (!node || node === document.body) return null;
                    const r = node.getBoundingClientRect();
                    return {tag: node.tagName, id: node.id, text: (node.innerText || node.getAttribute('aria-label') || '').trim().slice(0, 80), rect: {left:r.left, top:r.top, right:r.right, bottom:r.bottom}, outline: getComputedStyle(node).outlineStyle, boxShadow: getComputedStyle(node).boxShadow, visible: !!(r.width && r.height)};
                }"""
            )
            if focus and not focus["visible"]:
                self._finding("high", "a11y", "dashboard-keyboard", "keyboard focus is visible", f"focused element has no visible box: {focus}")
            if focus and focus.get("outline") == "none" and focus.get("boxShadow") == "none":
                self._finding("high", "a11y", "dashboard-keyboard", "keyboard focus has a visible indicator", f"focused element has no outline or box shadow: {focus}")
            if focus and not _viewport_rect(page).contains(Rect(**focus["rect"])):
                # Focus can be inside the vertically scrollable book; insist on
                # horizontal visibility and flag only complete viewport loss.
                rect = Rect(**focus["rect"])
                viewport = _viewport_rect(page)
                if rect.right <= viewport.left or rect.left >= viewport.right:
                    self._finding("high", "a11y", "dashboard-keyboard", "focused control is not fully horizontally obscured", f"focus outside viewport: {focus}")
            page.keyboard.press("Tab")
        self._assert_accessibility_shape(page, checkpoint="dashboard-keyboard")
        self._assert_text_resize(page)
        self._capture(page, "dashboard-keyboard", role, viewport_name)

    def _assert_accessibility_shape(self, page, *, checkpoint: str) -> None:
        raw = page.evaluate(
            """() => ({
                unlabeled: [...document.querySelectorAll('input, select, textarea, button, a')].filter(node => {
                    const visible = node => {
                        const r = node.getBoundingClientRect();
                        if (!r.width || !r.height) return false;
                        for (let current = node; current; current = current.parentElement) {
                            const s = getComputedStyle(current);
                            if (s.display === 'none' || s.visibility === 'hidden' || parseFloat(s.opacity || '1') <= 0.05) return false;
                        }
                        return true;
                    };
                    if (!visible(node)) return false;
                    const label = node.getAttribute('aria-label') || node.getAttribute('title') || node.innerText || document.querySelector(`label[for="${CSS.escape(node.id || '')}"]`)?.innerText || '';
                    return !label.trim();
                }).map(node => node.outerHTML.slice(0, 160)),
                headings: [...document.querySelectorAll('h1,h2,h3,h4,h5,h6')].filter(node => { const r=node.getBoundingClientRect(); return r.width && r.height && getComputedStyle(node).visibility !== 'hidden'; }).map(node => node.tagName),
                landmarks: [...document.querySelectorAll('main, nav, header, [role="main"], [role="navigation"]')].filter(node => { const r=node.getBoundingClientRect(); return r.width && r.height; }).map(node => node.tagName),
                smallTargets: [...document.querySelectorAll('#passwordLoginSubmitBtn, .book-dashboard-ribbon button, .book-scene-action-btn')].filter(node => {
                    const r = node.getBoundingClientRect();
                    if (!r.width || !r.height) return false;
                    for (let current = node; current; current = current.parentElement) {
                        const s = getComputedStyle(current);
                        if (s.display === 'none' || s.visibility === 'hidden' || parseFloat(s.opacity || '1') <= 0.05) return false;
                    }
                    return r.width < 44 || r.height < 44;
                }).map(node => `${node.id || node.className}: ${Math.round(node.getBoundingClientRect().width)}x${Math.round(node.getBoundingClientRect().height)}`),
            })"""
        )
        if raw["unlabeled"]:
            self._finding("high", "a11y", checkpoint, "visible interactive controls have accessible names", f"unlabeled controls: {raw['unlabeled'][:3]}")
        if not raw["headings"]:
            self._finding("medium", "a11y", checkpoint, "settled page exposes a visible heading", "no visible heading")
        if not raw["landmarks"]:
            self._finding("medium", "a11y", checkpoint, "settled page exposes a visible landmark", "no visible landmark")
        if raw["smallTargets"]:
            self._finding("high", "responsive", checkpoint, "primary controls are at least 44x44 CSS pixels", f"small targets: {raw['smallTargets'][:8]}")
        self._assert_contrast(page, checkpoint)

    def _assert_contrast(self, page, checkpoint: str) -> None:
        low_contrast = page.evaluate(
            """() => {
                const parse = value => {
                    const match = String(value).match(/rgba?\\(([^)]+)\\)/);
                    if (!match) return null;
                    const parts = match[1].split(',').map(part => Number.parseFloat(part.trim()));
                    return {r: parts[0], g: parts[1], b: parts[2], a: parts.length > 3 ? parts[3] : 1};
                };
                const luminance = color => {
                    const channel = value => { const normalized=value/255; return normalized <= 0.03928 ? normalized/12.92 : Math.pow((normalized+0.055)/1.055, 2.4); };
                    return 0.2126*channel(color.r) + 0.7152*channel(color.g) + 0.0722*channel(color.b);
                };
                const visible = node => { const r=node.getBoundingClientRect(); const s=getComputedStyle(node); return s.display !== 'none' && s.visibility !== 'hidden' && r.width && r.height && (node.innerText || node.value || node.getAttribute('aria-label')); };
                return [...document.querySelectorAll('h1,h2,h3,p,a,button,label,input')].filter(visible).map(node => {
                    const color = parse(getComputedStyle(node).color);
                    let background = null;
                    for (let current=node; current && !background; current=current.parentElement) {
                        const candidate = parse(getComputedStyle(current).backgroundColor);
                        if (candidate && candidate.a > 0.95) background = candidate;
                    }
                    if (!color || !background) return null;
                    const ratio = (Math.max(luminance(color), luminance(background))+0.05) / (Math.min(luminance(color), luminance(background))+0.05);
                    const size = Number.parseFloat(getComputedStyle(node).fontSize);
                    const large = size >= 18 || (size >= 14 && Number.parseInt(getComputedStyle(node).fontWeight, 10) >= 700);
                    return ratio < (large ? 3 : 4.5)
                        ? `${node.tagName} ${node.id || node.className}: ${ratio.toFixed(2)}:1 (${color.r},${color.g},${color.b} on ${background.r},${background.g},${background.b})`
                        : null;
                }).filter(Boolean);
            }"""
        )
        if low_contrast:
            self._finding("high", "a11y", checkpoint, "visible text meets the 4.5:1 or large-text 3:1 contrast threshold", f"low contrast: {low_contrast[:8]}")

    def _assert_text_resize(self, page) -> None:
        try:
            result = page.evaluate(
                """() => {
                    const html = document.documentElement;
                    const original = html.style.fontSize;
                    html.style.fontSize = '200%';
                    const controls = [...document.querySelectorAll('button,a,input,select,textarea')]
                        .filter(node => { const r=node.getBoundingClientRect(); const s=getComputedStyle(node); return s.display !== 'none' && s.visibility !== 'hidden' && r.width && r.height; })
                        .filter(node => { const r=node.getBoundingClientRect(); return r.left < 0 || r.right > innerWidth; })
                        .map(node => node.id || node.className);
                    const output = {scrollWidth: document.documentElement.scrollWidth, innerWidth, controls};
                    html.style.fontSize = original;
                    return output;
                }"""
            )
            if result["scrollWidth"] > result["innerWidth"] + 1 or result["controls"]:
                self._finding("high", "responsive", "dashboard-keyboard", "dashboard remains usable at 200% text size", f"text resize overflow: {result}")
        except Exception as error:
            self._finding("blocker", "evidence", "dashboard-keyboard", "text resize probe completes", str(error))

    def _assert_no_duplicate_ids(self, page) -> None:
        duplicates = page.evaluate("""() => {
            const counts = {};
            for (const node of document.querySelectorAll('[id]')) counts[node.id] = (counts[node.id] || 0) + 1;
            return Object.entries(counts).filter(([, count]) => count > 1).map(([id, count]) => `${id} x${count}`);
        }""")
        if duplicates:
            self._finding("high", "a11y", self._active_checkpoint, "DOM ids are unique", f"duplicate ids: {duplicates}")

    def _assert_labelled(self, page, selector: str) -> None:
        labelled = page.evaluate("selector => { const node=document.querySelector(selector); if (!node) return false; return Boolean(node.getAttribute('aria-label') || node.getAttribute('aria-labelledby') || (node.id && document.querySelector(`label[for=\"${CSS.escape(node.id)}\"]`))); }", selector)
        if not labelled:
            self._finding("high", "a11y", self._active_checkpoint, f"{selector} has an accessible label", f"{selector} is unlabeled")

    def _assert_visible(self, page, selector: str, expected: str) -> None:
        locator = page.locator(selector).first
        if locator.count() == 0 or not locator.is_visible():
            self._finding("high", "journey", self._active_checkpoint, expected, f"{selector} is missing or not visible")

    def _assert_html(self, page, selector: str, attr: str, expected: str, expected_text: str) -> None:
        actual = page.locator(selector).get_attribute(attr)
        if actual != expected:
            self._finding("high", "a11y", self._active_checkpoint, expected_text, f"{attr}={actual!r}")

    def _assert_route(self, page, expected_path: str) -> None:
        if not page.url.split("?", 1)[0].endswith(expected_path):
            self._finding("blocker", "journey", self._active_checkpoint, f"route ends with {expected_path}", page.url)

    def _visible_count(self, page, selector: str) -> int:
        return sum(1 for index in range(page.locator(selector).count()) if page.locator(selector).nth(index).is_visible())

    def _wait_for(self, page, selector: str, message: str = "") -> None:
        try:
            page.wait_for_selector(selector, state="visible", timeout=15_000)
        except Exception as error:
            self._finding("blocker", "journey", self._active_checkpoint, message or f"{selector} becomes visible", str(error))

    def _wait_for_url(self, page, pattern: str) -> None:
        try:
            page.wait_for_url(pattern, timeout=15_000)
        except Exception as error:
            self._finding("blocker", "journey", self._active_checkpoint, f"URL matches {pattern}", f"{page.url}: {error}")

    def _wait_until_hidden(self, page, selector: str, message: str) -> None:
        try:
            page.wait_for_function(
                "selector => { const node = document.querySelector(selector); return !node || node.hidden || getComputedStyle(node).display === 'none' || getComputedStyle(node).visibility === 'hidden'; }",
                arg=selector,
                timeout=15_000,
            )
        except Exception as error:
            self._finding("blocker", "journey", self._active_checkpoint, message, str(error))

    def _checkpoint(self, page, name: str, role: str, viewport_name: str, *, path: str | None = None) -> None:
        self._active_checkpoint = name
        self._active_role = role
        self._active_viewport = viewport_name
        self.checkpoints.append({
            "name": name,
            "role": role,
            "viewport": viewport_name,
            "url": page.url,
            "path": path,
            "started_at": time.time(),
        })
        try:
            metrics = page.evaluate(
                """() => {
                    const navigation = performance.getEntriesByType('navigation')[0] || {};
                    return {
                        viewport: {width: innerWidth, height: innerHeight, dpr: devicePixelRatio},
                        document: {scrollWidth: document.documentElement.scrollWidth, scrollHeight: document.documentElement.scrollHeight},
                        timing: {
                            responseEnd: navigation.responseEnd || 0,
                            domInteractive: navigation.domInteractive || 0,
                            domContentLoadedEventEnd: navigation.domContentLoadedEventEnd || 0,
                            loadEventEnd: navigation.loadEventEnd || 0,
                        },
                        marks: performance.getEntriesByType('mark').map(entry => ({name: entry.name, startTime: entry.startTime})),
                    };
                }"""
            )
            self.telemetry.append({"type": "metrics", "checkpoint": name, "role": role, "viewport": viewport_name, "data": metrics})
        except Exception as error:
            self._finding("blocker", "evidence", name, "checkpoint metrics are captured", str(error))

    def _capture(self, page, checkpoint: str, role: str, viewport_name: str) -> None:
        path = self.out_dir / "screenshots" / f"{_safe_filename(role)}-{_safe_filename(viewport_name)}-{checkpoint}.png"
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            # The successful login status is intentionally a short-lived
            # same-document checkpoint before the redirect. Waiting here
            # would move the screenshot into the next document, where
            # Playwright can block on the dashboard font load and lose the
            # submitted-state evidence entirely.
            page.wait_for_timeout(0 if checkpoint == "login-submitted" else 250)
            page.screenshot(path=str(path), full_page=False, animations="disabled", timeout=30_000)
        except Exception as error:
            self._finding("blocker", "evidence", checkpoint, "checkpoint screenshot is captured", str(error))
            return
        evidence: list[str] = [path.name]
        try:
            dom_path = self.out_dir / "dom" / f"{_safe_filename(role)}-{_safe_filename(viewport_name)}-{checkpoint}.html"
            dom_path.parent.mkdir(parents=True, exist_ok=True)
            dom_path.write_text(page.content(), encoding="utf-8")
            evidence.append(str(dom_path.relative_to(self.out_dir)))
            aria_path = self.out_dir / "aria" / f"{_safe_filename(role)}-{_safe_filename(viewport_name)}-{checkpoint}.txt"
            aria_path.parent.mkdir(parents=True, exist_ok=True)
            body = page.locator("body")
            aria_snapshot = body.aria_snapshot(timeout=5_000) if hasattr(body, "aria_snapshot") else body.inner_text(timeout=5_000)
            aria_path.write_text(str(aria_snapshot), encoding="utf-8")
            evidence.append(str(aria_path.relative_to(self.out_dir)))
        except Exception as error:
            self._finding("blocker", "evidence", checkpoint, "DOM and accessible-state evidence is captured", str(error))
        baseline = self.baseline_dir / f"{_safe_filename(role)}-{_safe_filename(viewport_name)}-{checkpoint}.png"
        if self.update_baselines:
            baseline.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, baseline)
            comparison = {"status": "updated", "actual_sha256": _sha256(path), "baseline_sha256": _sha256(baseline)}
        else:
            diff = self.out_dir / "screenshots" / f"{_safe_filename(role)}-{_safe_filename(viewport_name)}-{checkpoint}.diff.png"
            matched, comparison = compare_screenshot(path, baseline, diff)
            if comparison["status"] == "missing":
                self._finding("blocker", "evidence", checkpoint, f"reviewed screenshot baseline exists: {baseline.name}", "baseline missing; visual acceptance is inconclusive", evidence=evidence)
            elif not matched:
                self._finding("high", "visual", checkpoint, "screenshot matches the reviewed baseline", f"screenshot differs: {comparison}", evidence=[*evidence, diff.name])
        self.telemetry.append({"type": "screenshot", "checkpoint": checkpoint, "role": role, "viewport": viewport_name, "path": str(path.relative_to(self.out_dir)), "evidence": evidence, "comparison": comparison})

    def _finding(self, severity: str, category: str, checkpoint: str, expected: str, actual: str, *, evidence: list[str] | None = None, detail: str = "") -> None:
        self.findings.append(Finding(
            severity=severity,
            category=category,
            checkpoint=checkpoint,
            role=self._active_role,
            viewport=self._active_viewport,
            expected=expected,
            actual=actual,
            evidence=evidence or [],
            detail=detail,
        ))

    def _write_evidence(self, started: float, target_url: str) -> None:
        _write_json(self.out_dir / "telemetry.json", self.telemetry)
        _write_json(self.out_dir / "strict_journey.json", self.result() | {
            "target": target_url,
            "started_at": started,
            "finished_at": time.time(),
        })


def _credentials_for_local(stack) -> dict[str, dict[str, str]]:
    keys = mint_registration_keys(stack.database_url, count=2)
    from playwright.sync_api import sync_playwright
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        session = RobotSession(context, base_url=stack.base_url, robot_name="strict-setup", artifacts_dir=stack.data_dir.parent)
        session.open()
        identities = {}
        for role, username, index in (("dm", "strict_dm", 0), ("player", "strict_player", 1)):
            password = "Ro8ot-Test-Passw0rd!"
            if not session.register(username=username, email=f"{username}@robots.roll-drauf.de", password=password, registration_key=keys[index]):
                raise StackError(f"strict {role} registration failed: {[f.detail for f in session.findings]}")
            identities[role] = {"username": username, "password": password}
            session.page.goto(f"{stack.base_url}/login.html?logged_out=1", wait_until="domcontentloaded")
            session.page.wait_for_timeout(500)
            context.clear_cookies()
        browser.close()
        return identities


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="tools.robots.strict_journey")
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--target", choices=("local", "url"), default="local")
    parser.add_argument("--url", default=None, help="read-only target base URL when --target=url")
    parser.add_argument("--baseline-dir", type=Path, default=BASELINE_DIR)
    parser.add_argument("--update-baselines", action="store_true")
    parser.add_argument("--browsers", default="chromium,firefox,webkit", help="comma-separated browser engines")
    parser.add_argument("--viewports", default=",".join((*DESKTOP_VIEWPORTS, *PHONE_VIEWPORTS)), help="comma-separated named viewports")
    parser.add_argument("--roles", default="dm,player", help="comma-separated roles")
    args = parser.parse_args(argv)
    out_dir = args.out or DEFAULT_OUT
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        if args.target == "local":
            workdir = Path(tempfile.mkdtemp(prefix="vtt-strict-"))
            with disposable_stack(workdir) as stack:
                credentials = _credentials_for_local(stack)
                result = StrictJourney(out_dir=out_dir, baseline_dir=args.baseline_dir,
                                       update_baselines=args.update_baselines,
                                       browser_names=[name for name in args.browsers.split(",") if name],
                                       viewport_names=[name for name in args.viewports.split(",") if name],
                                       role_names=[name for name in args.roles.split(",") if name]).run(target_url=stack.base_url, credentials=credentials, stack=stack)
        else:
            target_url = (args.url or os.environ.get("STRICT_ROBOT_TARGET_URL") or "").rstrip("/")
            if not target_url.startswith("https://"):
                raise StackError("--target=url requires an HTTPS URL; live visual mode is read-only")
            credentials = {
                "dm": {"username": os.environ.get("STRICT_ROBOT_DM_USERNAME", ""), "password": os.environ.get("STRICT_ROBOT_DM_PASSWORD", "")},
                "player": {"username": os.environ.get("STRICT_ROBOT_PLAYER_USERNAME", ""), "password": os.environ.get("STRICT_ROBOT_PLAYER_PASSWORD", "")},
            }
            if any(not item for identity in credentials.values() for item in identity.values()):
                raise StackError("read-only URL mode requires STRICT_ROBOT_{DM,PLAYER}_{USERNAME,PASSWORD}")
            result = StrictJourney(out_dir=out_dir, baseline_dir=args.baseline_dir,
                                   browser_names=[name for name in args.browsers.split(",") if name],
                                   viewport_names=[name for name in args.viewports.split(",") if name],
                                   role_names=[name for name in args.roles.split(",") if name]).run(target_url=target_url, credentials=credentials)
    except Exception as error:
        result = {"status": "blocked", "findings": [{"severity": "blocker", "category": "evidence", "checkpoint": "setup", "role": "unknown", "viewport": "unknown", "expected": "strict journey can initialize its declared target", "actual": f"{type(error).__name__}: {error}"}], "checkpoints": [], "telemetry": []}
        _write_json(out_dir / "strict_journey.json", result)

    report = out_dir / "report.md"
    lines = ["# Strict journey robot", "", f"Status: **{result['status']}**", "", f"Findings: **{len(result.get('findings', []))}**", ""]
    for finding in result.get("findings", []):
        lines.append(f"- **{finding['severity']}** `{finding['category']}` `{finding['checkpoint']}` ({finding['role']} / {finding['viewport']}): {finding['actual']}")
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"strict_journey · {result['status']} · {len(result.get('findings', []))} finding(s)")
    print(f"JSON: {out_dir / 'strict_journey.json'}")
    return {"passed": 0, "failed": 1, "blocked": 2, "inconclusive": 2}.get(result["status"], 2)


if __name__ == "__main__":
    sys.exit(main())
