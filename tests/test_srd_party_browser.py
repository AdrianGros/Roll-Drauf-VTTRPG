"""P11: campaign assignment, share link, party page and DM handouts in a real browser with two accounts."""

import re
from datetime import datetime

import pytest
from flask_jwt_extended import create_access_token

from tests.test_srd_creator_api import data  # noqa: F401
from tests.test_srd_inventory_browser import _character
from tests.test_srd_manage_browser import _page
from tests.test_srd_sheet import QuietHandler, site  # noqa: F401
from vtt.extensions import db
from vtt.models import Campaign, CampaignMember, Role, User


def _campaign_with_dm(app, player_id):
    with app.app_context():
        role = Role.query.filter_by(name="Player").first()
        dm = User(username="tisch-dm", email="dm@example.test", role_id=role.id, is_active=True)
        dm.set_password("Srd-Pass-123!")
        db.session.add(dm)
        db.session.flush()
        campaign = Campaign(name="Rolltisch", description="", owner_id=dm.id, status="active", max_players=6)
        db.session.add(campaign)
        db.session.flush()
        for user_id, campaign_role in ((dm.id, "DM"), (player_id, "Player")):
            db.session.add(CampaignMember(
                campaign_id=campaign.id, user_id=user_id, campaign_role=campaign_role, status="active",
                joined_at=datetime.utcnow(), invited_at=datetime.utcnow(), accepted_at=datetime.utcnow(), invited_by=dm.id))
        db.session.commit()
        return campaign.id, {"token": create_access_token(identity=str(dm.id)), "user_id": dm.id}


@pytest.mark.parametrize("width", [1440, 390])
def test_assign_share_party_and_handout(site, data, width):
    from playwright.sync_api import expect, sync_playwright

    app, origin, info = site
    char_id = _character(app, info, data)
    campaign_id, dm_info = _campaign_with_dm(app, info["user_id"])
    with sync_playwright() as p:
        browser, page, errors = _page(p, origin, info, width)
        page.goto(f"{origin}/character-sheet?id={char_id}&mode=edit")
        page.locator("#srdManageCampaign").select_option(label="Rolltisch")
        page.locator("#srdManageAssign").click()
        expect(page.locator("#srdManageStatus")).to_contain_text("zugeordnet")
        expect(page.locator("#srdManageParty")).to_have_attribute("href", f"/party?campaign={campaign_id}")

        page.locator("#srdManageShareOn").click()
        url_box = page.locator("#srdManageShareUrl")
        expect(url_box).to_have_value(re.compile(r"/shared-sheet#\d+-"))
        link = url_box.input_value()
        anonymous = browser.new_context(viewport={"width": width, "height": 1000}, reduced_motion="reduce").new_page()
        anonymous.set_default_timeout(15000)
        anonymous_errors = []
        anonymous.on("pageerror", lambda error: anonymous_errors.append(str(error)))
        anonymous.goto(link)
        expect(anonymous.locator("#ssTitle")).to_have_text("Mira Eulenfeder")
        expect(anonymous.locator("#ssSheet")).to_contain_text("TP 32 / 32")
        expect(anonymous.locator("#ssSheet")).to_contain_text("Magier 5")
        expect(anonymous.locator("#ssSheet")).not_to_contain_text("Fand eine Eule")
        expect(anonymous.locator("#ssSheet")).not_to_contain_text("sheet-reader")
        assert anonymous.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth") <= 1

        page.locator("#srdManageShareRegenerate").click()
        page.locator("#srdManageShareConfirm").click()
        expect(url_box).not_to_have_value(link)
        anonymous.reload()
        expect(anonymous.locator("#ssStatus")).to_contain_text("nicht (mehr) gültig")
        page.locator("#srdManageShareOff").click()
        page.locator("#srdManageShareConfirm").click()
        expect(page.locator("#srdManageShareOn")).to_be_visible()

        page.goto(f"{origin}/party?campaign={campaign_id}")
        card = page.locator(".sp-card", has_text="Mira Eulenfeder")
        expect(card).to_contain_text("TP 32 / 32")
        expect(card).to_contain_text("RK")
        expect(card).to_contain_text("Magier 5")
        expect(page.locator("#spDm")).to_be_hidden()
        expect(card.get_by_role("button", name="Gegenstand ausgeben")).to_have_count(0)
        assert page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth") <= 1

        dm_browser, dm_page, dm_errors = _page(p, origin, dm_info, width)
        dm_page.goto(f"{origin}/party?campaign={campaign_id}")
        dm_card = dm_page.locator(".sp-card", has_text="Mira Eulenfeder")
        expect(dm_card).to_contain_text("EP")
        expect(dm_page.locator("#spDm")).to_be_visible()
        dm_page.fill("#spXp", "400")
        dm_page.fill("#spNote", "Brücke gehalten")
        dm_page.locator("#spGiveXp").click()
        expect(dm_page.locator("#spStatus")).to_contain_text("EP vergeben: 1 Charakter")
        expect(dm_card).to_contain_text("6900 EP / 14000")

        dm_page.locator("#spSaveRules").click()
        expect(dm_page.locator("#spStatus")).to_contain_text("Regeln gespeichert")
        dm_page.get_by_label("Manuell").uncheck()
        dm_page.locator("#spSaveRules").click()
        dm_page.reload()
        expect(dm_page.get_by_label("Manuell")).not_to_be_checked()
        expect(dm_page.get_by_label("Punktekauf")).to_be_checked()

        dm_card = dm_page.locator(".sp-card", has_text="Mira Eulenfeder")
        dm_card.get_by_role("button", name="Gegenstand ausgeben").click()
        dialog = dm_page.locator("#spDialog")
        expect(dialog).to_be_visible()
        dm_page.fill("#spSearch", "Seil")
        results = dm_page.locator("#spResults .sp-result")
        expect(results.first).to_contain_text("Seil")
        results.first.get_by_role("button", name="Ausgeben").click()
        expect(dm_page.locator("#spHandoutMessage")).to_contain_text("ausgegeben")
        expect(dm_page.locator(".sp-given-row")).to_have_count(1)
        dm_page.locator("[data-kind=magic]").click()
        expect(dm_page.locator("#spResults .sp-result").first).to_be_visible()
        magic_name = dm_page.locator("#spResults .sp-result").first.get_attribute("data-item-name")
        dm_page.locator("#spResults .sp-result").first.get_by_role("button", name="Ausgeben").click()
        expect(dm_page.locator(".sp-given-row")).to_have_count(2)
        dm_page.locator("[data-kind=coins]").click()
        dm_page.fill("#spCoinGM", "25")
        dm_page.locator("#spGiveCoins").click()
        expect(dm_page.locator("#spHandoutMessage")).to_contain_text("Münzen ausgegeben")
        assert dm_page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth") <= 1
        dm_page.locator(".sp-given-row").first.get_by_role("button", name="Zurücknehmen").click()
        expect(dm_page.locator(".sp-given-row")).to_have_count(1)
        dm_page.locator("#spDialogClose").click()
        expect(dialog).not_to_be_visible()

        page.goto(f"{origin}/character-sheet?id={char_id}&mode=edit")
        row = page.locator(".srd-inv-item", has_text=magic_name).first
        expect(row).to_contain_text("von der Spielleitung")
        expect(row).to_contain_text("Magischer Gegenstand")
        expect(page.locator("#srdInventory")).to_contain_text("Gegenstände (1)")
        page.locator("#srdProgression summary", has_text="Verlauf").click()
        expect(page.locator("#srdProgression")).to_contain_text("Von der Spielleitung ausgegeben")
        expect(page.locator("#srdProgression")).to_contain_text("Brücke gehalten")

        assert not errors and not dm_errors and not anonymous_errors, (errors, dm_errors, anonymous_errors)
        browser.close()
