"""Regression contract for the dynamic login-book height chain."""

from pathlib import Path


BOOK_SCENE_JS = Path(__file__).parents[1] / "vtt/static/js/book-scene.js"
BOOK_SCENE_CSS = Path(__file__).parents[1] / "vtt/static/css/book-scene.css"


def test_open_login_book_syncs_shell_height_to_content_height():
    source = BOOK_SCENE_JS.read_text(encoding="utf-8")

    assert "syncLoginBookHeight()" in source
    assert "this.book.style.aspectRatio = 'auto';" in source
    assert "this.book.style.height = `${contentHeight}px`;" in source
    assert "this.loginBookResizeObserver.observe(this.loginContent);" in source


def test_hidden_dashboard_scene_does_not_extend_login_scroll_height():
    source = BOOK_SCENE_CSS.read_text(encoding="utf-8")

    assert ".book-dashboard-scene[hidden]" in source
    assert ".book-dashboard-scene[hidden] {\n    display: none;\n}" in source
