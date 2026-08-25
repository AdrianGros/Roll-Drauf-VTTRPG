"""Emergency public-surface and Playtable empty-state contracts."""

from pathlib import Path

import pytest

from vtt import create_app


REPO_ROOT = Path(__file__).resolve().parents[1]
PLAY_TEMPLATE = REPO_ROOT / "vtt" / "templates" / "play.html"
PLAY_UI = REPO_ROOT / "vtt" / "static" / "js" / "play-ui.js"


@pytest.fixture
def app():
    return create_app(config_name="testing")


@pytest.fixture
def client(app):
    return app.test_client()


def test_root_is_the_app_front_door_not_a_showcase(client):
    """The root path leads into the product, not into a marketing landing page.

    The `/showcase` surface existed for two days (a6619f7) so the Beyond20
    maintainers had something public to look at. It is gone on purpose: this
    is a VTT, and its front door is the way in, not a pitch about itself.
    """
    response = client.get("/", follow_redirects=False)

    assert response.status_code in (301, 302, 308)
    assert response.headers["Location"].endswith("/login.html")


@pytest.mark.parametrize("path", ["/showcase", "/showcase.html"])
def test_showcase_surface_stays_removed(client, path):
    """No showcase page is served anywhere.

    These paths do not 404: serve_static() falls back to login.html for every
    unknown path, so an unrouted URL silently renders the login page (a
    pre-existing soft-404 this test does not change). What matters here is
    that the landing/pitch content is gone, so the assertion names the
    content rather than the status code.
    """
    response = client.get(path, follow_redirects=False)
    html = response.get_data(as_text=True)

    assert "Beyond20-Integration ansehen" not in html
    assert "Der offene Spieltisch" not in html
    assert 'id="login-content"' in html


def test_beyond20_review_page_is_public_and_names_the_supported_contract(client):
    response = client.get("/beyond20.html")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    for event_name in (
        "Beyond20_RenderedRoll",
        "Beyond20_UpdateHP",
        "Beyond20_UpdateConditions",
        "Beyond20_UpdateCombat",
    ):
        assert event_name in html
    assert "Sessiondaten geschützt" in html


def test_playtable_add_page_offers_upload_or_copy_never_a_dead_end():
    """'Hinzufügen' is documented (2026-08-25) as the one way to add a page,
    with an explicit rule it must never end in the old dead end this test
    used to assert on ('Alle vorhandenen Kampagnenkarten sind bereits
    Seiten' + a disabled control). That dead end is gone on purpose: a map
    already used elsewhere is now offered for copy rather than blocking.
    See docs/PLAYTABLE_AUDIT_2026-08-25.md and tests/test_layer_add_flow.py,
    which cover the copy behaviour itself end-to-end against the backend.
    """
    template = PLAY_TEMPLATE.read_text(encoding="utf-8")
    script = PLAY_UI.read_text(encoding="utf-8")

    assert 'id="layerAddStatus"' in template
    assert 'role="status"' in template
    assert 'id="layerAddUpload"' in template
    assert 'id="layerAddCopy"' in template
    assert "Alle vorhandenen Kampagnenkarten sind bereits Seiten" not in script
    assert "wird kopiert" in script
