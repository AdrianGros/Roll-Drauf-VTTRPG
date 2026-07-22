"""Minimal headless browser smoke for campaign and play surfaces."""

from __future__ import annotations

import os
import sys
from typing import Iterable

from playwright.sync_api import sync_playwright


def _fail(message: str) -> int:
    print(f"[browser-smoke] FAIL: {message}")
    return 1


def _run_page_checks(base_url: str, paths: Iterable[str]) -> int:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        js_errors: list[str] = []

        page.on("pageerror", lambda err: js_errors.append(str(err)))

        for path in paths:
            url = f"{base_url}{path}"
            response = page.goto(url, wait_until="domcontentloaded", timeout=20_000)
            if response is None:
                browser.close()
                return _fail(f"no HTTP response for {url}")
            if response.status >= 400:
                browser.close()
                return _fail(f"HTTP {response.status} for {url}")

            page.wait_for_timeout(400)

        browser.close()

    if js_errors:
        joined = "; ".join(js_errors[:3])
        return _fail(f"page JS errors captured: {joined}")

    print("[browser-smoke] PASS: login/campaign/play pages render without JS runtime errors.")
    return 0


def main() -> int:
    base_url = os.getenv("BASE_URL", "http://127.0.0.1:5000").rstrip("/")
    paths = (
        "/login.html",
        "/campaigns.html",
        "/play?campaign_id=1&session_id=1",
    )
    return _run_page_checks(base_url, paths)


if __name__ == "__main__":
    sys.exit(main())
