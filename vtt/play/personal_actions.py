"""Personal action references over the existing character rules and roll seam."""

from hashlib import sha256
import json

from flask import g, jsonify, request
from flask_jwt_extended import jwt_required
from sqlalchemy.exc import IntegrityError

from vtt.characters import sheet_link, srd_inventory
from vtt.extensions import db, limiter, socketio
from vtt.models import Character, ChatMessage, TokenState
from vtt.models.character_hotbar import CharacterHotbar
from vtt.play import play_bp
from vtt.play.receipts import idempotent_table_request
from vtt.play.contexts import current_role
from vtt.play.service import is_operator_role, is_read_only_mode
from vtt.utils.realtime import build_event_envelope, session_room


def _character(campaign_id, session_id, char_id):
    context = g.table_context
    char = db.session.get(Character, char_id)
    if not char or char.deleted_at is not None or char.campaign_id != campaign_id:
        return None
    role = current_role(campaign_id, context.user_id, session_id)
    if role is None:
        return None
    operator = is_operator_role(role)
    if char.user_id != context.user_id and not operator:
        return None
    tokens = TokenState.query.filter_by(game_session_id=session_id, character_id=char_id, deleted_at=None)
    if not operator:
        tokens = tokens.filter(TokenState.owner_user_id == context.user_id,
                               TokenState.visibility.in_(["public", "owner_only"]))
    return char if tokens.first() else None


def catalog(char):
    evaluation = sheet_link.srd_evaluation(char)
    if evaluation is None:
        return {"revision": "unsupported", "actions": []}
    actions = []

    def add(kind, key, label, detail=""):
        actions.append({"id": f"{kind}:{key or ''}", "kind": kind, "key": key,
                        "label": label, "detail": detail})

    for kind, values in [("ability", evaluation.get("abilities", {})),
                         ("save", evaluation.get("saves", {})),
                         ("skill", evaluation.get("skills", {}))]:
        for key in values:
            spec = sheet_link.roll_spec(evaluation, kind, key)
            if spec:
                add(kind, key, spec["label"], sheet_link.dice_text(spec["modifier"]))
    for kind in ("initiative", "death_save"):
        spec = sheet_link.roll_spec(evaluation, kind, None)
        add(kind, None, spec["label"], sheet_link.dice_text(spec["modifier"]))
    for weapon in srd_inventory.attack_rows(char, evaluation, srd_inventory.items_of(char)):
        for kind, title in [("weapon_attack", "Angriffswurf"), ("weapon_damage", "Schaden")]:
            spec = srd_inventory.weapon_roll_spec(char, evaluation, kind, weapon["key"])
            add(kind, weapon["key"], f"{weapon['name']} · {title}",
                spec.get("dice") or sheet_link.dice_text(spec.get("modifier", 0)))
    for class_key in ((evaluation.get("spellcasting") or {}).get("classes") or {}):
        spec = sheet_link.roll_spec(evaluation, "spell_attack", class_key)
        if spec:
            add("spell_attack", class_key, spec["label"], sheet_link.dice_text(spec["modifier"]))
    block = sheet_link.srd_block(char)
    selected = ((block or {}).get("state") or {}).get("spells") or {}
    data = sheet_link.rules_data(char)
    spell_rows = data.get("spells") or {}
    spells = spell_rows if isinstance(spell_rows, dict) else {spell["id"]: spell for spell in spell_rows}
    chosen = set()
    for selection in selected.values():
        if isinstance(selection, dict):
            chosen.update(selection.get("cantrips") or [])
            chosen.update(selection.get("prepared") or [])
    for key in sorted(chosen):
        spell = spells.get(key)
        if spell:
            add("spell_declare", key, f"{spell['name']} · ankündigen",
                "Ankündigung; Zauberplätze und Effekte verwaltest du am Bogen.")
    revision = sha256(json.dumps(actions, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    return {"revision": revision, "actions": actions}


@play_bp.route("/campaigns/<int:campaign_id>/sessions/<int:session_id>/characters/<int:char_id>/hotbar", methods=["GET", "PUT"])
@jwt_required()
def personal_hotbar(campaign_id, session_id, char_id):
    char = _character(campaign_id, session_id, char_id)
    if char is None:
        return jsonify(error="character_not_available_at_table"), 403
    context = g.table_context
    current = catalog(char)
    row = CharacterHotbar.query.filter_by(user_id=context.user_id, character_id=char.id).first()
    if request.method == "PUT":
        body = request.get_json(silent=True)
        if not isinstance(body, dict) or not isinstance(body.get("slots"), list) or len(body["slots"]) > 10:
            return jsonify(error="invalid_hotbar"), 400
        ids = {action["id"] for action in current["actions"]}
        slots = body["slots"]
        if any(value is not None and (not isinstance(value, str) or value not in ids) for value in slots):
            return jsonify(error="unknown_action_reference"), 422
        expected = body.get("revision")
        if type(expected) is not int or expected != (row.revision if row else 0):
            return jsonify(error="hotbar_conflict"), 409
        if row:
            changed = CharacterHotbar.query.filter_by(id=row.id, revision=expected).update(
                {"slots": slots, "revision": expected + 1}, synchronize_session=False)
            if not changed:
                db.session.rollback()
                return jsonify(error="hotbar_conflict"), 409
        else:
            row = CharacterHotbar(user_id=context.user_id, character_id=char.id, slots=slots, revision=1)
            db.session.add(row)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            return jsonify(error="hotbar_conflict"), 409
        db.session.refresh(row)
    response = jsonify(character_id=char.id, character_name=char.name, revision=row.revision if row else 0,
                       slots=row.slots if row else [], catalog=current)
    response.headers["Cache-Control"] = "private, no-store"
    return response


@play_bp.post("/campaigns/<int:campaign_id>/sessions/<int:session_id>/characters/<int:char_id>/actions/execute")
@limiter.limit("240 per hour")
@jwt_required()
@idempotent_table_request
def execute_personal_action(campaign_id, session_id, char_id):
    from vtt.models import GameSession, User
    char = _character(campaign_id, session_id, char_id)
    if char is None:
        return jsonify(error="character_not_available_at_table"), 403
    context = g.table_context
    game_session = db.session.get(GameSession, session_id)
    if game_session.status != "in_progress" or is_read_only_mode(game_session.status, current_role(campaign_id, context.user_id, session_id)):
        return jsonify(error="read_only"), 403
    body = request.get_json(silent=True)
    if not isinstance(body, dict) or not isinstance(body.get("request_id"), str):
        return jsonify(error="request_id_required"), 400
    current = catalog(char)
    if body.get("catalog_revision") != current["revision"]:
        return jsonify(error="action_catalog_changed", message="Die Figur hat sich geändert. Bitte die Aktionsleiste neu laden."), 409
    action = next((a for a in current["actions"] if a["id"] == body.get("action_id")), None)
    if action is None:
        return jsonify(error="unknown_action_reference"), 422
    user = db.session.get(User, context.user_id)
    if action["kind"] == "spell_declare":
        try:
            sheet_link.roll_destination(user, char, session_id)
        except sheet_link.RollTargetError as exc:
            return jsonify(error=exc.code, message=exc.message), exc.status
        text = f"{char.name}: {action['label']}. Zauberplätze und Effekte werden am Bogen verwaltet."
        message = ChatMessage(campaign_id=campaign_id, game_session_id=session_id, author_user_id=user.id,
                              content=text, content_type="action_declaration", visibility="public")
        db.session.add(message)
        db.session.commit()
        socketio.emit("chat:message_sent", build_event_envelope(campaign_id, session_id,
                      {"message": text, "sender_name": char.name, "message_id": message.id}),
                      room=session_room(campaign_id, session_id))
        return jsonify(messageId=message.id, label=action["label"], declared=True, resources="manual")
    try:
        result = sheet_link.execute_sheet_roll(user, char, action["kind"], action["key"],
                                               session_id=session_id, mode=body.get("mode", "normal"),
                                               visibility=body.get("visibility", "public"))
    except sheet_link.RollTargetError as exc:
        return jsonify(error=exc.code, message=exc.message), exc.status
    return jsonify(result)
