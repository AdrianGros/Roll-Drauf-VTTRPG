"""Sheet rolls a person can put on the table's hotbar (Charakter-Makroleiste)."""
from vtt.characters import sheet_link, srd_inventory
from vtt.extensions import db
from vtt.models.table_macro_bar import MAX_MACRO_SLOTS, TableMacroBar


class MacroError(Exception):
    def __init__(self, code, message, status=400):
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


def _slot_id(kind, key):
    return f"{kind}:{key or ''}"


def macro_options(char):
    """Every roll the sheet offers for this SRD character, grouped for the editor; None if it is not SRD."""
    evaluation = sheet_link.srd_evaluation(char)
    if evaluation is None:
        return None
    options = []

    def add(group, kind, key, spec):
        if spec:
            options.append({"kind": kind, "key": key, "label": spec["label"], "group": group})

    add("Kampf", "initiative", None, sheet_link.roll_spec(evaluation, "initiative", None))
    for row in srd_inventory.attack_rows(char, evaluation, srd_inventory.items_of(char)):
        for kind in ("weapon_attack", "weapon_damage"):
            add("Kampf", kind, row["key"], srd_inventory.weapon_roll_spec(char, evaluation, kind, row["key"]))
    for key in ((evaluation.get("spellcasting") or {}).get("classes") or {}):
        add("Kampf", "spell_attack", key, sheet_link.roll_spec(evaluation, "spell_attack", key))
    add("Kampf", "death_save", None, sheet_link.roll_spec(evaluation, "death_save", None))
    for key in sheet_link.ABILITY_NAMES:
        add("Proben", "ability", key, sheet_link.roll_spec(evaluation, "ability", key))
    for key in sheet_link.ABILITY_NAMES:
        add("Rettungswürfe", "save", key, sheet_link.roll_spec(evaluation, "save", key))
    skills = evaluation.get("skills") or {}
    for key in sorted(skills, key=lambda name: str(skills[name].get("name", name))):
        add("Fertigkeiten", "skill", key, sheet_link.roll_spec(evaluation, "skill", key))
    return options


def bar_view(user, char):
    """This person's slots for the character (labels from the current sheet) plus every option."""
    options = macro_options(char)
    if options is None:
        return {"characterId": char.id, "slots": [], "options": [], "limit": MAX_MACRO_SLOTS, "reason": "not_srd"}
    by_id = {_slot_id(option["kind"], option["key"]): option for option in options}
    row = TableMacroBar.query.filter_by(user_id=user.id, character_id=char.id).first()
    stored = row.slots if row and isinstance(row.slots, list) else []
    # A slot whose weapon left the inventory simply drops out.
    slots = [by_id[slot_id] for slot_id in
             (_slot_id(slot.get("kind"), slot.get("key")) for slot in stored if isinstance(slot, dict))
             if slot_id in by_id]
    return {"characterId": char.id, "slots": slots, "options": options, "limit": MAX_MACRO_SLOTS, "reason": None}


def save_bar(user, char, raw_slots):
    options = macro_options(char)
    if options is None:
        raise MacroError("not_srd", "Für diesen Charakter gibt es keine Bogen-Würfe.", 422)
    if not isinstance(raw_slots, list):
        raise MacroError("invalid_slots", "slots muss eine Liste sein.")
    if len(raw_slots) > MAX_MACRO_SLOTS:
        raise MacroError("too_many_slots", f"Höchstens {MAX_MACRO_SLOTS} Makros.")
    by_id = {_slot_id(option["kind"], option["key"]): option for option in options}
    chosen, seen = [], set()
    for slot in raw_slots:
        slot_id = _slot_id(slot.get("kind"), slot.get("key")) if isinstance(slot, dict) else None
        if slot_id not in by_id:
            raise MacroError("invalid_slot", "Diesen Wurf gibt es auf dem Bogen nicht.", 422)
        if slot_id in seen:
            continue
        seen.add(slot_id)
        chosen.append({"kind": by_id[slot_id]["kind"], "key": by_id[slot_id]["key"]})
    row = TableMacroBar.query.filter_by(user_id=user.id, character_id=char.id).first()
    if row is None:
        db.session.add(TableMacroBar(user_id=user.id, character_id=char.id, slots=chosen))
    else:
        row.slots = chosen
    db.session.commit()
    return bar_view(user, char)
