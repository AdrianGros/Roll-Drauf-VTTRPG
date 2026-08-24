"""Every rendered HTML surface uses the exact Roll-Drauf browser icon."""

from pathlib import Path


TEMPLATES_ROOT = Path(__file__).parents[1] / "vtt/templates"
ICON_HREF = "/static/assets/sternenstaub/icons/server-icon.png"


def test_all_html_templates_declare_the_shared_browser_icon():
    templates = sorted(TEMPLATES_ROOT.glob("*.html")) + sorted(
        (TEMPLATES_ROOT / "admin").glob("*.html")
    )

    assert templates
    for template in templates:
        html = template.read_text(encoding="utf-8")
        assert f'href="{ICON_HREF}"' in html, template
        assert html.count('rel="icon"') == 1, template
