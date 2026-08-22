"""Preflight: prove the harness itself before any product finding is
judged (same discipline as the Goblin Delve sister suite -- a broken
robot must never be mistaken for a broken product).

Checks, in dependency order:

  1. chromium     — Playwright can launch the browser at all
  2. postgres     — initdb/pg_ctl exist and the postgres user answers
  3. live-guard   — the refuse-live-database interlock actually refuses
  4. stack        — the disposable stack boots; /health/live answers
  5. keys         — a registration key batch can be minted
  6. register     — the real /register.html form accepts a fresh robot
                    and leaves it logged in
  7. login        — logging out and back in through /login.html works

    python -m tools.robots.preflight [--out DIR]

Exit codes: 0 = passed, 2 = blocked (infrastructure), never 1 — a
preflight cannot produce product findings by definition.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
import time
from pathlib import Path

from tools.robots.stack import (StackError, _live_database_url,
                                _refuse_live_database, disposable_stack)


def _check_chromium(record) -> None:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        record["browser"] = f"chromium {browser.version}"
        browser.close()


def _check_postgres_binaries(record) -> None:
    import subprocess
    for tool in ("initdb", "pg_ctl", "psql"):
        if not (shutil.which(tool) or Path(f"/usr/bin/{tool}").exists()):
            raise RuntimeError(f"{tool} not found on PATH or /usr/bin")
    probe = subprocess.run(["su", "postgres", "-c", "true"],
                           capture_output=True, text=True)
    if probe.returncode != 0:
        raise RuntimeError(
            f"cannot become the postgres user: {probe.stderr.strip()} "
            "(the stack needs root)")
    record["postgres"] = "binaries + user ok"


def _check_live_guard(record) -> None:
    live = _live_database_url()
    if not live:
        record["live_guard"] = "no live DATABASE_URL found (nothing to guard)"
        return
    try:
        _refuse_live_database(live)
    except StackError:
        record["live_guard"] = "interlock refuses the live database URL"
        return
    raise RuntimeError(
        "_refuse_live_database ACCEPTED the live database URL — the one "
        "check that must never be removed is not working")


def run_preflight(out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    checks: dict[str, dict] = {}

    def step(name: str, runner) -> bool:
        started = time.monotonic()
        record: dict = {}
        try:
            runner(record)
        except BaseException as error:  # noqa: BLE001 — every failure blocks
            checks[name] = {"ok": False, "detail": str(error)[:1000],
                            "seconds": round(time.monotonic() - started, 1)}
            return False
        checks[name] = {"ok": True, **record,
                        "seconds": round(time.monotonic() - started, 1)}
        return True

    ok = (step("chromium", _check_chromium)
          and step("postgres", _check_postgres_binaries)
          and step("live_guard", _check_live_guard))

    if ok:
        workdir = Path(tempfile.mkdtemp(prefix="vtt-preflight-"))
        try:
            def stack_keys_register_login(record) -> None:
                with disposable_stack(workdir) as stack:
                    record["stack"] = "up (/health/live answered)"
                    from tools.robots.accounts import mint_registration_keys
                    keys = mint_registration_keys(stack.database_url, count=2)
                    record["keys"] = f"{len(keys)} minted"

                    from playwright.sync_api import sync_playwright
                    from tools.robots.session import RobotSession
                    with sync_playwright() as playwright:
                        browser = playwright.chromium.launch()
                        context = browser.new_context(
                            viewport={"width": 1280, "height": 900})
                        session = RobotSession(
                            context, base_url=stack.base_url,
                            robot_name="preflight", artifacts_dir=workdir)
                        session.open()
                        registered = session.register(
                            username="preflight_bot",
                            email="preflight_bot@robots.roll-drauf.de",
                            password="Ro8ot-Test-Passw0rd!",
                            registration_key=keys[0])
                        if not registered:
                            detail = "; ".join(f.detail for f in session.findings)
                            raise RuntimeError(f"registration did not complete: {detail}")
                        record["register"] = "real form accepted a fresh robot"

                        # Prove login independently of the registration
                        # session: clear cookies first, otherwise
                        # /login.html's own "already authenticated ->
                        # redirect to dashboard" logic collides with the
                        # book-UI scene transition and intercepts the
                        # form's click.
                        context.clear_cookies()
                        logged_in = session.login(username="preflight_bot",
                                                  password="Ro8ot-Test-Passw0rd!")
                        if not logged_in:
                            detail = "; ".join(f.detail for f in session.findings)
                            raise RuntimeError(f"login did not complete: {detail}")
                        record["login"] = "real form accepted the same robot again"
                        browser.close()
            ok = step("stack_keys_register_login", stack_keys_register_login)
        finally:
            shutil.rmtree(workdir, ignore_errors=True)

    status = "passed" if ok else "blocked"
    result = {"status": status, "checks": checks}
    (out_dir / "preflight.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="tools.robots.preflight")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)
    out = args.out or Path(tempfile.mkdtemp(prefix="vtt-preflight-out-"))
    result = run_preflight(out)
    for name, check in result["checks"].items():
        mark = "✓" if check.get("ok") else "✗"
        detail = check.get("detail", "") or ", ".join(
            f"{k}={v}" for k, v in check.items()
            if k not in {"ok", "seconds"})
        print(f"  {mark} {name} ({check.get('seconds', '?')}s) {detail}")
    print(f"Preflight: {result['status']} · {out / 'preflight.json'}")
    return 0 if result["status"] == "passed" else 2


if __name__ == "__main__":
    sys.exit(main())
