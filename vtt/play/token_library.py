"""Templates belong to one user, campaign and authorized presentation mode."""
import re
from flask import g, jsonify, request
from flask_jwt_extended import jwt_required
from vtt.extensions import db, limiter
from vtt.models import Asset, Character, TokenState
from vtt.models.session_feedback import TokenTemplate
from vtt.play import play_bp
from vtt.play.routes import _get_context
from vtt.play.service import is_token_visible_to, is_operator_role


def _scope(campaign_id, session_id):
    user, campaign, session, role = _get_context(campaign_id, session_id)
    if isinstance(role, tuple):
        return None, role
    if role not in {"PLAYER", "DM", "CO_DM"}:
        return None, (jsonify(error="forbidden"), 403)
    return (user, campaign, session, role), None


def _query(user, campaign):
    return TokenTemplate.query.filter_by(user_id=user.id, campaign_id=campaign.id,
                                         mode=g.table_context.mode)


@play_bp.route("/campaigns/<int:campaign_id>/sessions/<int:session_id>/token-library", methods=["GET", "POST"])
@jwt_required()
@limiter.limit("120 per minute")
def token_library(campaign_id, session_id):
    scope, error = _scope(campaign_id, session_id)
    if error:
        return error
    user, campaign, session, role = scope
    query = _query(user, campaign)
    if request.method == "GET":
        return jsonify(templates=[row.serialize() for row in query.order_by(TokenTemplate.name, TokenTemplate.id).limit(200)])
    body = request.get_json(silent=True) or {}
    if not isinstance(body, dict):
        return jsonify(error="invalid_body"), 400
    if type(body.get("token_id")) is not int:
        return jsonify(error="token_required"), 400
    token = TokenState.query.filter_by(id=body["token_id"], campaign_id=campaign.id,
                                      game_session_id=session.id, deleted_at=None).first()
    if not token or not is_token_visible_to(token, role, user.id) or (
            not is_operator_role(role) and token.owner_user_id != user.id):
        return jsonify(error="token_not_available"), 404
    if query.count() >= 200:
        return jsonify(error="library_limit", message="Die Bibliothek enthält bereits 200 Vorlagen."), 409
    name = str(body.get("name") or token.name).strip()[:120]
    if not name:
        return jsonify(error="name_required"), 400
    image = (token.metadata_json or {}).get("image_url")
    metadata = {}
    match = re.fullmatch(r"/api/assets/(\d+)/preview", str(image or ""))
    if match:
        asset = db.session.get(Asset, int(match[1]))
        if asset and asset.campaign_id == campaign.id and not asset.deleted_at and asset.asset_type in {"token", "image"}:
            metadata["image_url"] = image
    elif isinstance(image, str) and image.startswith("https://") and len(image) <= 2048:
        metadata["image_url"] = image
    values = dict(token_type=token.token_type if is_operator_role(role) else "player",
                  size=token.size, rotation=token.rotation, hp_max=token.hp_max,
                  sight_range=token.sight_range, metadata_json=metadata)
    if token.character_id:
        character = db.session.get(Character, token.character_id)
        if character and not character.deleted_at and character.campaign_id == campaign.id and (
                is_operator_role(role) or character.user_id == user.id):
            values["character_id"] = character.id
    row = TokenTemplate(user_id=user.id, campaign_id=campaign.id, mode=g.table_context.mode,
                        name=name, values=values)
    db.session.add(row)
    db.session.commit()
    return jsonify(template=row.serialize()), 201


@play_bp.route("/campaigns/<int:campaign_id>/sessions/<int:session_id>/token-library/<int:template_id>", methods=["PATCH", "DELETE"])
@jwt_required()
def update_token_template(campaign_id, session_id, template_id):
    scope, error = _scope(campaign_id, session_id)
    if error:
        return error
    user, campaign, session, role = scope
    row = _query(user, campaign).filter_by(id=template_id).with_for_update().first()
    if not row:
        return jsonify(error="not_found"), 404
    body = request.get_json(silent=True) or {}
    if not isinstance(body, dict):
        return jsonify(error="invalid_body"), 400
    if type(body.get("revision")) is not int or body["revision"] != row.revision:
        return jsonify(error="version_conflict"), 409
    if request.method == "DELETE":
        db.session.delete(row)
    else:
        name = body.get("name")
        size = body.get("size", row.values.get("size", 1))
        if not isinstance(name, str) or not 1 <= len(name.strip()) <= 120 or type(size) is not int or not 1 <= size <= 6:
            return jsonify(error="invalid_template"), 400
        row.name = name.strip()
        row.values = {**row.values, "size": size}
        row.revision += 1
    db.session.commit()
    return jsonify(ok=True)
