"""M17 tests: character journey productization surface checks."""

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CHARACTERS_TEMPLATE = REPO_ROOT / "vtt" / "templates" / "characters.html"
CHARACTER_SHEET_TEMPLATE = REPO_ROOT / "vtt" / "templates" / "character-sheet.html"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_characters_template_hands_creation_to_srd_creator():
    content = _read(CHARACTERS_TEMPLATE)

    assert "window.location.replace('/srd-creator')" in content
    assert "standardArrayAssignments" not in content
    assert "Roll Drauf Light" not in content


def test_characters_template_exposes_clear_archive_to_sheet_and_campaign_actions():
    content = _read(CHARACTERS_TEMPLATE)

    assert "Bogen öffnen" in content
    runtime = _read(REPO_ROOT / "vtt/static/js/book-scene.js")
    assert "Bogen öffnen" in runtime
    assert "buildIntentHref('/character-sheet', { id: character.id })" in runtime
    assert 'function renderCharacters(' not in content
    assert "Campaign Context" in content
    assert "openCharacterIdentityPicker" in content
    assert "charactersJourneyNote" in content
    assert "openCharacterSheet(id, viewMode = 'view')" in content
    assert "goToCampaignContext(campaignId)" in content
    assert "Open Campaign Context" in content
    assert "get('intent') === 'create'" in content


def test_character_sheet_template_links_view_edit_and_campaign_context():
    content = _read(CHARACTER_SHEET_TEMPLATE)

    assert 'id="sheetModeActionBtn"' in content
    assert "toggleSheetMode()" in content
    assert 'id="campaignContextBtn"' in content
    assert "openCampaignContext()" in content
    assert "sheetIdentityGrid" in content
    assert "function openIdentityPicker(identityKind)" in content
    assert "function removeIdentity(identityKind)" in content
    assert "Kampagnen-Kontext" in content
    assert "Kehre zum Kampagnen-Kontext zurück, wenn du bereit für die Session bist." in content
