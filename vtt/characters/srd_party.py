"""Campaign side of SRD characters: party view, campaign rules, share links and the DM's tools.

Pure functions; `srd_party_routes.py` does permissions, rate limits and the commit.
"""

import copy
import hmac
import secrets

from sqlalchemy.orm.attributes import flag_modified

from vtt.characters import sheet_link, srd_inventory, srd_manage, srd_progression
from vtt.characters.srd_progression import ProgressionError, _log
from vtt.extensions import db
from vtt.models import Character, GameSession, InventoryItem, TokenState
from vtt.models.campaign_srd_rules import CampaignSrdRules
from vtt.play.conditions import CONDITION_CATALOG
from vtt.rules_content.creator_rules import load_creator_data
from vtt.utils.time import utcnow

ABILITY_METHODS = {
    "standard-array": "Standardsatz",
    "point-buy": "Punktekauf",
    "roll": "Würfeln (4W6)",
    "manual": "Manuell",
}
MAX_AWARD_XP = 1_000_000
MAX_DESCRIPTION = 4000
MAX_SEARCH = 30
_CONDITION_LABELS = {entry["id"]: entry["label"] for entry in CONDITION_CATALOG}
_LIVE = ("scheduled", "ready", "in_progress", "paused")


# --------------------------------------------------------------------------- campaign rules

def allowed_ability_methods(campaign_id):
    row = db.session.get(CampaignSrdRules, campaign_id)
    stored = row.ability_methods if row and isinstance(row.ability_methods, list) else []
    chosen = [m for m in ABILITY_METHODS if m in stored]
    return chosen or list(ABILITY_METHODS)


def campaign_rules(campaign_id):
    return {"attributeMethods": allowed_ability_methods(campaign_id), "allMethods": [{"id": k, "label": v} for k, v in ABILITY_METHODS.items()]}


def set_campaign_rules(campaign_id, body, *, user_id):
    methods = body.get("attributeMethods") if isinstance(body, dict) else None
    if not isinstance(methods, list) or not methods or any(m not in ABILITY_METHODS for m in methods):
        raise ProgressionError("invalid_methods", "Wähle mindestens eine Methode aus: " + ", ".join(ABILITY_METHODS) + ".", 400)
    row = db.session.get(CampaignSrdRules, campaign_id)
    if row is None:
        row = CampaignSrdRules(campaign_id=campaign_id)
        db.session.add(row)
    row.ability_methods = [m for m in ABILITY_METHODS if m in methods]
    row.updated_by = user_id


def check_ability_method(state, campaign_id):
    """A new character may only join a campaign whose rules allow the attribute method it was built with."""
    if not campaign_id:
        return
    allowed = allowed_ability_methods(campaign_id)
    method = (state or {}).get("abilityMethod")
    if method not in allowed:
        names = ", ".join(ABILITY_METHODS[m] for m in allowed)
        used = ABILITY_METHODS.get(method, "keine Methode")
        raise ProgressionError(
            "ability_method_not_allowed",
            f"Diese Kampagne erlaubt nur: {names}. Der Charakter wurde mit „{used}“ gebaut.", 422,
            allowed=allowed,
        )


def check_character_for_campaign(char, campaign_id):
    block = (char.character_data or {}).get("srd") if isinstance(char.character_data, dict) else None
    if isinstance(block, dict):
        check_ability_method(block.get("state"), campaign_id)


# --------------------------------------------------------------------------- party view

def _conditions_by_character(campaign_id):
    rows = (
        TokenState.query.join(GameSession, TokenState.game_session_id == GameSession.id)
        .filter(GameSession.campaign_id == campaign_id, GameSession.status.in_(_LIVE),
                TokenState.deleted_at.is_(None), TokenState.character_id.isnot(None))
        .all()
    )
    out = {}
    for token in rows:
        raw = (token.metadata_json or {}).get("conditions")
        for cid in raw if isinstance(raw, list) else []:
            if isinstance(cid, str) and cid in _CONDITION_LABELS and cid not in out.setdefault(token.character_id, []):
                out[token.character_id].append(cid)
    return out


def party(campaign, *, viewer_is_dm):
    data = load_creator_data()
    conditions = _conditions_by_character(campaign.id)
    characters = Character.query.filter_by(campaign_id=campaign.id, deleted_at=None).order_by(Character.name.asc(), Character.id.asc()).all()
    rows = []
    for char in characters:
        if srd_manage.is_archived(char):
            continue
        evaluation = sheet_link.srd_evaluation(char)
        row = {
            "id": char.id, "name": char.name, "owner": char.user.username if char.user else None,
            "species": char.race, "className": char.class_name, "level": char.level,
            "hpCurrent": char.hp_current, "hpMax": char.hp_max, "srd": evaluation is not None,
            "conditions": [{"id": c, "label": _CONDITION_LABELS[c]} for c in conditions.get(char.id, [])],
            "ac": char.ac, "href": f"/character-sheet?id={char.id}",
        }
        if evaluation:
            casting = next(iter(evaluation["spellcasting"]["classes"].values()), None)
            row.update(
                ac=evaluation["armorClass"]["value"], speedMeters=evaluation["speedMeters"],
                passivePerception=evaluation["passivePerception"], initiative=evaluation["initiative"],
                abilities={key: value["score"] for key, value in evaluation["abilities"].items()},
                spellSaveDc=casting["saveDc"] if casting else None,
            )
            if viewer_is_dm:
                status = srd_progression.status(char, data)
                row["progress"] = {key: status[key] for key in ("mode", "xp", "nextLevelXp", "canLevelUp", "targetLevel")}
        rows.append(row)
    return rows


def award(campaign, body, *, user_id):
    """XP or a milestone target for several characters of the campaign in one go (caller commits)."""
    if not isinstance(body, dict):
        raise ProgressionError("invalid_body", "JSON-Objekt erwartet.", 400)
    payload = {key: body[key] for key in ("addXp", "milestoneTarget", "note") if key in body}
    if "addXp" in payload and (type(payload["addXp"]) is not int or not 1 <= payload["addXp"] <= MAX_AWARD_XP):
        raise ProgressionError("invalid_xp", f"Vergib 1 bis {MAX_AWARD_XP} Erfahrungspunkte.", 400)
    if not ({"addXp", "milestoneTarget"} & set(payload)):
        raise ProgressionError("invalid_award", "Sende addXp oder milestoneTarget.", 400)
    ids = body.get("characterIds")
    if ids is not None and (not isinstance(ids, list) or any(type(i) is not int for i in ids) or len(ids) > 50):
        raise ProgressionError("invalid_ids", "characterIds muss eine Liste von Charakter-IDs sein.", 400)
    data = load_creator_data()
    changed = []
    for char in Character.query.filter_by(campaign_id=campaign.id, deleted_at=None).order_by(Character.id).all():
        if (ids is not None and char.id not in ids) or srd_manage.is_archived(char) or sheet_link.srd_evaluation(char) is None:
            continue
        if srd_progression.set_progression(char, data, payload, user_id=user_id)["changed"]:
            changed.append(char.id)
    return changed


# --------------------------------------------------------------------------- share link

def _sharing(char):
    stored = (char.character_data or {}).get("sharing") if isinstance(char.character_data, dict) else None
    return stored if isinstance(stored, dict) else {}


def sharing_info(char):
    stored = _sharing(char)
    enabled = bool(stored.get("enabled") and stored.get("secret"))
    return {"enabled": enabled, "token": f"{char.id}-{stored['secret']}" if enabled else None}


def set_sharing(char, enabled, *, regenerate=False):
    if not isinstance(enabled, bool) or not isinstance(regenerate, bool):
        raise ProgressionError("invalid_sharing", "enabled und regenerate müssen true oder false sein.", 400)
    stored = _sharing(char)
    data = copy.deepcopy(char.character_data)
    if enabled:
        secret = stored.get("secret") if stored.get("enabled") and not regenerate else secrets.token_urlsafe(18)
        data["sharing"] = {"enabled": True, "secret": secret, "since": stored.get("since") if secret == stored.get("secret") else utcnow().isoformat() + "Z"}
    else:
        data.pop("sharing", None)
    char.character_data = data
    flag_modified(char, "character_data")


def find_shared(token):
    """The character a share token opens, else None. The secret is compared in constant time."""
    if not isinstance(token, str) or len(token) > 80:
        return None
    ident, _, secret = token.partition("-")
    if not ident.isdigit() or len(ident) > 9 or not secret:
        return None
    char = db.session.get(Character, int(ident))
    if char is None or char.deleted_at or srd_manage.is_archived(char):
        return None
    stored = _sharing(char)
    if not stored.get("enabled") or not isinstance(stored.get("secret"), str):
        return None
    if not hmac.compare_digest(stored["secret"].encode(), secret.encode()):
        return None
    return char if sheet_link.srd_evaluation(char) is not None else None


def shared_view(char):
    """What anyone with the link sees: the numbers of the sheet, no notes, no owner, no ids."""
    data = load_creator_data()
    evaluation = sheet_link.srd_evaluation(char)
    state = ((char.character_data or {}).get("srd") or {}).get("state") or {}
    spells = []
    for class_key, picked in (state.get("spells") or {}).items():
        if not isinstance(picked, dict):
            continue
        for group, label in (("cantrips", "Zaubertrick"), ("prepared", "Vorbereitet")):
            for spell_id in picked.get(group) or []:
                spell = data["spells"].get(spell_id)
                if spell:
                    spells.append({"name": spell["name"], "level": spell["level"], "group": label})
    feat_names = {feat["id"]: feat["name"] for feat in data["feats"]}
    inventory = srd_inventory.inventory_state(char)
    cat = srd_inventory.catalog(data)
    items = [srd_inventory.item_view(row, cat) for row in srd_inventory.items_of(char)]
    return {
        "name": char.name, "species": char.race, "background": char.background, "level": char.level,
        "classes": [{"name": c["name"], "level": c["level"]} for c in evaluation["classes"]],
        "proficiencyBonus": evaluation["proficiencyBonus"],
        "abilities": evaluation["abilities"], "saves": evaluation["saves"],
        "skills": {key: {"name": v["name"], "proficiency": v["proficiency"], "bonus": v["bonus"]} for key, v in evaluation["skills"].items()},
        "hitPoints": {"current": char.hp_current, "max": evaluation["hitPoints"]["max"]},
        "armorClass": evaluation["armorClass"]["value"], "initiative": evaluation["initiative"],
        "speedMeters": evaluation["speedMeters"], "passivePerception": evaluation["passivePerception"],
        "spellcasting": {"classes": evaluation["spellcasting"]["classes"], "slots": evaluation["spellcasting"]["slots"]},
        "spells": spells, "feats": [feat_names.get(f, f) for f in evaluation["feats"]],
        "equipment": [{"name": i["name"], "quantity": i["quantity"], "equipped": i["equipped"]} for i in items],
        "coins": inventory["coins"],
    }


# --------------------------------------------------------------------------- handing out items

def search_items(kind, query):
    query = (query or "").strip().casefold()[:100]
    if kind == "gear":
        cat = srd_inventory.catalog()
        found = [e for e in cat.values() if not query or query in e["name"].casefold()]
        found.sort(key=lambda e: e["name"].casefold())
        return [{"id": e["id"], "name": e["name"], "kind": e["kind"], "summary": srd_inventory.cost_text(e["costCp"])} for e in found[:MAX_SEARCH]]
    if kind == "magic":
        from vtt.rules import _compendium

        found = [e for e in _compendium()["entities"] if e["type"] == "magic-item" and (not query or query in e["name"].casefold())]
        found.sort(key=lambda e: e["name"].casefold())
        return [{"id": e["id"], "name": e["name"], "kind": "magic", "summary": f"{e['detail']}"} for e in found[:MAX_SEARCH]]
    raise srd_inventory.InventoryError("invalid_kind", "kind muss „gear“ oder „magic“ sein.")


def _magic_text(entity):
    from vtt.rules import _PACKAGE, _load_json
    from vtt.rules_content.compendium import entry_excerpt

    document = _load_json(_PACKAGE / "documents" / f"{entity['documentId']}.json")
    parts = []
    for block in entry_excerpt(document, entity):
        if block["type"] == "paragraph" and not block["ruleId"].endswith(".untertitel"):
            parts.append(block["text"])
        elif block["type"] == "unordered-list":
            parts.append("\n".join(f"• {item}" if isinstance(item, str) else f"• {item.get('text', '')}" for item in block["items"]))
    text = "\n\n".join(parts)
    if len(text) > MAX_DESCRIPTION:
        text = text[:MAX_DESCRIPTION].rstrip() + f" … Vollständiger Text im Regelwerk: {entity['url']}"
    elif any(b["type"] in {"table", "stat-block"} for b in entry_excerpt(document, entity)):
        text += f"\n\nTabellen und Werte im Regelwerk: {entity['url']}"
    return text


def _magic_item(char, compendium_id, quantity, user_id):
    from vtt.rules import _compendium

    entity = next((e for e in _compendium()["entities"] if e["type"] == "magic-item" and e["id"] == compendium_id), None)
    if entity is None:
        raise srd_inventory.InventoryError("unknown_item", "Diesen magischen Gegenstand gibt es im Regelwerk nicht.", 404)
    quantity = srd_inventory._clean_quantity(quantity)
    if srd_inventory._count(char) >= srd_inventory.MAX_ITEMS:
        raise srd_inventory.InventoryError("inventory_full", f"Das Inventar fasst höchstens {srd_inventory.MAX_ITEMS} Einträge.")
    row = InventoryItem(
        character_id=char.id, name=entity["name"][:100], item_type="magic", quantity=quantity,
        weight_per_unit=0, description=_magic_text(entity), effects={},
    )
    srd_inventory._set_meta(
        row, itemId=None, kind="magic", equipped=False, compendiumId=entity["id"], rarity=entity["rarity"],
        attunement=bool(entity["attunement"]), source="SRD 5.2.1 (CC BY 4.0)",
    )
    db.session.add(row)
    return [row]


def hand_out(char, body, *, user_id):
    """The DM puts SRD gear, an SRD magic item or coins into a character's inventory (caller commits)."""
    if not isinstance(body, dict):
        raise srd_inventory.InventoryError("invalid_body", "JSON-Objekt erwartet.")
    label = None
    if "coins" in body:
        coins = srd_inventory.change_coins(char, {"delta": body["coins"]}) if body.get("coins") else None
        if coins is None:
            raise srd_inventory.InventoryError("invalid_coins", "Gib Münzen an.")
        label = "Münzen " + ", ".join(f"{v} {k}" for k, v in body["coins"].items())
        rows = []
    else:
        quantity = body.get("quantity", 1)
        if body.get("kind") == "magic":
            rows = _magic_item(char, body.get("itemId"), quantity, user_id)
        elif body.get("kind") == "gear":
            rows = srd_inventory.add_catalog_item(char, body.get("itemId"), quantity)
        else:
            raise srd_inventory.InventoryError("invalid_kind", "kind muss „gear“ oder „magic“ sein.")
        label = rows[0].name if rows else "Gegenstand"
        if len(rows) > 1:
            label += " und weitere"
        for row in rows:
            if row in db.session.new:
                srd_inventory._set_meta(row, handedOutBy=user_id, handedOutAt=utcnow().isoformat() + "Z")
    data = copy.deepcopy(char.character_data)
    _log(data["srd"], {"type": "handout", "by": user_id, "label": label[:120]})
    char.character_data = data
    flag_modified(char, "character_data")
    return rows


def take_back(char, row, *, user_id):
    """The DM removes an item they handed out; the player's own items are not theirs to remove."""
    if not srd_inventory._meta(row).get("handedOutBy"):
        raise srd_inventory.InventoryError("not_handed_out", "Nur ausgegebene Gegenstände kann die Spielleitung zurücknehmen.", 409)
    name = row.name
    srd_inventory.remove_item(char, row)
    data = copy.deepcopy(char.character_data)
    _log(data["srd"], {"type": "take-back", "by": user_id, "label": name[:120]})
    char.character_data = data
    flag_modified(char, "character_data")
