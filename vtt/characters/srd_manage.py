"""Management of finished SRD characters: archive, duplicate, rebuild as draft and companions.

Pure functions; the blueprint in `srd_creator.py` does permissions, rate limits and the commit.
"""

import copy
import re
import secrets

from sqlalchemy.orm.attributes import flag_modified

from vtt.characters.srd_progression import ProgressionError, _log
from vtt.models import Character, Equipment, InventoryItem, Spell
from vtt.rules_content.creator_drafts import identity_name, sanitize_state
from vtt.rules_content.creator_sources import default_source_ids
from vtt.utils.time import utcnow

MAX_COMPANIONS = 20
COMPANION_TEXT = {"name": 60, "kind": 40, "speed": 40, "attacks": 500, "notes": 2000}
COMPANION_NUMBERS = {"hpMax": (0, 9999), "hpCurrent": (0, 9999), "ac": (0, 50)}
_ID = re.compile(r"^[A-Za-z0-9_-]{1,40}$")
_CHILD_SKIP = {"id", "character_id", "created_at", "updated_at"}


def _data(char):
    data = char.character_data if isinstance(char.character_data, dict) else {}
    if not isinstance(data.get("srd"), dict):
        raise ProgressionError("not_srd", "Kein SRD-Charakter.")
    return data


def is_archived(char):
    lifecycle = (char.character_data or {}).get("lifecycle") if isinstance(char.character_data, dict) else None
    return isinstance(lifecycle, dict) and bool(lifecycle.get("archivedAt"))


def set_archived(char, archived, *, user_id):
    """Archive or restore (caller commits). Characters in a campaign must leave it first."""
    if not isinstance(archived, bool):
        raise ProgressionError("invalid_archived", "archived muss true oder false sein.", 400)
    _data(char)
    if archived == is_archived(char):
        return
    if archived and char.campaign_id:
        raise ProgressionError("in_campaign", "Nimm den Charakter zuerst aus der Kampagne, bevor du ihn archivierst.", 409)
    data = copy.deepcopy(char.character_data)
    if archived:
        data["lifecycle"] = {"archivedAt": utcnow().isoformat() + "Z"}
    else:
        data.pop("lifecycle", None)
    _log(data["srd"], {"type": "archive" if archived else "restore", "by": user_id})
    char.character_data = data
    flag_modified(char, "character_data")


def duplicate(char, *, user_id):
    """A new, independent character from `char` (not yet added to the session). Avatars and campaign are not copied."""
    _data(char)
    data = copy.deepcopy(char.character_data)
    data.pop("lifecycle", None)
    block = data["srd"]
    block["draftId"] = None
    block["history"] = []
    _log(block, {"type": "duplicate", "by": user_id, "fromCharacterId": char.id})
    copy_row = Character(
        user_id=user_id,
        campaign_id=None,
        name=f"{char.name} (Kopie)"[:100],
        race=char.race, class_name=char.class_name, background=char.background,
        level=char.level, xp=char.xp,
        ac=char.ac, hp_current=char.hp_current, hp_max=char.hp_max, mana_current=0, mana_max=0,
        str_score=char.str_score, dex_score=char.dex_score, con_score=char.con_score,
        int_score=char.int_score, wis_score=char.wis_score, cha_score=char.cha_score,
        proficiency_bonus=char.proficiency_bonus,
        character_data=data,
    )
    for relation, model in (("spells", Spell), ("equipment", Equipment), ("inventory", InventoryItem)):
        columns = [c.key for c in model.__table__.columns if c.key not in _CHILD_SKIP]
        for row in getattr(char, relation):
            getattr(copy_row, relation).append(model(**{key: copy.deepcopy(getattr(row, key)) for key in columns}))
    return copy_row


def draft_values(char, data):
    """(state, name, sources) for a rebuild draft; the draft later becomes a second character."""
    block = _data(char)["srd"]
    state, problems = sanitize_state(copy.deepcopy(block.get("state") or {}), data)
    if problems:
        raise ProgressionError("invalid_state", "Der Zustand ist ungültig.", 422, problems=problems)
    return state, identity_name(state)[:100] or None, state.get("sources") or default_source_ids()


# --------------------------------------------------------------------------- companions

def companions(char):
    stored = (char.character_data or {}).get("srdCompanions") if isinstance(char.character_data, dict) else None
    return [c for c in stored if isinstance(c, dict)] if isinstance(stored, list) else []


def _companion(raw, index):
    if not isinstance(raw, dict):
        raise ProgressionError("invalid_companion", f"Begleiter {index + 1}: Objekt erwartet.", 422)
    out = {}
    cid = raw.get("id")
    if cid is not None and not (isinstance(cid, str) and _ID.match(cid)):
        raise ProgressionError("invalid_companion", f"Begleiter {index + 1}: ungültige Kennung.", 422)
    out["id"] = cid
    for field, limit in COMPANION_TEXT.items():
        value = raw.get(field, "")
        if not isinstance(value, str) or len(value) > limit:
            raise ProgressionError("invalid_companion", f"Begleiter {index + 1}: {field} ist zu lang oder kein Text (höchstens {limit} Zeichen).", 422)
        out[field] = value.strip()
    if not out["name"]:
        raise ProgressionError("invalid_companion", f"Begleiter {index + 1} braucht einen Namen.", 422)
    for field, (low, high) in COMPANION_NUMBERS.items():
        value = raw.get(field, 0)
        if type(value) is not int or not low <= value <= high:
            raise ProgressionError("invalid_companion", f"Begleiter {index + 1}: {field} muss eine ganze Zahl von {low} bis {high} sein.", 422)
        out[field] = value
    out["hpCurrent"] = min(out["hpCurrent"], out["hpMax"])
    return out


def _fresh_id(taken):
    while True:
        candidate = "c" + secrets.token_hex(4)
        if candidate not in taken:
            return candidate


def set_companions(char, body, *, user_id):
    """Replace the companion list (caller commits). Returns the stored list."""
    _data(char)
    raw = body.get("companions") if isinstance(body, dict) else None
    if not isinstance(raw, list):
        raise ProgressionError("invalid_companions", "companions muss eine Liste sein.", 400)
    if len(raw) > MAX_COMPANIONS:
        raise ProgressionError("too_many_companions", f"Höchstens {MAX_COMPANIONS} Begleiter.", 422)
    cleaned, seen = [], set()
    for index, entry in enumerate(raw):
        item = _companion(entry, index)
        if item["id"] is None or item["id"] in seen:
            item["id"] = _fresh_id(seen)
        seen.add(item["id"])
        cleaned.append(item)
    data = copy.deepcopy(char.character_data)
    data["srdCompanions"] = cleaned
    char.character_data = data
    flag_modified(char, "character_data")
    return cleaned
