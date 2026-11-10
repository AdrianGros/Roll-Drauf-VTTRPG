"""Export and import of finished SRD characters as a versioned JSON file.

The file carries what the owner built (rules state, hit points, experience, inventory, companions) and nothing
that ties it to an account: no ids, campaign, sharing secret or history. Import re-runs the rules on the state,
so a hand-edited or outdated file can never produce a character the creator would not have allowed.
"""

import copy

from vtt.characters import species_catalog, srd_inventory, srd_manage
from vtt.extensions import db
from vtt.rules_content import species_profiles
from vtt.characters.srd_progression import MODES, ProgressionError, _log
from vtt.models import Character, InventoryItem
from vtt.rules_content.creator_drafts import character_values, finalize_blockers, sanitize_state
from vtt.rules_content.creator_rules import evaluate, load_creator_data
from vtt.rules_content.creator_sources import pin_sources
from vtt.utils.time import utcnow

FORMAT = "roll-drauf-srd-character"
VERSION = 1
MAX_BYTES = 400_000
MAX_XP = 1_000_000
MAX_TEXT = 4000


def _srd_block(char):
    block = (char.character_data or {}).get("srd") if isinstance(char.character_data, dict) else None
    if not isinstance(block, dict):
        raise ProgressionError("not_srd", "Kein SRD-Charakter.")
    return block


def export_document(char):
    block = _srd_block(char)
    data = char.character_data
    inv = srd_inventory.inventory_state(char)
    items = []
    for row in srd_inventory.items_of(char):
        meta = srd_inventory._meta(row)
        item = {
            "name": row.name, "quantity": row.quantity or 1, "weightKg": float(row.weight_per_unit or 0),
            "cost": row.cost, "description": row.description, "itemId": meta.get("itemId"),
            "kind": meta.get("kind") or "custom", "equipped": bool(meta.get("equipped")),
        }
        for key in ("rarity", "attunement", "source", "compendiumId"):
            if meta.get(key) is not None:
                item[key] = meta[key]
        items.append(item)
    progression = block.get("progression") if isinstance(block.get("progression"), dict) else {}
    companions = [{k: v for k, v in c.items() if k != "id"} for c in srd_manage.companions(char)]
    pin = species_profiles.pinned(block)
    extra = {"speciesPin": {"revisionId": pin["revisionId"], "digest": pin.get("digest"), "name": pin["profile"]["name"]}} if pin else {}
    return {
        **extra,
        "format": FORMAT, "version": VERSION, "ruleset": load_creator_data()["rulesetId"],
        "exportedAt": utcnow().isoformat() + "Z",
        "sources": block.get("sources"),
        "character": {"name": char.name, "hpCurrent": char.hp_current, "xp": char.xp},
        "state": copy.deepcopy(block.get("state") or {}),
        "progression": {"mode": progression.get("mode", "xp"), "milestoneTarget": progression.get("milestoneTarget")},
        "theme": srd_manage.theme_of(char),
        "inventory": {"coins": inv["coins"], "seeded": inv["seeded"], "items": items},
        "companions": companions,
    }


def file_name(char):
    safe = "".join(c if c.isalnum() else "-" for c in (char.name or "charakter")).strip("-").lower() or "charakter"
    return f"{safe[:40]}.rollcharakter.json"


def _bad(message, **extra):
    return ProgressionError("import_invalid", message, 422, **extra)


def _text(value, limit, field, *, required=False):
    if value is None and not required:
        return None
    if not isinstance(value, str) or len(value) > limit or (required and not value.strip()):
        raise _bad(f"Inventar: „{field}“ fehlt oder ist zu lang (höchstens {limit} Zeichen).")
    return value


def _clean_items(raw, cat):
    if not isinstance(raw, list) or len(raw) > srd_inventory.MAX_ITEMS:
        raise _bad(f"Das Inventar muss eine Liste mit höchstens {srd_inventory.MAX_ITEMS} Einträgen sein.")
    out = []
    for index, entry in enumerate(raw):
        if not isinstance(entry, dict):
            raise _bad(f"Gegenstand {index + 1}: Objekt erwartet.")
        quantity = entry.get("quantity", 1)
        if type(quantity) is not int or not 1 <= quantity <= srd_inventory.MAX_QUANTITY:
            raise _bad(f"Gegenstand {index + 1}: ungültige Anzahl.")
        weight = entry.get("weightKg", 0)
        if isinstance(weight, bool) or not isinstance(weight, (int, float)) or not 0 <= weight <= 1000:
            raise _bad(f"Gegenstand {index + 1}: ungültiges Gewicht.")
        item_id = entry.get("itemId")
        if item_id is not None and not isinstance(item_id, str):
            raise _bad(f"Gegenstand {index + 1}: ungültige Kennung.")
        clean = {
            "name": _text(entry.get("name"), 100, "name", required=True).strip(), "quantity": quantity, "weightKg": float(weight),
            "cost": _text(entry.get("cost"), 50, "cost"), "description": _text(entry.get("description"), MAX_TEXT, "description"),
            "itemId": item_id if item_id in cat else None, "equipped": entry.get("equipped") is True,
            "kind": "magic" if entry.get("kind") == "magic" else "custom",
            "rarity": _text(entry.get("rarity"), 40, "rarity"), "attunement": entry.get("attunement") is True,
            "source": _text(entry.get("source"), 80, "source"), "compendiumId": _text(entry.get("compendiumId"), 100, "compendiumId"),
        }
        out.append(clean)
    return out


def _clean_coins(raw):
    if not isinstance(raw, dict):
        raise _bad("Münzen: Objekt erwartet.")
    coins = {}
    for code in srd_inventory.COIN_ORDER:
        value = raw.get(code, 0)
        if type(value) is not int or not 0 <= value <= srd_inventory.MAX_COINS:
            raise _bad(f"Münzen: „{code}“ muss eine ganze Zahl von 0 bis {srd_inventory.MAX_COINS} sein.")
        coins[code] = value
    return coins


def _species_for_import(doc, state, data, user_id):
    """(rules data, pin or None). A homebrew Species is re-pinned from this server's published revision, never
    from the file, and only if the importing user may choose exactly that revision; otherwise nothing is written."""
    species = state.get("species") if isinstance(state.get("species"), dict) else {}
    if not species_profiles.is_homebrew_species(species.get("id")):
        return data, None
    named = doc.get("speciesPin") if isinstance(doc.get("speciesPin"), dict) else {}
    resolved, row, problems = species_catalog.resolve(user_id, state)
    if problems or row is None or named.get("revisionId") != row.id or named.get("digest") != row.profile_digest:
        name = named.get("name") if isinstance(named.get("name"), str) else "Homebrew-Spezies"
        raise _bad(f"Die Datei nutzt die Homebrew-Spezies „{name[:100]}“. Sie ist hier nicht in genau dieser Fassung für dich "
                   "veröffentlicht, darum wird nichts importiert.")
    return resolved, species_catalog.pin_for(row)


def import_character(doc, *, user_id):
    """(Character, extras) built from an export file; the caller adds the character, flushes and calls `finish_import`."""
    if not isinstance(doc, dict) or doc.get("format") != FORMAT:
        raise _bad("Das ist keine Charakterdatei aus dem Regelwerk-Ersteller.")
    if doc.get("version") != VERSION:
        raise _bad("Diese Dateiversion wird nicht unterstützt.")
    data = load_creator_data()
    if doc.get("ruleset") != data["rulesetId"]:
        raise _bad("Die Datei gehört zu einem anderen Regelwerk.")
    state, problems = sanitize_state(copy.deepcopy(doc.get("state")) if isinstance(doc.get("state"), dict) else {}, data)
    if problems:
        raise _bad("Der Charakterzustand in der Datei ist ungültig.", problems=problems)
    data, pin = _species_for_import(doc, state, data, user_id)
    evaluation = evaluate(data, state)
    blockers = finalize_blockers(evaluation, state)
    if blockers:
        raise _bad("Die Datei beschreibt keinen regelkonformen, vollständigen Charakter.", blockers=blockers)
    cat = srd_inventory.catalog(data)
    inventory = doc.get("inventory") if isinstance(doc.get("inventory"), dict) else {}
    items = _clean_items(inventory.get("items", []), cat)
    coins = _clean_coins(inventory.get("coins", {}))
    companions = doc.get("companions", [])
    if not isinstance(companions, list):
        raise _bad("Begleiter müssen eine Liste sein.")
    progression = doc.get("progression") if isinstance(doc.get("progression"), dict) else {}
    mode = progression.get("mode", "xp")
    target = progression.get("milestoneTarget")
    if mode not in MODES or (target is not None and (type(target) is not int or not 1 <= target <= 20)):
        raise _bad("Fortschritt: ungültiger Modus oder ungültige Zielstufe.")
    saved = doc.get("character") if isinstance(doc.get("character"), dict) else {}
    values = character_values(data, state, evaluation, draft_id=None, finalized_at=utcnow().isoformat() + "Z")
    values["character_data"]["srd"]["sources"] = pin_sources(data, state.get("sources"))
    xp, hp = saved.get("xp"), saved.get("hpCurrent")
    if type(xp) is int:
        values["xp"] = max(values["xp"], min(xp, MAX_XP))
    if type(hp) is int:
        values["hp_current"] = max(0, min(hp, values["hp_max"]))
    block = values["character_data"]["srd"]
    if pin:
        block["speciesPin"] = pin
    block["progression"] = {"mode": mode, "milestoneTarget": target}
    _log(block, {"type": "import", "by": user_id})
    if doc.get("theme") in srd_manage.THEME_IDS:
        values["character_data"]["srdTheme"] = doc["theme"]
    char = Character(user_id=user_id, campaign_id=None, mana_max=0, mana_current=0, **values)
    extras = {"items": items, "coins": coins, "seeded": inventory.get("seeded") is True, "companions": companions}
    return char, extras


def finish_import(char, extras, *, user_id):
    """Inventory, coins and companions once the character has an id (caller commits)."""
    cat = srd_inventory.catalog()

    for item in extras["items"]:
        entry = cat.get(item["itemId"]) if item["itemId"] else None
        row = InventoryItem(
            character_id=char.id, name=item["name"][:100], item_type=entry["kind"] if entry else item["kind"], quantity=item["quantity"],
            weight_per_unit=entry["weightKg"] if entry else item["weightKg"],
            cost=srd_inventory.cost_text(entry["costCp"]) if entry else item["cost"],
            description=None if entry else item["description"], effects={},
        )
        meta = {"itemId": item["itemId"], "kind": entry["kind"] if entry else item["kind"], "equipped": item["equipped"]}
        if not entry and item["kind"] == "magic":
            meta.update({k: item[k] for k in ("rarity", "attunement", "source", "compendiumId") if item[k] not in (None, False)})
        srd_inventory._set_meta(row, **meta)
        db.session.add(row)
    srd_inventory._store_inventory(char, {"coins": extras["coins"], "seeded": extras["seeded"], "pending": []})
    if extras["companions"]:
        srd_manage.set_companions(char, {"companions": extras["companions"]}, user_id=user_id)
