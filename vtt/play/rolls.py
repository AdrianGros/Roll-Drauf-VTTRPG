"""One authorized actor/initiative seam for internal, sheet and external rolls."""
import math
import random
from flask import g, jsonify, request
from flask_jwt_extended import jwt_required
from vtt.extensions import db, limiter
from vtt.models import CombatEncounter, TokenState
from vtt.play import play_bp
from vtt.play.contexts import current_role
from vtt.play.receipts import idempotent_table_request
from vtt.play.service import is_operator_role, is_read_only_mode, is_token_visible_to


def actor_token(campaign_id, session_id, user_id, token_id=None, character_id=None):
    role = current_role(campaign_id, user_id, session_id)
    if role not in {"DM", "CO_DM", "PLAYER"}:
        raise ValueError("Du kannst in diesem Tischkontext nicht für einen Token würfeln.")
    query = TokenState.query.filter_by(campaign_id=campaign_id, game_session_id=session_id, deleted_at=None)
    if token_id is not None:
        if type(token_id) is not int:
            raise ValueError("Bitte einen eigenen Token auswählen.")
        query = query.filter_by(id=token_id)
    elif character_id is not None:
        query = query.filter_by(character_id=character_id)
    else:
        raise ValueError("Bitte zuerst deinen Token auswählen.")
    candidates = [t for t in query.all() if is_token_visible_to(t, role, user_id)
                  and (is_operator_role(role) or t.owner_user_id == user_id)
                  and t.map_id == t.session_state.active_map_id]
    if len(candidates) != 1:
        raise ValueError("Dieser Token ist nicht eindeutig an deinem aktuellen Tisch verfügbar.")
    return candidates[0]


def apply_initiative(token, total, user_id):
    if isinstance(total, bool) or not isinstance(total, (float, int)) or not math.isfinite(total) or int(total) != total or abs(total) > 10000:
        raise ValueError("Initiative muss eine ganze Zahl zwischen -10000 und 10000 sein.")
    encounter = CombatEncounter.query.filter_by(game_session_id=token.game_session_id, status="active").with_for_update().first()
    # Serialize competing writes to the token even before combat has begun.
    db.session.refresh(token, with_for_update=True)
    token.initiative = int(total)
    token.updated_by = user_id
    token.version += 1
    if encounter:
        from vtt.combat.service import set_initiative
        current = encounter.active_token_id
        error = set_initiative(encounter, [{"token_id": token.id, "initiative": int(total)}], user_id)
        if error:
            raise ValueError(error)
        if current in encounter.initiative_order_json:
            encounter.active_token_id = current
            encounter.turn_index = encounter.initiative_order_json.index(current)
    token.session_state.bump_version()
    return encounter


def publish_initiative(token):
    from vtt.socket_handlers import _emit_token_event
    from vtt.campaigns.routes import _emit_combat_event, _serialize_combat_state
    from vtt.combat.service import get_active_encounter
    _emit_token_event("updated", token.campaign_id, token.game_session_id,
                      {"token": token.serialize(), "version": token.version,
                       "state_version": token.session_state.version, "client_event_id": None},
                      visibility=token.visibility, owner_user_id=token.owner_user_id)
    encounter = get_active_encounter(token.game_session_id)
    if encounter:
        _emit_combat_event(token.campaign_id, token.game_session_id, "combat:updated",
                           {"change": "initiative", "state": _serialize_combat_state(encounter, token.session_state)})


@play_bp.post("/campaigns/<int:campaign_id>/sessions/<int:session_id>/tokens/<int:token_id>/initiative-roll")
@jwt_required()
@limiter.limit("30 per minute")
@idempotent_table_request
def roll_token_initiative(campaign_id, session_id, token_id):
    from vtt.models import ChatMessage, GameSession
    session = db.session.get(GameSession, session_id)
    user_id = g.table_context.user_id
    role = current_role(campaign_id, user_id, session_id)
    if not session or is_read_only_mode(session.status, role):
        return jsonify(error="read_only"), 403
    try:
        token = actor_token(campaign_id, session_id, user_id, token_id)
        modifier = 0
        if token.character:
            from vtt.characters import sheet_link
            evaluation = sheet_link.srd_evaluation(token.character)
            if evaluation:
                modifier = int(evaluation.get("initiative", 0))
            else:
                from vtt.combat.service import _dex_modifier
                modifier = _dex_modifier(token.character)
        die = random.randint(1, 20)
        total = die + modifier
        apply_initiative(token, total, user_id)
        message = ChatMessage(campaign_id=campaign_id, game_session_id=session_id,
                              author_user_id=user_id, content=f"{token.name} · Initiative: {die} {modifier:+d} = {total}",
                              content_type="dice_roll", visibility="public" if token.visibility == "public" else "gm_only")
        db.session.add(message)
        db.session.commit()
        publish_initiative(token)
        from vtt.socket_handlers import _emit_scoped_roll
        _emit_scoped_roll(campaign_id, session_id, {"player": token.name, "token_id": token.id,
                          "label": "Initiative", "dice": f"1d20{modifier:+d}",
                          "result": {"rolls": [die], "modifier": modifier, "total": total},
                          "message_id": message.id, "visibility": message.visibility}, visibility=message.visibility)
        return jsonify(total=total, token_id=token.id, message_id=message.id)
    except ValueError as error:
        db.session.rollback()
        return jsonify(error="initiative_rejected", message=str(error)), 403
