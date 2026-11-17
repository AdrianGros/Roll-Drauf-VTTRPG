"""One authorized actor/initiative seam for internal, sheet and external rolls."""
import math
import random
import uuid
import hashlib
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


def _apply_accepted_initiative(token, total, user_id):
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


def _locked_round(session_id):
    from vtt.models import GameSession
    from vtt.models.ui_playtable import InitiativeRound
    db.session.query(GameSession).filter_by(id=session_id).with_for_update().one()
    row = db.session.get(InitiativeRound, session_id, populate_existing=True)
    if row is None:
        row = InitiativeRound(session_id=session_id, number=1, revision=0)
        db.session.add(row); db.session.flush()
    return row


def apply_initiative(token, total, user_id, *, event_id=None, source='roll'):
    """First roll applies; distinct later rolls wait for an explicit DM decision."""
    from vtt.models.ui_playtable import InitiativeCandidate
    if type(total) not in (int, float) or not math.isfinite(total) or int(total) != total or abs(total) > 10000:
        raise ValueError('Initiative muss eine ganze Zahl zwischen -10000 und 10000 sein.')
    round_ = _locked_round(token.game_session_id)
    CombatEncounter.query.filter_by(game_session_id=token.game_session_id, status="active").with_for_update().first()
    db.session.refresh(token, with_for_update=True)
    body = request.get_json(silent=True) or {}
    key = event_id or (body.get('request_id') if isinstance(body, dict) else None) or str(uuid.uuid4())
    key = hashlib.sha256(f'{user_id}:{source}:{key}'.encode()).hexdigest()
    previous = InitiativeCandidate.query.filter_by(session_id=token.game_session_id,
        round_number=round_.number, event_id=key).first()
    if previous:
        if previous.token_id != token.id or previous.total != int(total):
            raise ValueError('Diese Wurf-ID wurde bereits für einen anderen Wurf verwendet.')
        return None
    candidate = InitiativeCandidate(campaign_id=token.campaign_id, session_id=token.game_session_id,
        round_number=round_.number, token_id=token.id, actor_id=user_id, event_id=key,
        source=source[:30], total=int(total), status='accepted' if token.initiative is None else 'pending')
    db.session.add(candidate); round_.revision += 1
    if candidate.status == 'accepted':
        return _apply_accepted_initiative(token, total, user_id)
    token.session_state.bump_version()
    return None


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


@play_bp.route('/campaigns/<int:campaign_id>/sessions/<int:session_id>/initiative-candidates', methods=['GET', 'POST'])
@jwt_required()
@limiter.limit('90 per minute')
def initiative_candidates(campaign_id, session_id):
    from vtt.play.routes import _get_context
    from vtt.models.ui_playtable import InitiativeRound, InitiativeCandidate
    user, campaign, session, role = _get_context(campaign_id, session_id)
    if isinstance(role, tuple): return role
    if request.method == 'POST':
        if is_read_only_mode(session.status, role): return jsonify(error='read_only'),403
        body = request.get_json(silent=True)
        if not isinstance(body, dict) or set(body)-{'token_id','total','event_id','source'} or not isinstance(body.get('event_id'),str) or not 8 <= len(body['event_id']) <= 120:
            return jsonify(error='invalid_candidate'),400
        try:
            token=actor_token(campaign_id,session_id,user.id,body.get('token_id'))
            apply_initiative(token,body.get('total'),user.id,event_id=body['event_id'],source='tracker')
            db.session.commit();publish_initiative(token)
        except ValueError as error:
            db.session.rollback();return jsonify(error='initiative_rejected',message=str(error)),403
    round_=db.session.get(InitiativeRound,session_id)
    number=round_.number if round_ else 1
    tokens=TokenState.query.filter_by(campaign_id=campaign_id,game_session_id=session_id,deleted_at=None).all()
    allowed={t.id:t for t in tokens if is_token_visible_to(t,role,user.id)
             and (is_operator_role(role) or t.owner_user_id==user.id)}
    rows=InitiativeCandidate.query.filter_by(session_id=session_id,round_number=number).order_by(InitiativeCandidate.id.desc()).limit(200).all()
    return jsonify(round=number,revision=round_.revision if round_ else 0,
        candidates=[dict(id=r.id,token_id=r.token_id,name=allowed[r.token_id].name,
            total=r.total,status=r.status,source=r.source,created_at=r.created_at.isoformat())
            for r in rows if r.token_id in allowed])


@play_bp.post('/campaigns/<int:campaign_id>/sessions/<int:session_id>/initiative-candidates/<int:candidate_id>/accept')
@jwt_required()
@idempotent_table_request
def accept_initiative_candidate(campaign_id,session_id,candidate_id):
    from vtt.play.routes import _get_context
    from vtt.models.ui_playtable import InitiativeCandidate
    user,campaign,session,role=_get_context(campaign_id,session_id)
    if isinstance(role,tuple):return role
    if not is_operator_role(role) or is_read_only_mode(session.status,role):return jsonify(error='forbidden'),403
    body=request.get_json(silent=True) or {}
    round_=_locked_round(session_id)
    if not isinstance(body,dict) or type(body.get('revision')) is not int or body['revision']!=round_.revision:
        return jsonify(error='version_conflict'),409
    row=InitiativeCandidate.query.filter_by(id=candidate_id,campaign_id=campaign_id,session_id=session_id,round_number=round_.number).first()
    if not row:return jsonify(error='not_found'),404
    try:token=actor_token(campaign_id,session_id,user.id,row.token_id)
    except ValueError as error:return jsonify(error='token_not_available',message=str(error)),409
    _apply_accepted_initiative(token,row.total,user.id)
    for other in InitiativeCandidate.query.filter_by(session_id=session_id,round_number=round_.number,token_id=token.id).all():
        other.status='accepted' if other.id==row.id else 'superseded'
    row.decided_by=user.id;round_.revision+=1
    db.session.commit();publish_initiative(token)
    return jsonify(accepted=row.id,total=row.total,revision=round_.revision)


@play_bp.post('/campaigns/<int:campaign_id>/sessions/<int:session_id>/initiative-candidates/reset')
@jwt_required()
@idempotent_table_request
def reset_initiative_round(campaign_id,session_id):
    from vtt.play.routes import _get_context
    user,campaign,session,role=_get_context(campaign_id,session_id)
    if isinstance(role,tuple):return role
    if not is_operator_role(role) or is_read_only_mode(session.status,role):return jsonify(error='forbidden'),403
    body=request.get_json(silent=True) or {};round_=_locked_round(session_id)
    if body.get('confirm') is not True or body.get('revision')!=round_.revision:
        return jsonify(error='confirmation_or_revision_required'),409
    tokens=TokenState.query.filter_by(campaign_id=campaign_id,game_session_id=session_id,deleted_at=None).all()
    for token in tokens:
        token.initiative=None;token.version+=1;token.session_state.bump_version()
    round_.number+=1;round_.revision+=1;db.session.commit()
    for token in tokens:publish_initiative(token)
    return jsonify(round=round_.number,revision=round_.revision)
