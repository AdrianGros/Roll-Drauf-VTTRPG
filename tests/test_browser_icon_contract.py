"""Every rendered HTML surface uses the exact Roll-Drauf browser icon.

The icon served is a 64px delivery derivative of the exact server icon
(2026-08-25): the original attachment was an 800x800/520KB PNG, absurd as
a favicon and a real cost on every page load. The original stays in the
repo untouched — the derivative is the same artwork at favicon size, and
this contract pins both facts.
"""

from pathlib import Path


TEMPLATES_ROOT = Path(__file__).parents[1] / "vtt/templates"
ICON_HREF = "/static/assets/sternenstaub/icons/server-icon-64.png"
ICON_SOURCE = Path(__file__).parents[1] / "vtt/static/assets/sternenstaub/icons/server-icon.png"
ICON_DERIVATIVE = Path(__file__).parents[1] / "vtt/static/assets/sternenstaub/icons/server-icon-64.png"


def test_icon_derivative_exists_and_original_is_kept():
    assert ICON_SOURCE.is_file(), "the exact original attachment must stay in the repo"
    assert ICON_DERIVATIVE.is_file()
    assert ICON_DERIVATIVE.stat().st_size < 32_000


def test_all_html_templates_declare_the_shared_browser_icon():
    templates = sorted(TEMPLATES_ROOT.glob("*.html")) + sorted(
        (TEMPLATES_ROOT / "admin").glob("*.html")
    )

    assert templates
    for template in templates:
        html = template.read_text(encoding="utf-8")
        assert f'href="{ICON_HREF}"' in html, template
        assert html.count('rel="icon"') == 1, template
