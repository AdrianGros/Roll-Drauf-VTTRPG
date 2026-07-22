"""M17.8 tests: pre-table usability closeout."""

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_TEMPLATE = REPO_ROOT / "vtt" / "templates" / "dashboard.html"
CHARACTERS_TEMPLATE = REPO_ROOT / "vtt" / "templates" / "characters.html"
CHARACTER_SHEET_TEMPLATE = REPO_ROOT / "vtt" / "templates" / "character-sheet.html"
CAMPAIGNS_TEMPLATE = REPO_ROOT / "vtt" / "templates" / "campaigns.html"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_dashboard_exposes_clearer_pre_table_starting_points():
    content = _read(DASHBOARD_TEMPLATE)

    assert "Heute wichtig:" in content
    assert "Kampagnen oeffnen" in content
    assert "Charaktere oeffnen" in content
    assert "Next: open the hub, review session prep, and continue toward play." in content
    assert "Next: finish the sheet and identity, then continue into campaign prep." in content
    assert "function openCharacterCampaignContext(campaignId)" in content


def test_character_surfaces_strengthen_sheet_to_campaign_continuity():
    characters = _read(CHARACTERS_TEMPLATE)
    sheet = _read(CHARACTER_SHEET_TEMPLATE)

    assert "Next: open the sheet for final review, then return to campaign prep to assign the hero to a session." in characters
    assert "Campaigns Hub" in characters
    assert "Session Assignment Route" in characters

    assert 'id="sheetNextStepNote"' in sheet
    assert "return to campaign prep to assign this hero to a session before play" in sheet
    assert "This hero is not yet tied to a campaign." in sheet


def test_campaigns_route_aligns_hub_and_session_prep_readiness_language():
    content = _read(CAMPAIGNS_TEMPLATE)

    assert "Session-Prep oeffnen" in content
    assert "braucht noch eine aktive Session-Karte" in content
    assert "Home -> Kampagnen-Hub -> Session-Prep -> Session starten oder fortsetzen -> Play." in content
    assert "Sichtbar, aber nicht blockierend:" in content
    assert "Keine harten Vorbedingungen offen" in content


def test_closeout_keeps_play_entry_seam_owned():
    content = _read(CAMPAIGNS_TEMPLATE)

    assert "function openPlay(campaignId, sessionId)" in content
    assert "BookScene.enterPlay({" in content
    assert "sourceRoute: 'campaigns'" in content
    assert "window.location.href = `/play" not in content
