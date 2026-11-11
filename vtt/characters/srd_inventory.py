"""Inventory of SRD characters: catalog items, worn gear, coins, weight and weapon attacks.

Items are stored as `InventoryItem` rows (so loot handed over at the table shows up too);
the SRD part lives in `effects["srd"] = {itemId, kind, equipped}`. Coins and the starting
equipment bookkeeping live in `character_data["srdInventory"]`. Worn armor and shield are
written back to the character's rules state, so the armor class always comes from `evaluate`.
"""

import copy
import random
import secrets

from sqlalchemy.orm.attributes import flag_modified

from vtt.extensions import db
from vtt.models import InventoryItem
from vtt.rules_content.creator_rules import _weapon_allowed, evaluate, load_creator_data
from vtt.rules_content.species_profiles import rules_data_for_block

MAX_ITEMS = 150
MAX_QUANTITY = 9999
MAX_COINS = 10_000_000
COIN_ORDER = ("PM", "GM", "EM", "SM", "KM")
COIN_WEIGHT_KG = 0.01
DAMAGE_TYPES = {"slashing": "Hieb", "piercing": "Stich", "bludgeoning": "Wucht"}
SIZE_ORDER = ("Winzig", "Klein", "Mittelgroß", "Groß", "Riesig", "Gigantisch")
SIZE_FACTORS = {"Winzig": 3.75, "Klein": 7.5, "Mittelgroß": 7.5, "Groß": 15.0, "Riesig": 30.0, "Gigantisch": 60.0}
CHOICE_CATEGORIES = {
    "arcane-focus": ("Arkaner Fokus", "Arkaner Fokus"),
    "holy-symbol": ("Heiliges Symbol", "Heiliges Symbol"),
    "druidic-focus": ("Druidischer Fokus", "Druidischer Fokus"),
    "musical-instrument": ("Musikinstrument", "Musikinstrument"),
    "tool-choice": ("Handwerkszeug oder Musikinstrument", "Handwerkszeug"),
}
MUSIC_ITEM = "equipment.tools.tool-musikinstrument"


class InventoryError(Exception):
    def __init__(self, code, message, status=422):
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


# --------------------------------------------------------------------------- catalog

_catalog_cache: dict = {}


def catalog(data=None):
    data = data or load_creator_data()
    cached = _catalog_cache.get(data.get("packageDigest"))
    if cached is not None:
        return cached
    equipment = data["equipment"]
    out = {}
    for armor in equipment["armor"]:
        kind = "shield" if armor["category"] == "shield" else "armor"
        out[armor["id"]] = {"id": armor["id"], "name": armor["name"], "kind": kind, "category": armor["category"],
                            "weightKg": armor["weightKg"], "costCp": armor["costCp"], "raw": armor}
    for weapon in equipment["weapons"]:
        out[weapon["id"]] = {"id": weapon["id"], "name": weapon["name"], "kind": "weapon", "category": weapon["category"],
                             "weightKg": weapon["weightKg"], "costCp": weapon["costCp"], "raw": weapon}
    for item in equipment["items"]:
        out[item["id"]] = {"id": item["id"], "name": item["name"], "kind": item["kind"], "category": item["category"],
                           "weightKg": item["weightKg"], "costCp": item["costCp"], "raw": item}
    _catalog_cache[data.get("packageDigest")] = out
    return out


def _meters(value):
    text = f"{value:g}".replace(".", ",")
    return text


def cost_text(cost_cp):
    if not cost_cp:
        return None
    if cost_cp % 100 == 0:
        return f"{cost_cp // 100} GM"
    if cost_cp % 10 == 0:
        return f"{cost_cp // 10} SM"
    return f"{cost_cp} KM"


def weapon_properties(weapon):
    parts = []
    for prop in weapon["properties"]:
        text = prop["name"]
        if prop.get("range"):
            text += f" ({_meters(prop['range']['normal'])}/{_meters(prop['range']['long'])} m)"
        elif prop.get("versatile"):
            versatile = prop["versatile"]
            text += f" ({versatile['dice']}W{versatile['sides']})"
        parts.append(text)
    return parts


def damage_text(damage, modifier=0):
    parts = []
    if damage["dice"]:
        parts.append(f"{damage['dice']}d{damage['sides']}")
    flat = (damage.get("flat") or 0) + modifier
    if flat or not parts:
        parts.append(f"{flat:+d}" if parts else str(flat))
    return "".join(parts)


def summary(entry):
    if entry is None:
        return ""
    raw = entry["raw"]
    if entry["kind"] == "weapon":
        damage = raw["damage"]
        bits = [f"{damage['dice']}W{damage['sides']} {DAMAGE_TYPES.get(damage['type'], damage['type'])}",
                f"Meisterschaft {raw['mastery']}"] + weapon_properties(raw)
        return " · ".join(bit for bit in bits if bit)
    if entry["kind"] == "shield":
        return f"+{raw['base']} RK"
    if entry["kind"] == "armor":
        dex = {"full": " + GES", "capped": f" + GES (max. {raw['dexCap']})", "none": ""}[raw["dex"]]
        extras = []
        if raw["strengthRequirement"]:
            extras.append(f"Stärke {raw['strengthRequirement']}")
        if raw["stealthDisadvantage"]:
            extras.append("Nachteil auf Heimlichkeit")
        return " · ".join([f"RK {raw['base']}{dex}"] + extras)
    return entry["category"]


# --------------------------------------------------------------------------- stored state

def srd_block(char):
    block = (char.character_data or {}).get("srd")
    return block if isinstance(block, dict) else None


def inventory_state(char):
    stored = (char.character_data or {}).get("srdInventory")
    stored = stored if isinstance(stored, dict) else {}
    coins = stored.get("coins") if isinstance(stored.get("coins"), dict) else {}
    return {
        "coins": {code: max(0, int(coins.get(code) or 0)) for code in COIN_ORDER},
        "seeded": bool(stored.get("seeded")),
        "pending": [p for p in (stored.get("pending") or []) if isinstance(p, dict)],
    }


def _write(char, mutate, *, recompute=False):
    """Apply `mutate(character_data)` to a copy of the character data and store it (caller commits)."""
    data = copy.deepcopy(char.character_data or {})
    mutate(data)
    if recompute:
        block = data["srd"]
        evaluation = evaluate(rules_data_for_block(block), block.get("state") or {})
        block["derived"] = evaluation
        char.ac = evaluation["armorClass"]["value"]
    char.character_data = data
    flag_modified(char, "character_data")


def _store_inventory(char, inv):
    def apply(data):
        data["srdInventory"] = {"coins": inv["coins"], "seeded": inv["seeded"], "pending": inv["pending"]}
    _write(char, apply)


def items_of(char):
    return InventoryItem.query.filter_by(character_id=char.id).order_by(InventoryItem.id).all()


def _meta(item):
    meta = (item.effects or {}).get("srd")
    return meta if isinstance(meta, dict) else {}


def _set_meta(item, **changes):
    effects = dict(item.effects or {})
    meta = dict(effects.get("srd") or {})
    meta.update(changes)
    effects["srd"] = meta
    item.effects = effects


def item_view(item, cat):
    meta = _meta(item)
    entry = cat.get(meta.get("itemId")) if meta.get("itemId") else None
    unit = float(item.weight_per_unit or 0)
    return {
        "id": item.id,
        "itemId": meta.get("itemId"),
        "name": item.name,
        "kind": meta.get("kind") or "custom",
        "quantity": item.quantity or 0,
        "weightKg": unit,
        "totalKg": round(unit * (item.quantity or 0), 3),
        "cost": item.cost,
        "equipped": bool(meta.get("equipped")),
        "summary": summary(entry),
        "description": item.description,
        "custom": entry is None,
        "handedOut": bool(meta.get("handedOutBy")),
        "rarity": meta.get("rarity"),
        "attunement": bool(meta.get("attunement")),
        "source": meta.get("source"),
    }


# --------------------------------------------------------------------------- mutations

def _clean_quantity(value):
    if type(value) is not int or not 1 <= value <= MAX_QUANTITY:
        raise InventoryError("invalid_quantity", f"Die Anzahl muss zwischen 1 und {MAX_QUANTITY} liegen.")
    return value


def _count(char):
    return InventoryItem.query.filter_by(character_id=char.id).count()


def add_catalog_item(char, item_id, quantity=1, *, name=None, expand=True):
    """Put a catalog item (or the contents of a pack) into the inventory; returns the touched rows."""
    data = load_creator_data()
    cat = catalog(data)
    entry = cat.get(item_id)
    if entry is None:
        raise InventoryError("unknown_item", "Diesen Gegenstand gibt es im Regelwerk nicht.")
    quantity = _clean_quantity(quantity)
    pack = data["equipment"]["packs"].get(item_id) if expand else None
    if pack:
        rows = []
        for content in pack["contents"]:
            if content.get("kind") == "item":
                rows.extend(add_catalog_item(char, content["itemId"], content["quantity"] * quantity, expand=False))
        return rows
    label = name or entry["name"]
    for row in items_of(char):
        if _meta(row).get("itemId") == item_id and row.name == label:
            if (row.quantity or 0) + quantity > MAX_QUANTITY:
                raise InventoryError("invalid_quantity", f"Mehr als {MAX_QUANTITY} Stück sind nicht möglich.")
            row.quantity = (row.quantity or 0) + quantity
            return [row]
    if _count(char) >= MAX_ITEMS:
        raise InventoryError("inventory_full", f"Das Inventar fasst höchstens {MAX_ITEMS} Einträge.")
    row = InventoryItem(
        character_id=char.id, name=label[:100], item_type=entry["kind"], quantity=quantity,
        weight_per_unit=entry["weightKg"], cost=cost_text(entry["costCp"]), effects={},
    )
    _set_meta(row, itemId=item_id, kind=entry["kind"], equipped=False)
    db.session.add(row)
    return [row]


def add_custom_item(char, payload):
    name = payload.get("name")
    if not isinstance(name, str) or not name.strip():
        raise InventoryError("invalid_name", "Gib dem Gegenstand einen Namen.")
    weight = payload.get("weightKg", 0)
    if isinstance(weight, bool) or not isinstance(weight, (int, float)) or not 0 <= weight <= 1000:
        raise InventoryError("invalid_weight", "Das Gewicht muss zwischen 0 und 1000 kg liegen.")
    description = payload.get("description")
    if description is not None and (not isinstance(description, str) or len(description) > 1000):
        raise InventoryError("invalid_description", "Die Beschreibung ist zu lang (höchstens 1000 Zeichen).")
    quantity = _clean_quantity(payload.get("quantity", 1))
    if _count(char) >= MAX_ITEMS:
        raise InventoryError("inventory_full", f"Das Inventar fasst höchstens {MAX_ITEMS} Einträge.")
    row = InventoryItem(
        character_id=char.id, name=name.strip()[:100], item_type="custom", quantity=quantity,
        weight_per_unit=float(weight), description=(description or None), effects={},
    )
    _set_meta(row, itemId=None, kind="custom", equipped=False)
    db.session.add(row)
    return row


def _sync_worn(char, items):
    """Write the worn armor and shield of the inventory into the rules state and recompute (caller commits)."""
    armor = next((_meta(i).get("itemId") for i in items if _meta(i).get("kind") == "armor" and _meta(i).get("equipped")), None)
    shield = any(_meta(i).get("kind") == "shield" and _meta(i).get("equipped") for i in items)

    def apply(data):
        equipment = data["srd"].setdefault("state", {}).setdefault("equipment", {})
        if armor:
            equipment["armor"] = armor
        else:
            equipment.pop("armor", None)
        if shield:
            equipment["shield"] = True
        else:
            equipment.pop("shield", None)

    _write(char, apply, recompute=True)


def set_equipped(char, row, equipped):
    meta = _meta(row)
    kind = meta.get("kind")
    if kind not in {"armor", "shield", "weapon"}:
        raise InventoryError("not_wearable", "Dieser Gegenstand kann nicht angelegt werden.")
    items = items_of(char)
    if equipped and kind in {"armor", "shield"}:
        for other in items:
            if other.id != row.id and _meta(other).get("kind") == kind and _meta(other).get("equipped"):
                _set_meta(other, equipped=False)
    _set_meta(row, equipped=bool(equipped))
    if kind in {"armor", "shield"}:
        _sync_worn(char, items)


def remove_item(char, row):
    meta = _meta(row)
    was_worn = meta.get("kind") in {"armor", "shield"} and meta.get("equipped")
    db.session.delete(row)
    db.session.flush()
    if was_worn:
        _sync_worn(char, items_of(char))


def change_coins(char, payload):
    inv = inventory_state(char)
    coins = dict(inv["coins"])
    absolute, delta = payload.get("coins"), payload.get("delta")
    if (absolute is None) == (delta is None):
        raise InventoryError("invalid_coins", "Sende entweder „coins“ (neue Stände) oder „delta“ (Änderung).")
    source = absolute if absolute is not None else delta
    if not isinstance(source, dict) or not source or set(source) - set(COIN_ORDER):
        raise InventoryError("invalid_coins", "Erlaubte Münzen: " + ", ".join(COIN_ORDER) + ".")
    for code, value in source.items():
        if type(value) is not int:
            raise InventoryError("invalid_coins", "Münzmengen sind ganze Zahlen.")
        if absolute is not None and value < 0:
            raise InventoryError("invalid_coins", "Münzmengen können nicht negativ sein.")
        new = value if absolute is not None else coins[code] + value
        if new < 0:
            raise InventoryError("not_enough_coins", f"Du hast nicht genug {code}.")
        if new > MAX_COINS:
            raise InventoryError("invalid_coins", "Diese Menge ist zu groß.")
        coins[code] = new
    inv["coins"] = coins
    _store_inventory(char, inv)
    return coins


def resolve_pending(char, pending_id):
    inv = inventory_state(char)
    inv["pending"] = [p for p in inv["pending"] if p.get("id") != pending_id]
    _store_inventory(char, inv)


def pending_options(pending, data=None):
    data = data or load_creator_data()
    cat = catalog(data)
    mapping = CHOICE_CATEGORIES.get(pending.get("category"))
    if mapping is None:
        return []
    wanted = {mapping[1]}
    if pending["category"] == "tool-choice":
        wanted.add("Musikinstrument")
    options = [e for e in cat.values() if e["category"] in wanted or (e["id"] == MUSIC_ITEM and "Musikinstrument" in wanted)]
    return [{"itemId": e["id"], "name": e["name"]} for e in options]


def seed_starting_equipment(char, class_package=None, background_package=None):
    """Move the chosen starting packages into the inventory once; returns the notes for the player."""
    block = srd_block(char)
    data = load_creator_data()
    cat = catalog(data)
    inv = inventory_state(char)
    if inv["seeded"]:
        raise InventoryError("already_seeded", "Die Ausgangsausrüstung wurde bereits übernommen.", 409)
    state = block.get("state") or {}
    evaluation = evaluate(data, state)
    equipment = state.get("equipment") if isinstance(state.get("equipment"), dict) else {}
    first = (evaluation.get("classes") or [{}])[0].get("classKey")
    cls = next((c for c in data["classes"] if c["classKey"] == first), None)
    background = next((b for b in data["backgrounds"] if b["id"] == (state.get("background") or {}).get("id")), None)
    chosen = {
        "classPackage": class_package or equipment.get("classPackage"),
        "backgroundPackage": background_package or equipment.get("backgroundPackage"),
    }
    entries = []
    for label, source, key in (("Klasse", cls, "classPackage"), ("Hintergrund", background, "backgroundPackage")):
        packages = (source or {}).get("startingEquipment") or {}
        if not packages:
            continue
        if chosen[key] not in packages:
            raise InventoryError("package_missing", f"Wähle ein Ausrüstungspaket für {label} ({'/'.join(sorted(packages))}).")
        entries.extend(packages[chosen[key]])

    notes, pending = [], list(inv["pending"])
    coins = dict(inv["coins"])
    for entry in entries:
        kind = entry.get("kind")
        if kind == "item":
            variant = entry.get("variant")
            base = cat.get(entry["itemId"])
            name = f"{base['name']} ({variant})" if variant and base else None
            add_catalog_item(char, entry["itemId"], entry["quantity"], name=name)
        elif kind == "coins":
            coins[entry["coin"]] = coins.get(entry["coin"], 0) + int(entry["amount"])
        elif kind == "choice":
            pending.append({"id": "p" + secrets.token_hex(3), "category": entry["category"],
                            "variant": entry.get("variant"), "quantity": entry.get("quantity", 1)})
        elif kind == "special" and entry.get("special") == "spellbook":
            row = add_custom_item(char, {"name": "Zauberbuch", "weightKg": 0, "quantity": 1,
                                         "description": "Dein Zauberbuch mit den Zaubern, die du in ihm niedergeschrieben hast."})
            _set_meta(row, kind="custom")
    level = evaluation.get("level") or 1
    row = next((r for r in data["startingEquipmentByLevel"] if r["fromLevel"] <= level <= r["toLevel"]), None)
    if row and level > 1:
        if row["baseGold"]:
            coins["GM"] += int(row["baseGold"])
        notes.append(f"Stufe {level}: {row['baseGold']} GM zusätzlich übernommen. Magische Gegenstände ({row['magicItems']}) "
                     "und gewürfeltes Gold vergibt die Spielleitung.")
    db.session.flush()
    inv.update(coins=coins, seeded=True, pending=pending)

    def apply(data_):
        data_["srdInventory"] = {"coins": inv["coins"], "seeded": True, "pending": inv["pending"]}
        equipment_ = data_["srd"].setdefault("state", {}).setdefault("equipment", {})
        equipment_["classPackage"] = chosen["classPackage"] or equipment_.get("classPackage")
        equipment_["backgroundPackage"] = chosen["backgroundPackage"] or equipment_.get("backgroundPackage")
        if not equipment_["classPackage"]:
            equipment_.pop("classPackage")
        if not equipment_["backgroundPackage"]:
            equipment_.pop("backgroundPackage")

    _write(char, apply)
    rows = items_of(char)
    armor_rows = [r for r in rows if _meta(r).get("kind") == "armor"]
    shield_rows = [r for r in rows if _meta(r).get("kind") == "shield"]
    wanted = next((r for r in armor_rows if _meta(r).get("itemId") == equipment.get("armor")), None)
    target = wanted or (armor_rows[0] if armor_rows else None)
    if target:
        _set_meta(target, equipped=True)
    if shield_rows:
        _set_meta(shield_rows[0], equipped=True)
    _sync_worn(char, rows)
    return notes


# --------------------------------------------------------------------------- carrying capacity

def carrying(char, evaluation, items, coins):
    data = load_creator_data()
    state = (srd_block(char) or {}).get("state") or {}
    species = next((s for s in data["species"] if s["id"] == (state.get("species") or {}).get("id")), None)
    size = "Mittelgroß"
    if species:
        chosen = ((state.get("species") or {}).get("choices") or {}).get("size")
        size = chosen if chosen in species["sizes"] else species["sizes"][0]
        if "Kräftiger Körperbau" in species.get("traits", []):
            size = SIZE_ORDER[min(SIZE_ORDER.index(size) + 1, len(SIZE_ORDER) - 1)]
    strength = evaluation["abilities"]["str"]["score"]
    capacity = strength * SIZE_FACTORS[size]
    items_kg = sum((i.weight_per_unit or 0) * (i.quantity or 0) for i in items)
    coins_kg = sum(coins.values()) * COIN_WEIGHT_KG
    carried = items_kg + coins_kg
    return {
        "size": size, "itemsKg": round(items_kg, 2), "coinsKg": round(coins_kg, 2), "carriedKg": round(carried, 2),
        "capacityKg": round(capacity, 2), "liftKg": round(capacity * 2, 2), "over": carried > capacity,
    }


# --------------------------------------------------------------------------- weapons

def _class_entries(evaluation, data):
    by_key = {c["classKey"]: c for c in data["classes"]}
    return [by_key[c["classKey"]] for c in evaluation.get("classes", []) if c["classKey"] in by_key]


def weapon_proficient(entries, weapon):
    if not entries:
        return False
    if _weapon_allowed(entries[0], weapon):
        return True
    for entry in entries[1:]:
        for grant in (entry.get("multiclassGrants") or {}).get("weapons", []):
            if grant["category"] != weapon["category"]:
                continue
            required = grant.get("requiresProperty")
            if not required or any(p["name"] in required for p in weapon["properties"]):
                return True
    return False


def attack_ability(weapon, abilities):
    names = {p["name"] for p in weapon["properties"]}
    if "Finesse" in names:
        return "str" if abilities["str"]["modifier"] >= abilities["dex"]["modifier"] else "dex"
    return "dex" if weapon["kind"] == "ranged" else "str"


def _masteries(state, weapons):
    picked = set()
    for per_class in (state.get("featureChoices") or {}).values():
        if isinstance(per_class, dict):
            for value in per_class.values():
                if isinstance(value, list):
                    picked.update(v for v in value if isinstance(v, str) and v in weapons)
    return picked


def attack_rows(char, evaluation, items):
    """Attack and damage values for every weapon in the inventory plus the unarmed strike."""
    data = load_creator_data()
    cat = catalog(data)
    state = (srd_block(char) or {}).get("state") or {}
    abilities, pb = evaluation["abilities"], evaluation["proficiencyBonus"]
    entries = _class_entries(evaluation, data)
    mastered = _masteries(state, {e["id"] for e in cat.values() if e["kind"] == "weapon"})
    strength = abilities["str"]["modifier"]
    rows = [{
        "key": "unarmed", "inventoryId": None, "name": "Waffenloser Schlag", "equipped": False, "proficient": True,
        "attackBonus": strength + pb, "damage": str(max(0, 1 + strength)), "damageType": "Wucht", "ability": "str",
        "versatile": None, "mastery": None, "masteryActive": False, "properties": [], "summary": "1 + Stärkemodifikator Wucht",
    }]
    for item in items:
        meta = _meta(item)
        entry = cat.get(meta.get("itemId")) if meta.get("kind") == "weapon" else None
        if entry is None:
            continue
        weapon = entry["raw"]
        ability = attack_ability(weapon, abilities)
        modifier = abilities[ability]["modifier"]
        proficient = weapon_proficient(entries, weapon)
        versatile = next((p["versatile"] for p in weapon["properties"] if p.get("versatile")), None)
        rows.append({
            "key": str(item.id), "inventoryId": item.id, "name": item.name, "equipped": bool(meta.get("equipped")),
            "proficient": proficient, "attackBonus": modifier + (pb if proficient else 0),
            "damage": damage_text(weapon["damage"], modifier),
            "damageType": DAMAGE_TYPES.get(weapon["damage"]["type"], weapon["damage"]["type"]),
            "ability": ability,
            "versatile": damage_text({"dice": versatile["dice"], "sides": versatile["sides"], "flat": 0}, modifier) if versatile else None,
            "mastery": weapon["mastery"], "masteryActive": weapon["id"] in mastered,
            "properties": weapon_properties(weapon), "summary": summary(entry),
        })
    for row in rows:
        modifier = abilities[row['ability']]['modifier']
        row['provenance'] = {
            'attack': {'label':'Angriffsbonus','total':row['attackBonus'],'stacking':'add',
                'contributions':[{'label':row['ability'].upper(),'value':modifier,'source':{'id':'modifier.'+row['ability']}},
                    {'label':'Waffenübung','value':pb if row['proficient'] else 0,'source':{'id':'proficiencyBonus','classes':[entry['classKey'] for entry in entries]}}]},
            'damage': {'label':'Schaden','formula':row['damage'],'stacking':'weapon_dice_plus_ability',
                'contributions':[{'label':'Waffe','value':row['summary'],'source':{'id':'inventory.'+row['key']}},
                    {'label':row['ability'].upper(),'value':modifier,'source':{'id':'modifier.'+row['ability']}}]},
        }
    return rows


def weapon_roll_spec(char, evaluation, kind, key, *, critical=False, two_handed=False):
    """{label, modifier} for an attack, {label, damage: {...}} for damage; None if the weapon is not in the inventory."""
    items = items_of(char)
    row = next((r for r in attack_rows(char, evaluation, items) if r["key"] == key), None)
    if row is None:
        return None
    if kind == "weapon_attack":
        return {"label": f"Angriff: {row['name']}", "modifier": int(row["attackBonus"])}
    item = next((i for i in items if i.id == row["inventoryId"]), None)
    entry = catalog().get(_meta(item).get("itemId")) if item else None
    modifier = evaluation["abilities"][row["ability"]]["modifier"]
    if entry is None:
        damage = {"dice": 0, "sides": 0, "flat": 1}
    else:
        weapon = entry["raw"]
        damage = dict(weapon["damage"])
        versatile = next((p["versatile"] for p in weapon["properties"] if p.get("versatile")), None)
        if two_handed:
            if not versatile:
                return None
            damage.update(dice=versatile["dice"], sides=versatile["sides"])
    dice = damage["dice"] * (2 if critical else 1)
    flat = (damage.get("flat") or 0) + modifier
    text = f"{dice}d{damage['sides']}" + (f"{flat:+d}" if flat else "") if dice else str(flat)
    suffix = " (Kritisch)" if critical else ""
    return {
        "label": f"Schaden: {row['name']}{' zweihändig' if two_handed else ''} ({row['damageType']}){suffix}",
        "damage": {"dice": dice, "sides": damage["sides"], "modifier": flat},
        "dice": text,
    }


def roll_damage(damage, rng=None):
    rng = rng or random.SystemRandom()
    rolls = [rng.randint(1, damage["sides"]) for _ in range(damage["dice"])]
    return {"rolls": rolls, "modifier": damage["modifier"], "total": max(0, sum(rolls) + damage["modifier"]), "mode": "normal"}


# --------------------------------------------------------------------------- payload

def inventory_payload(char, evaluation):
    data = load_creator_data()
    cat = catalog(data)
    rows = items_of(char)
    inv = inventory_state(char)
    state = (srd_block(char) or {}).get("state") or {}
    worn = state.get("equipment") if isinstance(state.get("equipment"), dict) else {}
    armor = cat.get(worn.get("armor"))
    first = (evaluation.get("classes") or [{}])[0].get("classKey")
    cls = next((c for c in data["classes"] if c["classKey"] == first), {})
    background = next((b for b in data["backgrounds"] if b["id"] == (state.get("background") or {}).get("id")), {})
    def package_options(source):
        return [{"id": key, "label": f"{key} · {'Gold' if all(e.get('kind') == 'coins' for e in entries) else 'Ausrüstung'}"}
                for key, entries in sorted(source.get("startingEquipment", {}).items())]
    return {
        "items": [item_view(row, cat) for row in rows],
        "coins": inv["coins"],
        "coinNames": {code: data["equipment"]["coins"][code]["name"] for code in COIN_ORDER},
        "seeded": inv["seeded"],
        "pending": [{**p, "options": pending_options(p, data)} for p in inv["pending"]],
        "weight": carrying(char, evaluation, rows, inv["coins"]),
        "armorClass": evaluation["armorClass"],
        "worn": {"armor": armor["name"] if armor else None, "armorItemId": worn.get("armor"), "shield": bool(worn.get("shield"))},
        "attacks": attack_rows(char, evaluation, rows),
        "findings": [f for f in evaluation.get("findings", []) if str(f.get("path") or "").startswith("equipment.")],
        "packages": {"class": worn.get("classPackage"), "background": worn.get("backgroundPackage")},
        "packageOptions": {"class": package_options(cls), "background": package_options(background)},
    }
