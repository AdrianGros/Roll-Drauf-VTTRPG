"""Browser evidence helpers shared by the visual robots.

Every checked view gets a normal viewport screenshot. Findings get a second
capture with red boxes drawn around the relevant DOM elements. The marks are
temporary browser overlays, so they never alter the application under test.
"""

from __future__ import annotations

import re
from pathlib import Path


def _safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", str(value)).strip("-") or "view"


_MARK_SCRIPT = """marks => {
    const old = document.querySelectorAll('[data-robot-red-mark]');
    old.forEach(el => el.remove());
    const list = Array.isArray(marks) && marks.length ? marks : [null];
    const viewportW = window.innerWidth;
    const viewportH = window.innerHeight;
    list.forEach((selector, index) => {
        let rect = null;
        if (selector) {
            try {
                const target = document.querySelector(selector);
                if (target) {
                    const box = target.getBoundingClientRect();
                    rect = {left: box.left, top: box.top,
                            width: box.width, height: box.height};
                }
            } catch (_) {
                // A missing/invalid selector is still a finding. Mark the
                // viewport edge so the screenshot is visibly reviewable.
            }
        }
        if (!rect || rect.width <= 0 || rect.height <= 0) {
            rect = {left: 4, top: 4, width: viewportW - 8, height: viewportH - 8};
        }
        const left = Math.max(2, Math.min(viewportW - 6, rect.left));
        const top = Math.max(2, Math.min(viewportH - 6, rect.top));
        const width = Math.max(12, Math.min(viewportW - left - 4, rect.width));
        const height = Math.max(12, Math.min(viewportH - top - 4, rect.height));
        const mark = document.createElement('div');
        mark.dataset.robotRedMark = String(index);
        Object.assign(mark.style, {
            position: 'fixed', left: `${left}px`, top: `${top}px`,
            width: `${width}px`, height: `${height}px`,
            border: '4px solid #e00000',
            background: 'rgba(224, 0, 0, 0.08)',
            boxShadow: '0 0 0 2px rgba(255,255,255,0.9), 0 0 0 6px rgba(224,0,0,0.55)',
            pointerEvents: 'none', zIndex: '2147483647', boxSizing: 'border-box'
        });
        document.documentElement.appendChild(mark);
    });
}"""


def capture(page, directory: Path, name: str, marks: list[str] | None = None) -> Path:
    """Capture a viewport screenshot, optionally with temporary red marks."""

    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{_safe_name(name)}.png"
    marked = [str(mark) for mark in (marks or []) if mark]
    try:
        if marked:
            page.evaluate(_MARK_SCRIPT, marked)
        page.screenshot(path=str(path))
    finally:
        if marked:
            try:
                page.evaluate(
                    """() => document.querySelectorAll('[data-robot-red-mark]')
                        .forEach(el => el.remove())""")
            except Exception:
                pass
    return path


def finding(findings: list[str], page, directory: Path, detail: str,
            name: str, marks: list[str] | None = None) -> Path | None:
    """Record a finding and retain the red-box evidence path beside it."""

    try:
        path = capture(page, directory, name, marks=marks)
        findings.append(f"{detail} (screenshot: {path})")
        return path
    except Exception as error:
        findings.append(f"{detail} (screenshot failed: {type(error).__name__}: {error})")
        return None
