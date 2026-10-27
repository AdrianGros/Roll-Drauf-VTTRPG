"""Sheet rolls and the live link between a character and its table tokens.

Rolls are rolled and logged by the server from the evaluated sheet, so the
client only chooses *what* to roll. The link keeps hit points and the sheet
values on a token in step with the character it belongs to.
"""

import random

from vtt.extensions import db
from vtt.models import Campaign, ChatMessage, Character, GameSession, TokenState
from vtt.rules_content.creator_drafts import is_srd_character_data
from vtt.rules_content.creator_rules import evaluate
from vtt.rules_content.species_profiles import rules_data_for_block

ABILITY_NAMES = {
    "str": "Stärke", "dex": "Geschicklichkeit", "con": "Konstitution",
    "int": "Intelligenz", "wis": "Weisheit", "cha": "Charisma",
}
ROLL_KINDS = ("ability", "save", "skill", "initiative", "spell_attack", "death_save", "weapon_attack", "weapon_damage")
ROLL_MODES = ("normal", "advantage", "disadvantage")
LIVE_STATUSES = ("scheduled", "ready", "in_progress", "paused")
NOT_RUNNING = {"paused": "ist pausiert", "ended": "ist beendet", "completed": "ist beendet", "cancelled": "wurde abgesagt"}


class RollTargetError(Exception):
    """The table a sheet roll names cannot take it: the roll is refused, never sent to another table."""

    def __init__(self, code, message, status, **extra):
        super().__init__(message)
        self.code, self.message, self.status, self.extra = code, message, status, extra


def srd_block(char):
    """The SRD block of a character, else None."""
    if not is_srd_character_data(char.character_data):
        return None
    block = (char.character_data or {}).get("srd")
    return block if isinstance(block, dict) else None


def rules_data(char):
    """The rules data this character is evaluated with: SRD plus its pinned homebrew Species, if any."""
    return rules_data_for_block(srd_block(char))


def srd_evaluation(char):
    """Fresh rules evaluation for an SRD character (from its pinned Species, if any), else None."""
    block = srd_block(char)
    if block is None:
        return None
    return evaluate(rules_data_for_block(block), block.get("state") or {})


def roll_spec(evaluation, kind, key):
    """What to roll for `kind`/`key`: {label, modifier} or None when the sheet has no such entry."""
    if kind == "initiative":
        return {"label": "Initiative", "modifier": int(evaluation.get("initiative", 0))}
    if kind == "death_save":
        return {"label": "Todesrettungswurf", "modifier": 0}
    if kind == "ability":
        ability = (evaluation.get("abilities") or {}).get(key)
        if key in ABILITY_NAMES and ability:
            return {"label": f"{ABILITY_NAMES[key]}-Probe", "modifier": int(ability["modifier"])}
    elif kind == "save":
        save = (evaluation.get("saves") or {}).get(key)
        if key in ABILITY_NAMES and save:
            return {"label": f"{ABILITY_NAMES[key]}-Rettungswurf", "modifier": int(save["bonus"])}
    elif kind == "skill":
        skill = (evaluation.get("skills") or {}).get(key)
        if skill:
            return {"label": skill["name"], "modifier": int(skill["bonus"])}
    elif kind == "spell_attack":
        info = ((evaluation.get("spellcasting") or {}).get("classes") or {}).get(key)
        if info:
            name = next((c["name"] for c in evaluation.get("classes", []) if c.get("classKey") == key), key)
            return {"label": f"Zauberangriff ({name})", "modifier": int(info["attackBonus"])}
    return None


def dice_text(modifier):
    return "1d20" + (f"{modifier:+d}" if modifier else "")


def roll_d20(modifier, mode="normal", rng=None):
    """One d20 with advantage/disadvantage; returns the same result shape the table roller uses."""
    rng = rng or random.SystemRandom()
    mode = mode if mode in ROLL_MODES else "normal"
    first = rng.randint(1, 20)
    result = {"rolls": [first], "modifier": modifier, "mode": mode}
    if mode != "normal":
        second = rng.randint(1, 20)
        keep = max(first, second) if mode == "advantage" else min(first, second)
        result["rolls"] = [keep]
        result["discarded_rolls"] = [second if keep == first else first]
    result["total"] = result["rolls"][0] + modifier
    result["natural"] = result["rolls"][0]
    return result


def can_roll_for(user, char):
    if char.user_id == user.id:
        return True
    if not char.campaign_id:
        return False
    from vtt.socket_handlers import _is_dm
    return _is_dm(char.campaign_id, user.id)


def session_view(game_session):
    return {"id": game_session.id, "name": game_session.name} if game_session else None


def rollable_sessions(user, char):
    """Running sessions of the character's campaign in which `user` may roll at the table, newest first."""
    from vtt.socket_handlers import _is_active_member, _reject_read_only

    campaign = db.session.get(Campaign, char.campaign_id) if char.campaign_id else None
    if campaign is None or not _is_active_member(campaign.id, user.id):
        return []
    running = (
        GameSession.query.filter_by(campaign_id=campaign.id, status="in_progress")
        .order_by(GameSession.id.desc())
        .all()
    )
    return [s for s in running if not _reject_read_only(campaign, s, user)]


def roll_destination(user, char, session_id=None):
    """Where a sheet roll is logged: {"session": GameSession or None, "sessions": [...], "reason": str or None}.

    An explicit `session_id` (the table the sheet was opened from or chosen on it) must be a running
    session of the character's campaign in which `user` may roll, else RollTargetError. Without one,
    the campaign's only running session is used; with several the player has to choose
    ("choose_session"), and with none the roll stays on the sheet ("no_session" / "no_campaign").
    """
    from vtt.socket_handlers import _is_active_member, _reject_read_only

    if session_id is None:
        sessions = rollable_sessions(user, char)
        if len(sessions) == 1:
            return {"session": sessions[0], "sessions": sessions, "reason": None}
        reason = "choose_session" if sessions else ("no_session" if char.campaign_id else "no_campaign")
        return {"session": None, "sessions": sessions, "reason": reason}
    campaign = db.session.get(Campaign, char.campaign_id) if char.campaign_id else None
    game_session = db.session.get(GameSession, session_id)
    if campaign is None or game_session is None or game_session.campaign_id != campaign.id:
        raise RollTargetError("session_mismatch", "Dieser Tisch gehört nicht zur Kampagne des Charakters.", 409)
    if not _is_active_member(campaign.id, user.id):
        raise RollTargetError("session_forbidden", "Du sitzt nicht an diesem Tisch.", 403)
    if game_session.status != "in_progress":
        state = NOT_RUNNING.get(game_session.status, "hat noch nicht begonnen")
        raise RollTargetError("session_not_live", f"Die Sitzung „{game_session.name}“ {state}.", 409,
                              sessionStatus=game_session.status)
    if _reject_read_only(campaign, game_session, user):
        raise RollTargetError("session_forbidden", "An diesem Tisch kannst du nur zusehen.", 403)
    return {"session": game_session, "sessions": [game_session], "reason": None}


def log_roll(user, char, game_session, spec, result, visibility):
    """Persist the roll in the chat log of `game_session` (from roll_destination) and broadcast it there.

    Returns the message id, or None when the roll stays on the sheet (no session).
    """
    from vtt.socket_handlers import _emit_scoped_roll, _is_dm

    if game_session is None:
        return None
    campaign = db.session.get(Campaign, game_session.campaign_id)
    if visibility in ("blind", "self") and not _is_dm(campaign.id, user.id):
        visibility = "public"
    if visibility not in ("public", "gm_only", "blind", "self"):
        visibility = "public"
    dice = spec.get("dice") or dice_text(result["modifier"])
    mode_text = {"advantage": " (Vorteil)", "disadvantage": " (Nachteil)"}.get(result["mode"], "")
    kept = " + ".join(str(r) for r in result["rolls"]) if spec.get("damage") else result["rolls"][0]
    modifier_text = f" {result['modifier']:+d}" if result["modifier"] else ""
    if spec.get("damage") and not result["rolls"]:
        kept, modifier_text = result["modifier"], ""
    message = ChatMessage(
        campaign_id=campaign.id,
        game_session_id=game_session.id,
        author_user_id=user.id,
        content=f"{char.name} · {spec['label']}{mode_text}: würfelt {dice}: {kept}{modifier_text} = {result['total']}",
        content_type="dice_roll",
        visibility=visibility,
    )
    db.session.add(message)
    db.session.commit()
    _emit_scoped_roll(
        campaign.id, game_session.id,
        {"player": char.name, "dice": dice, "label": spec["label"], "result": result,
         "message_id": message.id, "visibility": visibility},
        visibility=visibility,
    )
    return message.id


def sheet_snapshot(char):
    """Values shown on a linked token; derived from the rules for SRD characters."""
    snapshot = {"ac": char.ac, "level": char.level}
    evaluation = srd_evaluation(char)
    if evaluation:
        snapshot.update(
            ac=evaluation["armorClass"]["value"],
            passivePerception=evaluation.get("passivePerception"),
            speedMeters=evaluation.get("speedMeters"),
            initiative=evaluation.get("initiative"),
            proficiencyBonus=evaluation.get("proficiencyBonus"),
        )
    return snapshot


def link_error(campaign, user, is_dm, character_id, game_session_id, token_id=None):
    """Why this character may not be linked to a token (message), or None if it may."""
    char = db.session.get(Character, character_id) if isinstance(character_id, int) else None
    if char is None or char.deleted_at or char.campaign_id != campaign.id:
        return "Charakter nicht gefunden."
    if not is_dm and char.user_id != user.id:
        return "Du kannst nur deine eigenen Charaktere verknüpfen."
    taken = TokenState.query.filter(
        TokenState.character_id == char.id, TokenState.game_session_id == game_session_id,
        TokenState.deleted_at.is_(None))
    if token_id is not None:
        taken = taken.filter(TokenState.id != token_id)
    if taken.first():
        return "Dieser Charakter hat in dieser Sitzung bereits einen Token."
    return None


def linkable_characters(campaign, user, is_dm, game_session_id):
    """Characters of this campaign the user may put on the table in this session (no token yet)."""
    taken = {
        row[0] for row in db.session.query(TokenState.character_id).filter(
            TokenState.game_session_id == game_session_id, TokenState.deleted_at.is_(None),
            TokenState.character_id.isnot(None))
    }
    query = Character.query.filter(Character.campaign_id == campaign.id, Character.deleted_at.is_(None))
    if not is_dm:
        query = query.filter(Character.user_id == user.id)
    return [
        {"id": c.id, "name": c.name, "level": c.level, "hp": f"{c.hp_current}/{c.hp_max}", "ac": c.ac,
         "srd": is_srd_character_data(c.character_data)}
        for c in query.order_by(Character.name).all() if c.id not in taken
    ]


def apply_character_to_token(token, char):
    """Copy the character's hit points and sheet values onto the token (caller commits)."""
    token.hp_current = char.hp_current
    token.hp_max = char.hp_max
    metadata = dict(token.metadata_json or {})
    metadata["sheet"] = sheet_snapshot(char)
    token.metadata_json = metadata


def apply_token_patch_to_character(token, patch):
    """A hit-point edit on a linked token lands on the character; the maximum stays the sheet's (caller commits)."""
    if not token.character_id or not {"hp_current", "hp_max"} & set(patch):
        return
    char = db.session.get(Character, token.character_id)
    if char is None or char.deleted_at or not is_srd_character_data(char.character_data):
        return
    token.hp_max = char.hp_max
    if token.hp_current is not None:
        token.hp_current = max(0, min(token.hp_current, char.hp_max))
        char.hp_current = token.hp_current


def push_character_to_tokens(char):
    """After a sheet change, refresh every open table token of this character and broadcast it."""
    from vtt.socket_handlers import _emit_token_event

    if not is_srd_character_data(char.character_data):
        return 0
    tokens = (
        TokenState.query.join(GameSession, TokenState.game_session_id == GameSession.id)
        .filter(TokenState.character_id == char.id, TokenState.deleted_at.is_(None),
                GameSession.status.in_(LIVE_STATUSES))
        .all()
    )
    events = []
    for token in tokens:
        old_visibility, old_owner = token.visibility, token.owner_user_id
        apply_character_to_token(token, char)
        token.version += 1
        token.session_state.bump_version()
        events.append((token, old_visibility, old_owner))
    if not events:
        return 0
    db.session.commit()
    for token, old_visibility, old_owner in events:
        _emit_token_event(
            "updated", token.campaign_id, token.game_session_id,
            {"token": token.serialize(), "version": token.version,
             "state_version": token.session_state.version, "client_event_id": None},
            visibility=token.visibility, owner_user_id=token.owner_user_id,
            old_visibility=old_visibility, old_owner_user_id=old_owner)
    return len(events)
