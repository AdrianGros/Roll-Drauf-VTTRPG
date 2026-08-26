"""Beyond20 real-world compatibility check (2026-08-26).

STATUS (2026-08-26): every step through "Beyond20 permission granted for
vtt.roll-drauf.de" is proven and reliable -- extension build, real
production account/campaign/session, and the native Chrome permission
dialog (handled via a real X11 click, see _xtest.py). The dndbeyond.com
-> Wizards login step is NOT reliable when driven headlessly: the Vue
login form itself is now correctly targeted (input[name='email'], not
input[type='email'] -- that was the six-iteration bug), but Wizards'
own login page resists automation intermittently (a Ketch consent
banner + non-deterministic form submission -- confirmed via network
capture that the same click sometimes POSTs to /api/login and
sometimes doesn't). This is bot-detection-shaped behavior on a
third-party page, not a bug in this script or in Beyond20.

Real-world verification was completed by a human instead (Adrian,
2026-08-26): the official store Beyond20 extension + vtt.roll-drauf.de
added as a custom domain, clicking a real roll on a real character
sheet, landed in the playtable chat. That is the result that actually
matters. Do not keep fighting the Wizards.com login with more click
simulation -- if this script is revived, the productive next step is
importing a real, already-authenticated dndbeyond.com session's
cookies rather than driving their login form.

Every prior Beyond20 test in this repo (tools/robots/flows.py's
_beyond20_bridge_flow, tests/test_external_rolls.py) is SYNTHETIC: it
hand-dispatches a fake `Beyond20_RenderedRoll` DOM event and proves our
own bridge code reacts correctly. That proves nothing about whether the
real Beyond20 extension, built from our upstream fork
(/home/admin/projects/beyond20-upstream, PR kakaroto/Beyond20#1405,
already carries "https://vtt.roll-drauf.de/play*" in its built-in
SUPPORTED_VTT_URLS), actually activates on our site and actually
relays a real roll from a real dndbeyond.com character sheet.

This script does the real thing, end to end, with no shortcuts:

1. Launches a real (headed, under Xvfb) persistent Chromium context with
   Beyond20 loaded UNPACKED from a fresh build of the fork -- the exact
   artifact a real user would eventually install.
2. Registers a throwaway bot account on the LIVE production server
   (https://vtt.roll-drauf.de) via the real public /signup.html form --
   the domain match is hardcoded to the real domain, so a disposable
   local stack can never exercise this path. Additive only (one user,
   one campaign, one session); never touches existing data.
3. Grants Beyond20 its one-time host permission for vtt.roll-drauf.de
   exactly as a human does: click the popup's "give permission" banner,
   which raises a native Chrome extension-permission dialog. That
   dialog is NOT part of any page DOM and CDP/Playwright cannot reach
   it directly -- it is clicked with a genuine synthetic X11 button
   event (XTest, see tools/robots/_xtest.py), the same input path a
   real mouse click takes, at the coordinates of the "Allow" button.
4. Logs into the real dndbeyond.com with a throwaway account, opens a
   real character sheet, and clicks a real rollable action through the
   real Beyond20 UI it injects onto the page.
5. Switches to the VTT /play tab and asserts the roll actually landed
   in the table's chat log.

Secrets: D&D Beyond credentials are read ONLY from the environment
(BEYOND20_TEST_DNDBEYOND_EMAIL / _PASSWORD) at call time, are never
written to any file, log line, or finding text, and are not retained
after the process exits.

This is inherently different from every other robot in this directory:
it is real network traffic to a live third-party site and to our own
production server, not a disposable_stack run. Run manually, not as
part of CI or run_all.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

REPO = Path(__file__).resolve().parents[2]
EXT_SRC = Path("/home/admin/projects/beyond20-upstream")
EXT_BUILD = EXT_SRC / "build" / "chrome"
VTT_BASE = "https://vtt.roll-drauf.de"
DISPLAY = os.environ.get("BEYOND20_DISPLAY", ":99")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _xtest import click as x11_click  # noqa: E402


class Finding:
    def __init__(self):
        self.items: list[str] = []

    def add(self, text: str):
        print(f"[beyond20_e2e] FINDING: {text}")
        self.items.append(text)


def ensure_xvfb():
    check = subprocess.run(["pgrep", "-f", f"Xvfb {DISPLAY}"], capture_output=True)
    if check.returncode != 0:
        subprocess.Popen(
            ["Xvfb", DISPLAY, "-screen", "0", "1280x1024x24"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        time.sleep(1.5)


def ensure_extension_built():
    if (EXT_BUILD / "manifest.json").is_file():
        return
    subprocess.run(["npx", "gulp", "build-chrome"], cwd=EXT_SRC, check=True)


def shot(path: str):
    subprocess.run(["import", "-display", DISPLAY, "-window", "root", path])


def run(dndbeyond_email: str, dndbeyond_password: str, out_dir: Path) -> int:
    findings = Finding()
    out_dir.mkdir(parents=True, exist_ok=True)
    ensure_xvfb()
    ensure_extension_built()

    profile_dir = tempfile.mkdtemp(prefix="beyond20-e2e-profile-")
    stamp = str(int(time.time()))[-6:]
    reuse_username = os.environ.get("BEYOND20_REUSE_USERNAME")
    reuse_password = os.environ.get("BEYOND20_REUSE_PASSWORD")
    bot_username = reuse_username or f"b20_robot_{stamp}"
    bot_email = f"b20.robot.{stamp}@robots.roll-drauf.de"
    bot_password = reuse_password or "B20-Robot-Test-Pass-1!"

    os.environ["DISPLAY"] = DISPLAY

    with sync_playwright() as pw:
        ctx = pw.chromium.launch_persistent_context(
            profile_dir,
            headless=False,
            viewport={"width": 1280, "height": 900},
            args=[
                f"--disable-extensions-except={EXT_BUILD}",
                f"--load-extension={EXT_BUILD}",
                "--window-position=0,0",
            ],
        )
        try:
            if not ctx.service_workers:
                ctx.wait_for_event("serviceworker", timeout=15000)
            ext_id = ctx.service_workers[0].url.split("/")[2]
            print(f"[beyond20_e2e] extension id: {ext_id}")

            vtt = ctx.pages[0] if ctx.pages else ctx.new_page()

            # ── 1. Register the throwaway bot account on production, OR
            # reuse one already created by a prior run of this script --
            # /api/auth/register is rate-limited to 3/10min, which a debug
            # loop burns through fast. ──
            if reuse_username:
                print(f"[beyond20_e2e] reusing existing account {bot_username}")
                vtt.goto(f"{VTT_BASE}/login.html", wait_until="domcontentloaded", timeout=20000)
                vtt.wait_for_function(
                    "() => document.body.classList.contains('is-book-scene-login') "
                    "&& document.querySelector('.book-cover')",
                    timeout=15000,
                )
                vtt.click(".book-cover")
                vtt.wait_for_selector("#passwordLoginForm:not([hidden])", timeout=10000)
                vtt.fill("#loginUsername", bot_username)
                vtt.fill("#loginPassword", bot_password)
                vtt.click("#passwordLoginSubmitBtn")
                try:
                    vtt.wait_for_url("**/dashboard*", timeout=15000)
                except Exception as error:
                    findings.add(f"login with reused account failed: {error}")
                    shot(str(out_dir / "login-failed.png"))
                    return 2
                print(f"[beyond20_e2e] logged in as {bot_username}")
            else:
                vtt.goto(f"{VTT_BASE}/signup.html", wait_until="domcontentloaded", timeout=20000)
                vtt.wait_for_selector("#signupForm", state="visible", timeout=15000)
                vtt.fill("#username", bot_username)
                vtt.fill("#email", bot_email)
                vtt.fill("#password", bot_password)
                vtt.click("#submitBtn")
                try:
                    vtt.wait_for_url("**/login.html*", timeout=15000)
                except Exception as error:
                    findings.add(f"signup did not redirect to login: {error}")
                    shot(str(out_dir / "signup-failed.png"))
                    return 2
                print(f"[beyond20_e2e] registered {bot_username}")

            # ── 2. Registration already authenticates the session (the
            # backend sets access/refresh cookies on 201) -- landing back
            # on /login.html means book-scene.js's own instant-transition
            # takes it straight to the dashboard, so there is no login
            # form to submit here. Navigate directly and wait for that
            # settled state rather than racing the cover animation. ──
            vtt.goto(f"{VTT_BASE}/dashboard", wait_until="domcontentloaded", timeout=20000)
            vtt.wait_for_selector("#book-dashboard-scene.is-visible", timeout=15000)
            print("[beyond20_e2e] authenticated session confirmed on /dashboard")

            # ── 3. Create a campaign + session via the real API (still an
            # authenticated fetch from the page, not a UI form -- creating
            # via forms would be a second, unrelated robot to write; the
            # thing under test here is Beyond20, not campaign creation) ──
            reuse_campaign_id = os.environ.get("BEYOND20_REUSE_CAMPAIGN_ID")
            reuse_session_id = os.environ.get("BEYOND20_REUSE_SESSION_ID")
            if reuse_campaign_id and reuse_session_id:
                campaign_id, session_id = reuse_campaign_id, reuse_session_id
                print(f"[beyond20_e2e] reusing campaign={campaign_id} session={session_id} "
                      f"(POST /api/campaigns is rate-limited to 10/hour)")
            else:
                csrf = vtt.evaluate(
                    "() => document.cookie.split('; ').find(c => c.startsWith('csrf_access_token='))"
                    "?.split('=')[1] || ''"
                )
                campaign = vtt.evaluate(
                    """async (csrf) => {
                        const r = await fetch('/api/campaigns', {
                            method: 'POST', credentials: 'include',
                            headers: {'Content-Type': 'application/json', 'X-CSRF-TOKEN': csrf},
                            body: JSON.stringify({name: 'Beyond20 E2E', max_players: 2})
                        });
                        const text = await r.text();
                        let body;
                        try { body = JSON.parse(text); } catch (e) { body = {non_json_response: text.slice(0, 300)}; }
                        return {status: r.status, body};
                    }""",
                    csrf,
                )
                if campaign["status"] != 201:
                    findings.add(f"campaign creation failed: {campaign}")
                    return 2
                campaign_id = (campaign["body"].get("campaign") or campaign["body"])["id"]
                session = vtt.evaluate(
                    """async (args) => {
                        const [csrf, campaignId] = args;
                        const r = await fetch(`/api/campaigns/${campaignId}/sessions`, {
                            method: 'POST', credentials: 'include',
                            headers: {'Content-Type': 'application/json', 'X-CSRF-TOKEN': csrf},
                            body: JSON.stringify({name: 'Beyond20 E2E Session'})
                        });
                        const text = await r.text();
                        let body;
                        try { body = JSON.parse(text); } catch (e) { body = {non_json_response: text.slice(0, 300)}; }
                        return {status: r.status, body};
                    }""",
                    [csrf, campaign_id],
                )
                if session["status"] != 201:
                    findings.add(f"session creation failed: {session}")
                    return 2
                session_id = (session["body"].get("session") or session["body"])["id"]
                print(f"[beyond20_e2e] campaign={campaign_id} session={session_id}")

            # ── 4. Open the real play table ──
            vtt.goto(f"{VTT_BASE}/play?campaign_id={campaign_id}&session_id={session_id}",
                     wait_until="domcontentloaded", timeout=20000)
            vtt.wait_for_selector("#mapViewport", state="visible", timeout=15000)

            # ── 5. Grant Beyond20's one-time host permission the way a
            # human does: popup banner click -> native Chrome dialog ->
            # real X11 click on "Allow" (see module docstring). ──
            popup = ctx.new_page()
            vtt.bring_to_front()
            time.sleep(0.3)
            popup.goto(f"chrome-extension://{ext_id}/popup.html", timeout=10000)
            time.sleep(1)
            banner = popup.locator("label[for='default-popup']")
            if banner.count() == 0:
                findings.add("Beyond20 popup did not show a permission banner "
                              "for vtt.roll-drauf.de -- either already granted "
                              "(stale profile) or the domain match failed")
            else:
                banner.click()
                time.sleep(0.8)
                shot(str(out_dir / "permission-dialog.png"))
                # "Allow" button center, measured empirically for this
                # dialog at 1280x1024 -- fragile if Chrome's dialog layout
                # changes; re-measure via the screenshot above if this
                # stops working.
                x11_click(821, 281)
                time.sleep(1)
                popup.close()
                recheck = ctx.new_page()
                vtt.bring_to_front()
                time.sleep(0.3)
                recheck.goto(f"chrome-extension://{ext_id}/popup.html", timeout=10000)
                time.sleep(0.8)
                if recheck.locator("label[for='default-popup']").count() > 0:
                    findings.add("permission banner still present after the "
                                 "Allow click -- grant did not take")
                    shot(str(out_dir / "permission-not-granted.png"))
                    return 2
                recheck.close()
            print("[beyond20_e2e] Beyond20 permission granted for vtt.roll-drauf.de")

            vtt.reload(wait_until="domcontentloaded")
            vtt.wait_for_selector("#mapViewport", state="visible", timeout=15000)
            time.sleep(1.5)  # let Beyond20's content script + bridge settle

            # ── 6. Log into dndbeyond.com with the throwaway account ──
            # D&D Beyond's own login page no longer has an email/password
            # form -- auth is unified into a Wizards of the Coast account
            # ("Sign in with Wizards"), which redirects to a separate
            # wizards.com domain that hosts the actual credential form.
            ddb = ctx.new_page()
            ddb.goto("https://www.dndbeyond.com/login", wait_until="domcontentloaded", timeout=25000)
            try:
                accept = ddb.locator("button:has-text('Accept All')")
                if accept.count() > 0:
                    accept.first.click(timeout=5000)
                    time.sleep(0.5)
            except Exception:
                pass
            try:
                ddb.click("text=Sign in with Wizards", timeout=10000)
                # myaccounts.wizards.com is a Vue SPA behind an OAuth
                # consent redirect chain: domcontentloaded fires on an
                # intermediate empty document with zero <input> elements
                # (verified: a DOM dump right after domcontentloaded showed
                # []), and the form mounts a few seconds later. networkidle
                # never resolves here (persistent background connections --
                # analytics/polling), so don't wait on it; wait_for_selector
                # below already polls, which is the right tool for "appears
                # eventually" rather than a load-state proxy for it.
                # myaccounts.wizards.com: #email/#password are wrapper DIVs
                # (Vue form-group), not the inputs themselves -- the real
                # inputs are the only input[type=email]/[type=password] on
                # a single-step form (verified via screenshot, 2026-08-26).
                email_sel = "input[name='email']"
                pw_sel = "input[type='password']"
                ddb.wait_for_selector(email_sel, timeout=25000, state="visible")
                # Ketch (the CMP behind this page's cookie banner -- visible
                # in its DOM as ketch-* classes) is known to install a
                # global click-capture listener that silently swallows page
                # interaction until consent resolves, even when the visible
                # banner itself doesn't overlap the element being clicked.
                # A normal .click() here did not dismiss it (verified: the
                # banner was still rendered in a post-click screenshot) --
                # use the same real X11 click already proven against
                # Chrome's native permission dialog, at the "Accept All"
                # button's actual screen position.
                ketch_accept = ddb.locator("#ketch-banner-button-secondary, button:has-text('Accept All')")
                if ketch_accept.count() > 0:
                    box = ketch_accept.first.bounding_box()
                    if box:
                        cx = int(box["x"] + box["width"] / 2)
                        cy = int(box["y"] + box["height"] / 2)
                        x11_click(cx, cy)
                        time.sleep(1)
                        shot(str(out_dir / "ketch-after-x11-click.png"))
                ddb.fill(email_sel, dndbeyond_email)
                ddb.fill(pw_sel, dndbeyond_password)
                all_responses = []
                def _on_response(resp):
                    if "myaccounts.wizards.com" in resp.url and "datadog" not in resp.url:
                        all_responses.append((resp.status, resp.url))
                ddb.on("response", _on_response)
                btn = ddb.locator("button:has-text('LOG IN'), button:has-text('Log In'), button[type='submit']").first
                btn.click(timeout=10000)
                time.sleep(3)
                print(f"[debug] wizards.com responses after click: {all_responses}")
                # networkidle never resolves on these pages (persistent
                # background connections, verified earlier). wait_for_url's
                # callable-predicate form also misbehaved here (matched a
                # timeout against the function repr instead of invoking it)
                # -- plain polling is dumb but reliable.
                deadline = time.time() + 25
                while time.time() < deadline and "myaccounts.wizards.com/login" in ddb.url:
                    time.sleep(0.5)
                if "myaccounts.wizards.com/login" in ddb.url:
                    raise TimeoutError(f"still on {ddb.url} 25s after clicking LOG IN")
            except Exception as error:
                findings.add(f"dndbeyond.com/Wizards login flow did not match "
                              f"expected selectors (site may have changed): {error}")
                shot(str(out_dir / "ddb-login-failed.png"))
                return 2
            if "sign-in" in ddb.url or "login" in ddb.url.lower():
                findings.add(f"still on a login-looking URL after submitting "
                              f"credentials: {ddb.url} -- login likely failed "
                              f"(wrong password, MFA challenge, or CAPTCHA)")
                shot(str(out_dir / "ddb-login-still-pending.png"))
                return 2
            print(f"[beyond20_e2e] logged into dndbeyond.com (landed on {ddb.url})")

            # ── 7. Find a character to roll from ──
            ddb.goto("https://www.dndbeyond.com/characters", wait_until="domcontentloaded", timeout=20000)
            char_link = ddb.locator("a[href*='/characters/']").first
            try:
                char_link.wait_for(state="visible", timeout=10000)
            except Exception:
                findings.add("no character found on this dndbeyond.com account -- "
                              "this throwaway account needs at least one character "
                              "(even a Free Rules pregenerated one) for Beyond20 to "
                              "have anything rollable")
                shot(str(out_dir / "ddb-no-characters.png"))
                return 2
            href = char_link.get_attribute("href")
            ddb.goto(f"https://www.dndbeyond.com{href}" if href.startswith("/") else href,
                     wait_until="load", timeout=20000)
            time.sleep(2)  # character sheet React app settle
            print(f"[beyond20_e2e] opened character sheet: {ddb.url}")

            # ── 8. Click a rollable action through Beyond20's own UI ──
            # Beyond20 adds a roll icon/button next to ability checks; the
            # ability-score box itself is clickable in the base character
            # sheet UI (Beyond20 hooks the same click).
            roll_targets = [
                ".ct-quick-info__ability .ct-quick-info__ability-score",
                ".ct-ability-summary__box",
                "[class*='ability-block'] [class*='score']",
            ]
            clicked = False
            for sel in roll_targets:
                loc = ddb.locator(sel).first
                if loc.count() > 0:
                    try:
                        loc.click(timeout=5000)
                        clicked = True
                        break
                    except Exception:
                        continue
            if not clicked:
                findings.add("could not find a clickable rollable element on the "
                              "character sheet (dndbeyond.com layout may not match "
                              "the selectors this robot knows) -- see ddb-sheet.png")
                shot(str(out_dir / "ddb-sheet.png"))
                return 2
            time.sleep(1.5)
            shot(str(out_dir / "ddb-after-roll-click.png"))
            print("[beyond20_e2e] clicked a rollable action on the character sheet")

            # ── 9. Verify the roll landed in the VTT's chat ──
            vtt.bring_to_front()
            time.sleep(1)
            landed = False
            for _ in range(10):
                chat_text = vtt.evaluate(
                    "() => (document.getElementById('activityLog')?.innerText "
                    "|| document.getElementById('diceLog')?.innerText || '')"
                )
                if chat_text.strip():
                    landed = True
                    break
                time.sleep(1)
            shot(str(out_dir / "vtt-after-roll.png"))
            if not landed:
                findings.add("no roll appeared in the VTT's chat/dice log within "
                              "10s of clicking the D&D Beyond roll -- the bridge "
                              "either never received Beyond20_RenderedRoll, or "
                              "play-ui.js never rendered it")
                return 2

            print("[beyond20_e2e] roll landed in the VTT chat -- Beyond20 compatibility CONFIRMED")
            return 0
        finally:
            (out_dir / "findings.txt").write_text("\n".join(findings.items) + "\n")
            ctx.close()


def main(argv=None) -> int:
    email = os.environ.get("BEYOND20_TEST_DNDBEYOND_EMAIL")
    password = os.environ.get("BEYOND20_TEST_DNDBEYOND_PASSWORD")
    if not email or not password:
        print("Set BEYOND20_TEST_DNDBEYOND_EMAIL and BEYOND20_TEST_DNDBEYOND_PASSWORD", file=sys.stderr)
        return 2
    out_dir = Path(os.environ.get("BEYOND20_E2E_OUT", "/tmp/beyond20-e2e"))
    return run(email, password, out_dir)


if __name__ == "__main__":
    sys.exit(main())
