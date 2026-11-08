"""Real browser: Beyond20 on the fullscreen table.

The dice log sits in the closed menu, so a roll from D&D Beyond also shows on
the map for a few seconds, and the top row says whether Beyond20 is on the
page. The events carry the shapes Beyond20 2.21 dispatches: `detail` is the
argument array and a rendered roll names the character as a plain string.
"""
from playwright.sync_api import expect

from tests.test_table_seat_browser import table  # noqa: F401

RENDERED_ATTACK = {
    "action": "rendered-roll", "rendered": "fallback",
    "request": {"action": "roll", "type": "attack", "character": {"name": "Thorin", "type": "Character"}},
    "title": "Longsword", "html": "<div>...</div>", "character": "Thorin", "whisper": 0,
    "play_sound": False, "source": "", "attributes": {}, "description": "",
    "attack_rolls": [{
        "formula": "1d20+5", "type": "to-hit", "total": 19, "discarded": False,
        "critical-success": False, "critical-failure": False,
        "parts": [{"total": 14, "formula": "1d20", "rolls": [{"roll": 14}], "amount": 1, "faces": 20}, "+", 5],
    }],
    "roll_info": [["Range", "5 ft"]],
    "damage_rolls": [["Slashing", {
        "formula": "1d8+3", "type": "damage", "total": 9,
        "parts": [{"total": 6, "formula": "1d8", "rolls": [{"roll": 6}], "amount": 1, "faces": 8}, "+", 3],
    }, 0]],
    "total_damages": {}, "open": False,
}


def _dispatch(page, name, detail):
    page.evaluate("([name, detail]) => document.dispatchEvent(new CustomEvent(name, {detail}))", [name, detail])


def test_top_row_shows_when_beyond20_is_on_the_page(table):
    page = table["open_as"]("player")
    chip = page.locator("#beyond20Chip")
    expect(chip).to_be_hidden()

    _dispatch(page, "Beyond20_Loaded", [{}])

    expect(chip).to_be_visible()
    expect(page.locator("#beyond20Status")).to_have_attribute("data-state", "active")


def test_a_roll_from_dnd_beyond_shows_on_the_map_for_the_whole_table(table):
    dm = table["open_as"]("dm")
    player = table["open_as"]("player")

    _dispatch(player, "Beyond20_RenderedRoll", [RENDERED_ATTACK])

    for page in (player, dm):
        card = page.locator("#rollFeed .roll-feed-card")
        expect(card).to_have_count(1)
        expect(card.locator(".roll-feed-who")).to_have_text("Thorin")
        expect(card.locator(".roll-feed-total")).to_have_text("19")
        expect(card.locator(".roll-feed-title")).to_have_text("Longsword")
        expect(card.locator(".roll-feed-detail")).to_have_text("to-hit 19 · Slashing 9")
        expect(page.locator("#diceLog .ext-roll-card")).to_have_count(1)

    # Top right over the map, and clicks still reach the map underneath.
    feed = player.locator("#rollFeed")
    assert feed.evaluate("node => getComputedStyle(node).pointerEvents") == "none"
    box = feed.bounding_box()
    assert box["x"] > 1440 / 2 and box["y"] < 100, box
