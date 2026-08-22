"""M17.2 tests: shared Book shell UX stabilization."""

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BOOK_SCENE_CSS = REPO_ROOT / "vtt" / "static" / "css" / "book-scene.css"
BOOK_SCENE_JS = REPO_ROOT / "vtt" / "static" / "js" / "book-scene.js"
DASHBOARD_TEMPLATE = REPO_ROOT / "vtt" / "templates" / "dashboard.html"
CAMPAIGNS_TEMPLATE = REPO_ROOT / "vtt" / "templates" / "campaigns.html"
CHARACTERS_TEMPLATE = REPO_ROOT / "vtt" / "templates" / "characters.html"
CHARACTER_SHEET_TEMPLATE = REPO_ROOT / "vtt" / "templates" / "character-sheet.html"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_dashboard_recent_item_actions_are_real_routes_not_fake_live_alerts():
    content = _read(DASHBOARD_TEMPLATE)

    assert "alert('Campaign '" not in content
    assert "alert('Character '" not in content
    assert "function openCampaignHub(id)" in content
    assert "function openCharacterSheet(id)" in content
    assert "Open Hub" in content
    assert "Open Sheet" in content
    assert "goTo(`/campaigns?campaign_id=${id}`);" in content
    assert "goTo(`/character-sheet?id=${id}`);" in content


def test_shared_placeholder_styles_exist_in_book_scene_css():
    content = _read(BOOK_SCENE_CSS)

    assert ".book-shell-placeholder {" in content
    assert ".book-shell-placeholder-title {" in content
    assert ".book-shell-placeholder-copy {" in content
    assert ".book-shell-placeholder-actions {" in content
    assert ".book-shell-placeholder-actions .btn[disabled]" in content
    assert ".book-scene-action-row {" in content
    assert ".book-scene-action-btn {" in content


def test_book_scene_routes_use_production_copy_and_real_feature_entry_points():
    content = _read(BOOK_SCENE_JS)

    assert "How The Chapter Feels" not in content
    assert "What Comes Next" not in content
    assert "same enchanted object" not in content
    assert "Neue Kampagne anlegen" in content
    assert "Held anlegen" in content
    assert "Hub & Session-Prep" in content
    assert "data-dashboard-href" in content
    assert "buildIntentHref('/campaigns', { classic: 1, intent: 'create' })" in content
    assert "buildIntentHref('/characters', { classic: 1, intent: 'create' })" in content


def test_campaigns_template_honestly_marks_creation_map_and_import_export_surfaces():
    content = _read(CAMPAIGNS_TEMPLATE)

    assert "+ Kampagne anlegen" in content
    assert "Neue Kampagne im Buch anlegen" in content
    assert 'id="campaignCreateForm"' in content
    assert "Kampagnen-Hub oeffnen" in content
    # Map upload is a real, working feature now (M1 of the map/token/scene
    # plan) - no longer a disabled placeholder, so it's no longer marked
    # "folgt" (coming soon). Import/Export remains an honest placeholder.
    assert "Karte hochladen" in content
    assert "uploadStandaloneMap(" in content
    assert "Import / Export folgt hier" in content
    assert "Map Import folgt" in content
    assert "Paket Export folgt" in content
    assert '<button class="btn btn-secondary" disabled>Session folgt</button>' in content


def test_character_surfaces_expose_identity_surfaces_consistently():
    characters = _read(CHARACTERS_TEMPLATE)
    sheet = _read(CHARACTER_SHEET_TEMPLATE)

    assert 'id="identityFilePicker"' in characters
    assert "openCharacterIdentityPicker" in characters
    assert "Avatar First" in characters
    assert "Token Ready" in characters

    assert "Identity Surface" in sheet
    assert 'id="sheetIdentityFilePicker"' in sheet
    assert "function openIdentityPicker(identityKind)" in sheet
    assert "function removeIdentity(identityKind)" in sheet
