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
    assert "Kampagnen öffnen" in content
    assert "Charaktere öffnen" in content
    assert "Gehe in Kampagnen, um Runden anzulegen, Hubs zu öffnen und die Vorbereitung zu starten." in content
    assert "Charaktere bleiben der Ort für Archiv, Heldenerstellung und den Rückweg in Kampagnen oder Vorbereitung." in content
    assert "function openCharacterCampaignContext(campaignId)" in content


def test_character_surfaces_strengthen_sheet_to_campaign_continuity():
    characters = _read(CHARACTERS_TEMPLATE)
    sheet = _read(CHARACTER_SHEET_TEMPLATE)

    assert "Next: open the sheet for final review, then return to campaign prep to assign the hero to a session." in characters
    assert "Campaigns Hub" in characters
    assert "Session Assignment Route" in characters

    # The character-sheet side of this continuity used to be a second,
    # static "sheetNextStepNote" element with English placeholder text
    # nothing ever populated -- removed 2026-08-23 (Arc 0.7 robot audit)
    # in favor of the one that actually works: updateJourneyContext()
    # sets #sheetNextHint's text dynamically (state-based, German,
    # matching the rest of the app), including exactly the "not yet in a
    # campaign -> assign before play" and "ready -> return to campaign
    # context" cases this test originally meant to cover.
    assert 'id="sheetNextHint"' in sheet
    assert "function updateJourneyContext(character)" in sheet
    assert "Weise ihn einer Kampagne zu, bevor es an den Tisch geht." in sheet
    assert "Kehre zum Kampagnen-Kontext zurück, wenn du bereit für die Session bist." in sheet


def test_campaigns_route_aligns_hub_and_session_prep_readiness_language():
    content = _read(CAMPAIGNS_TEMPLATE)

    assert "Session-Prep öffnen" in content
    assert "braucht noch eine aktive Session-Karte" in content
    assert "Home -> Kampagnen-Hub -> Session-Prep -> Session starten oder fortsetzen -> Play." in content
    assert "Sichtbar, aber nicht blockierend:" not in content
    assert "Keine harten Vorbedingungen offen" in content


def test_closeout_keeps_play_entry_seam_owned():
    content = _read(CAMPAIGNS_TEMPLATE)

    assert "function openPlay(campaignId, sessionId)" in content
    assert "BookScene.enterPlay({" in content
    assert "sourceRoute: 'campaigns'" in content
    assert "window.location.href = `/play" not in content
