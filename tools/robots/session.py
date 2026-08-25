"""One robot's browser session: register, log in, act -- through the
real forms, never a database shortcut past the registration key (see
accounts.py's docstring for why that one exception is legitimate).

Findings are collected the same way the Goblin Delve sister suite does:
the harness is worthless if a robot can fail silently, so the watch list
is wider than "did an exception reach the screen" --

  * any HTTP response >= 500, on any request the page made
  * any uncaught JavaScript error or console error
  * a page that never reaches the state a real user would (form stays on
    screen after submit, expected element never appears)
"""

from __future__ import annotations

from dataclasses import dataclass, field

READY_TIMEOUT_MS = 15_000


@dataclass
class Finding:
    kind: str
    detail: str
    robot: str = ""
    screenshot: str = ""

    def as_dict(self) -> dict:
        return {"kind": self.kind, "detail": self.detail,
                "robot": self.robot, "screenshot": self.screenshot}


class RobotSession:
    def __init__(self, context, *, base_url: str, robot_name: str,
                 artifacts_dir) -> None:
        self.context = context
        self.base_url = base_url.rstrip("/")
        self.robot_name = robot_name
        self.artifacts_dir = artifacts_dir
        self.findings: list[Finding] = []
        self.page = None

    # ── setup ────────────────────────────────────────────────────────

    def open(self) -> None:
        self.page = self.context.new_page()
        self.page.on("pageerror", self._on_page_error)
        self.page.on("console", self._on_console)
        self.page.on("response", self._on_response)

    def register(self, *, username: str, email: str, password: str,
                registration_key: str) -> bool:
        """Through the real /register.html form -- the one shortcut is
        the key itself (accounts.py), never the form submission."""
        self.page.goto(f"{self.base_url}/register.html",
                       wait_until="domcontentloaded")
        try:
            self.page.wait_for_selector("#registerForm", state="visible",
                                        timeout=READY_TIMEOUT_MS)
            self.page.fill("#key", registration_key)
            self.page.fill("#username", username)
            self.page.fill("#email", email)
            self.page.fill("#password", password)
            self.page.fill("#confirmPassword", password)
            self.page.click("#submitBtn")
            # A successful submit shows a "Key accepted..." banner, THEN
            # redirects after a deliberate 350ms UX delay
            # (vtt/templates/register.html) -- wait for the actual
            # navigation rather than a fixed sleep shorter than that.
            self.page.wait_for_url("**/dashboard*", timeout=READY_TIMEOUT_MS)
        except Exception as error:
            self._record("registration-failed",
                         f"{error} — last banner: {self._error_text()}")
            return False
        # A successful registration logs the user straight in (per
        # vtt/auth/routes.py's _register_user_with_registration_key,
        # which sets the same cookies login() does and returns 201) --
        # staying on /register means the form was rejected.
        if "/register" in self.page.url:
            self._record("registration-refused", self._error_text())
            return False
        return True

    def login(self, *, username: str, password: str) -> bool:
        """Through the real /login.html form."""
        self.page.goto(f"{self.base_url}/login.html",
                       wait_until="domcontentloaded")
        try:
            # The login form lives inside the book.  Its CSS visibility is
            # not enough to make it clickable while the cover is closed;
            # open the same entry surface a human uses before filling it.
            self.page.wait_for_function(
                "() => document.body.classList.contains('is-book-scene-login') "
                "&& document.querySelector('.book-cover')",
                timeout=READY_TIMEOUT_MS,
            )
            cover = self.page.locator(".book-cover[aria-pressed='false']")
            if cover.count() and cover.is_visible():
                cover.click()
            self.page.wait_for_selector("#passwordLoginForm", state="visible",
                                        timeout=READY_TIMEOUT_MS)
            self.page.fill("#loginUsername", username)
            self.page.fill("#loginPassword", password)
            # Observed once (2026-08-22): the JS that un-hides the form
            # after /api/auth/discord/status resolves can still be mid-
            # initialization the instant it becomes visible, occasionally
            # clearing a value filled a moment earlier -- the login then
            # posts empty fields ("username and password required") with
            # no client-side error shown. Re-check the actual DOM value
            # before submitting rather than trusting fill() alone.
            if self.page.input_value("#loginUsername") != username:
                self.page.fill("#loginUsername", username)
            if self.page.input_value("#loginPassword") != password:
                self.page.fill("#loginPassword", password)
            self.page.click("#passwordLoginSubmitBtn")
            # 2026-08-25: the committed login flow (login.html @35efeab)
            # navigates straight to /dashboard on success — the interim
            # #passwordLoginContinueBtn two-step no longer exists in the
            # template, and waiting for it broke crawler re-login and every
            # phone-viewport login (kulissen).  If a Continue step returns,
            # update this together with strict_journey._journey (§13).
            self.page.wait_for_url("**/dashboard*", timeout=READY_TIMEOUT_MS)
        except Exception as error:
            self._record("login-failed",
                         f"{error} — last banner: {self._error_text()}")
            return False
        if "/login" in self.page.url:
            self._record("login-refused", self._error_text())
            return False
        return True

    def goto(self, path: str) -> bool:
        try:
            response = self.page.goto(
                f"{self.base_url}{path}", wait_until="domcontentloaded",
                timeout=READY_TIMEOUT_MS)
            self.page.wait_for_timeout(300)
        except Exception as error:
            self._record("page-load-failed", f"{path}: {error}")
            return False
        if response is not None and response.status >= 400:
            self._record("page-error", f"{path}: HTTP {response.status}")
            return False
        return True

    # ── event handlers ──────────────────────────────────────────────

    def _on_page_error(self, error) -> None:
        self._record("javascript-error", str(error))

    def _on_console(self, message) -> None:
        if message.type == "error":
            self._record("console-error", message.text[:500])

    def _on_response(self, response) -> None:
        if response.status >= 500:
            self._record("server-error", f"{response.status} {response.url}")

    def _error_text(self) -> str:
        for selector in (".error:not(:empty)", "[role=alert]:not(:empty)",
                        "#statusBanner:not([hidden])"):
            locator = self.page.locator(selector).first
            if locator.count() and locator.is_visible():
                return locator.inner_text()[:300]
        return self.page.inner_text("body")[:300]

    def _record(self, kind: str, detail: str) -> None:
        screenshot = ""
        if self.page is not None:
            try:
                path = self.artifacts_dir / f"{self.robot_name}-{kind}-{len(self.findings)}.png"
                self.page.screenshot(path=str(path))
                screenshot = path.name
            except Exception:
                pass
        self.findings.append(Finding(kind=kind, detail=detail,
                                     robot=self.robot_name,
                                     screenshot=screenshot))
