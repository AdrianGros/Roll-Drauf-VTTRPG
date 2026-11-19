"""Bounded, private artwork levels with server-side balcony/vision composition.

Levels change artwork only. Tokens, walls, light and fog retain the map's
existing 2D coordinate system; this module introduces no height simulation.
"""
import base64
from datetime import datetime
import hashlib
import hmac
from io import BytesIO
import json
import re
import uuid

from flask import Blueprint, current_app, g, jsonify, request, send_file
from flask_jwt_extended import get_jwt_identity, jwt_required
from PIL import Image, ImageDraw, UnidentifiedImageError
from sqlalchemy.exc import IntegrityError

from vtt.extensions import db, limiter
from vtt.models import CampaignMap, User, TokenState, SceneWall, SceneLight, FogOfWarState
from vtt.models.map_floor import MapFloorDeck, MapFloorImage
from vtt.endpoints.mapmaker import LibraryError, adapter, adjust_quota, cleanup
from vtt.play import contexts
from vtt.play.routes import _get_context, _get_active_map_or_404
from vtt.play.service import is_operator_role, is_token_visible_to
from vtt.play.scene_settings import view_settings, _notify
from vtt.play.vision import map_world_size
from vtt.play.illumination import render_overlay

floor_layers_bp = Blueprint("floor_layers", __name__)
BASE = "/campaigns/<int:campaign_id>/sessions/<int:session_id>"
MAX_FLOORS, MAX_SIDE, MAX_PIXELS = 8, 2048, 16_000_000
MAX_FILE, MAX_BYTES, MAX_OPENINGS = 4 * 1024**2, 16 * 1024**2, 32
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
LIMITATION = "Etagen ändern nur das Kartenbild. Tokens, Wände, Licht und Nebel bleiben auf einer gemeinsamen 2D-Karte; keine Höhen- oder Geschossbewegung."


@floor_layers_bp.after_request
def private_response(response):
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@floor_layers_bp.errorhandler(LibraryError)
def floor_error(error):
    db.session.rollback()
    return jsonify(error=str(error), code=error.code), error.status


def fail(code, status=400, message=None):
    raise LibraryError(message or code, status, code)


def context(campaign_id, session_id, dm=False):
    user, campaign, session, role = _get_context(campaign_id, session_id)
    if isinstance(role, tuple):
        return None, role
    if dm and (not is_operator_role(role) or getattr(getattr(g, "table_context", None), "mode", None) != "dm"):
        return None, (jsonify(error="forbidden"), 403)
    return (user, campaign, session, role), None


def map_for(campaign, map_id, locked=False):
    query = CampaignMap.query.filter_by(id=map_id, campaign_id=campaign.id, archived_at=None)
    row = query.with_for_update().populate_existing().first() if locked else query.first()
    if row is None:
        fail("not_found", 404)
    return row


def lock(context_, map_id):
    user, campaign, session, role = context_
    # Same owner reservation lock used by the library/asset budget, then map.
    db.session.execute(db.update(User).where(User.id == campaign.owner_id).values(
        storage_used_gb=db.func.coalesce(User.storage_used_gb, 0.0)))
    owner = db.session.get(User, campaign.owner_id, populate_existing=True)
    row = map_for(campaign, map_id, locked=True)
    if not owner or not owner.is_usable() or not contexts.validate(
            getattr(g, "table_context", None), user.id, campaign.id, session.id):
        fail("forbidden", 403)
    return owner, row


def rows(map_id):
    return MapFloorImage.query.filter_by(map_id=map_id, deleted_at=None).order_by(
        MapFloorImage.order_index, MapFloorImage.id).all()


def config(map_):
    deck = db.session.get(MapFloorDeck, map_.id)
    return dict(map_id=map_.id, revision=deck.revision if deck else 0,
                enabled=deck.enabled if deck else False,
                active_floor_id=deck.active_floor_id if deck else None,
                floors=[row.configuration() for row in rows(map_.id)],
                width=map_world_size(map_)[0], height=map_world_size(map_)[1],
                limits=dict(floors=MAX_FLOORS, side=MAX_SIDE, pixels=MAX_PIXELS,
                            file_bytes=MAX_FILE, total_bytes=MAX_BYTES, openings=MAX_OPENINGS),
                limitation=LIMITATION)


def revision(map_, value):
    deck = db.session.get(MapFloorDeck, map_.id, populate_existing=True)
    if type(value) is not int or value != (deck.revision if deck else 0):
        fail("revision_conflict", 409, "Die Etagen wurden geändert. Bitte den aktuellen Stand laden.")
    if not deck:
        deck = MapFloorDeck(map_id=map_.id, revision=0, enabled=False)
        db.session.add(deck)
    return deck


def body(allowed):
    if request.content_length is not None and request.content_length > 16384:
        fail("settings_too_large", 413)
    value = request.get_json(silent=True)
    if not isinstance(value, dict) or set(value) - allowed or "revision" not in value:
        fail("invalid_settings")
    return value


def floor_name(value):
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > 80:
        fail("invalid_name")
    return value.strip()


def read_png(upload, expected_size):
    if upload is None:
        fail("png_required")
    raw = upload.stream.read(MAX_FILE + 1)
    if len(raw) > MAX_FILE:
        fail("image_too_large", 413)
    if not raw.startswith(PNG_SIGNATURE):
        fail("png_required", 415)
    try:
        with Image.open(BytesIO(raw)) as image:
            width, height = image.size
            if image.format != "PNG" or getattr(image, "n_frames", 1) != 1:
                fail("single_png_required", 415)
            if width > MAX_SIDE or height > MAX_SIDE or width * height > MAX_PIXELS:
                fail("image_dimensions_exceeded", 413)
            if (width, height) != expected_size:
                fail("image_dimensions_mismatch", 422,
                     f"PNG muss genau {expected_size[0]} × {expected_size[1]} Pixel groß sein.")
            image.verify()
        # Re-encode actual pixels: no ancillary text/EXIF/embedded content.
        with Image.open(BytesIO(raw)) as image:
            output = BytesIO()
            image.convert("RGBA").save(output, format="PNG")
        encoded = output.getvalue()
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        fail("invalid_png", 415)
    if len(encoded) > MAX_FILE:
        fail("image_too_large", 413)
    return encoded, hashlib.sha256(raw).hexdigest(), width, height


def commit(deck, campaign_id, session_id):
    deck.revision += 1
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        fail("revision_conflict", 409)
    # A transport failure after commit must not roll back cleanup semantics or
    # remove the newly committed private object. Clients also poll the view.
    try:
        _notify(campaign_id, session_id, "floors")
    except Exception:
        current_app.logger.exception("Floor change notification failed")


@floor_layers_bp.get(BASE + "/maps/<int:map_id>/floors")
@jwt_required()
def get_configuration(campaign_id, session_id, map_id):
    ctx, error = context(campaign_id, session_id, dm=True)
    if error:
        return error
    return jsonify(config(map_for(ctx[1], map_id)))


@floor_layers_bp.post(BASE + "/maps/<int:map_id>/floors")
@jwt_required()
@limiter.limit("12 per minute", key_func=lambda: str(get_jwt_identity()))
def upload_floor(campaign_id, session_id, map_id):
    ctx, error = context(campaign_id, session_id, dm=True)
    if error:
        return error
    if request.content_length is not None and request.content_length > MAX_FILE + 8192:
        fail("image_too_large", 413)
    if set(request.form) - {"revision", "request_id", "name", "reveal_below"} or set(request.files) != {"file"}:
        fail("invalid_upload")
    map_ = map_for(ctx[1], map_id)
    name = floor_name(request.form.get("name"))
    reveal = request.form.get("reveal_below", "false")
    if reveal not in {"true", "false"}:
        fail("invalid_settings")
    request_id = request.form.get("request_id", "")
    if not re.fullmatch(r"[A-Za-z0-9_-]{16,80}", request_id):
        fail("invalid_request_id")
    try:
        expected = int(request.form.get("revision", ""))
    except ValueError:
        fail("invalid_revision")
    encoded, raw_digest, width, height = read_png(request.files.get("file"), map_world_size(map_))
    digest = hashlib.sha256(json.dumps([raw_digest, name, reveal], ensure_ascii=True).encode()).hexdigest()
    owner, map_ = lock(ctx, map_id)
    if (width, height) != map_world_size(map_):
        fail("image_dimensions_mismatch", 422)
    previous = MapFloorImage.query.filter_by(map_id=map_id, request_id=request_id).first()
    if previous:
        if previous.input_digest != digest or previous.deleted_at:
            fail("request_id_conflict", 409)
        return jsonify(config(map_)), 200
    deck = revision(map_, expected)
    current = rows(map_id)
    if len(current) >= MAX_FLOORS or sum(row.width * row.height for row in current) + width * height > MAX_PIXELS:
        fail("floor_budget_exceeded", 413)
    if sum(row.size_bytes for row in current) + len(encoded) > MAX_BYTES:
        fail("floor_budget_exceeded", 413)
    adjust_quota(owner, len(encoded))
    storage = adapter()
    key = f"users/{owner.id}/map-floors/{map_id}/{uuid.uuid4().hex}.png"
    try:
        result = storage.upload(key, encoded)
        image = MapFloorImage(map_id=map_id, order_index=len(current), name=name,
                              reveal_below=reveal == "true", openings=[], storage_key=key,
                              storage_provider=result["provider"], size_bytes=len(encoded),
                              png_sha256=hashlib.sha256(encoded).hexdigest(), width=width, height=height,
                              request_id=request_id, input_digest=digest, created_by=ctx[0].id)
        db.session.add(image)
        db.session.flush()
        if not current:
            deck.active_floor_id = image.id
        commit(deck, campaign_id, session_id)
    except Exception as exc:
        db.session.rollback()
        cleanup(storage, key)
        if isinstance(exc, LibraryError):
            raise
        current_app.logger.exception("Private floor upload failed")
        fail("storage_unavailable", 503)
    return jsonify(config(map_)), 201


@floor_layers_bp.put(BASE + "/maps/<int:map_id>/floors")
@jwt_required()
def update_deck(campaign_id, session_id, map_id):
    ctx, error = context(campaign_id, session_id, dm=True)
    if error:
        return error
    data = body({"revision", "enabled", "active_floor_id", "floor_ids"})
    _, map_ = lock(ctx, map_id)
    deck = revision(map_, data["revision"])
    current = rows(map_id)
    ids = [row.id for row in current]
    if "enabled" in data and type(data["enabled"]) is not bool:
        fail("invalid_settings")
    active = data.get("active_floor_id", deck.active_floor_id)
    if active is not None and (type(active) is not int or active not in ids):
        fail("invalid_active_floor", 422)
    enabled = data.get("enabled", deck.enabled)
    if enabled and active is None:
        fail("floor_required", 422)
    if "floor_ids" in data:
        order = data["floor_ids"]
        if not isinstance(order, list) or any(type(item) is not int for item in order) or len(order) != len(ids) or set(order) != set(ids):
            fail("invalid_floor_order", 422)
        for row in current:
            row.order_index = order.index(row.id)
    # Old cell-count maps may change world dimensions after grid edits.
    if enabled and any((row.width, row.height) != map_world_size(map_) for row in current):
        fail("image_dimensions_mismatch", 422)
    deck.active_floor_id, deck.enabled = active, enabled
    commit(deck, campaign_id, session_id)
    return jsonify(config(map_))


@floor_layers_bp.route(BASE + "/maps/<int:map_id>/floors/<int:floor_id>", methods=["PUT", "DELETE"])
@jwt_required()
def update_floor(campaign_id, session_id, map_id, floor_id):
    ctx, error = context(campaign_id, session_id, dm=True)
    if error:
        return error
    data = body({"revision"} if request.method == "DELETE" else {"revision", "name", "reveal_below", "openings"})
    owner, map_ = lock(ctx, map_id)
    deck = revision(map_, data["revision"])
    current = rows(map_id)
    row = next((item for item in current if item.id == floor_id), None)
    if row is None:
        fail("not_found", 404)
    if request.method == "DELETE":
        storage = adapter(row.storage_provider)
        adjust_quota(owner, -row.size_bytes)
        row.deleted_at = datetime.utcnow()
        remaining = [item for item in current if item != row]
        if deck.active_floor_id == row.id:
            neighbor = next((item for item in reversed(remaining) if item.order_index < row.order_index), None)
            deck.active_floor_id = (neighbor or (remaining[0] if remaining else None)).id if remaining else None
        if not remaining:
            deck.enabled = False
        for index, item in enumerate(remaining):
            item.order_index = index
        commit(deck, campaign_id, session_id)
        cleanup(storage, row.storage_key)
    else:
        if "name" in data:
            row.name = floor_name(data["name"])
        if "reveal_below" in data:
            if type(data["reveal_below"]) is not bool:
                fail("invalid_settings")
            row.reveal_below = data["reveal_below"]
        if "openings" in data:
            openings = data["openings"]
            if not isinstance(openings, list) or len(openings) > MAX_OPENINGS:
                fail("invalid_openings", 422)
            for rect in openings:
                if not isinstance(rect, dict) or set(rect) != {"x", "y", "width", "height"} or any(type(v) is not int for v in rect.values()):
                    fail("invalid_openings", 422)
                if rect["x"] < 0 or rect["y"] < 0 or rect["width"] <= 0 or rect["height"] <= 0 or rect["x"] + rect["width"] > row.width or rect["y"] + rect["height"] > row.height:
                    fail("invalid_openings", 422)
            row.openings = openings
        commit(deck, campaign_id, session_id)
    return jsonify(config(map_))


def download(row):
    try:
        raw = adapter(row.storage_provider).download(row.storage_key)
        if len(raw) != row.size_bytes or hashlib.sha256(raw).hexdigest() != row.png_sha256:
            fail("floor_source_unavailable", 503)
        return raw
    except LibraryError:
        raise
    except Exception:
        current_app.logger.exception("Private floor source unavailable")
        fail("floor_source_unavailable", 503)


@floor_layers_bp.get(BASE + "/maps/<int:map_id>/floors/<int:floor_id>/image")
@jwt_required()
def source_image(campaign_id, session_id, map_id, floor_id):
    ctx, error = context(campaign_id, session_id, dm=True)
    if error:
        return error
    map_for(ctx[1], map_id)
    row = MapFloorImage.query.filter_by(id=floor_id, map_id=map_id, deleted_at=None).first()
    if row is None:
        fail("not_found", 404)
    return send_file(BytesIO(download(row)), mimetype="image/png", max_age=0)


def composite(map_, deck, sources):
    size = map_world_size(map_)
    if size[0] > MAX_SIDE or size[1] > MAX_SIDE:
        fail("image_dimensions_mismatch", 503)
    active = next((index for index, row in enumerate(sources) if row.id == deck.active_floor_id), None)
    if active is None:
        fail("floor_source_unavailable", 503)
    surface = Image.new("RGBA", size, (0, 0, 0, 255))
    for row in sources[:active + 1]:
        if (row.width, row.height) != size:
            fail("image_dimensions_mismatch", 503)
        try:
            with Image.open(BytesIO(download(row))) as image:
                layer = image.convert("RGBA")
        except (OSError, ValueError):
            fail("floor_source_unavailable", 503)
        if not row.reveal_below:
            surface.paste((0, 0, 0, 255), (0, 0, *size))
        draw = ImageDraw.Draw(layer)
        for rect in row.openings:
            draw.rectangle((rect["x"], rect["y"], rect["x"] + rect["width"] - 1,
                            rect["y"] + rect["height"] - 1), fill=(0, 0, 0, 0))
        surface = Image.alpha_composite(surface, layer)
    return surface


@floor_layers_bp.get(BASE + "/floors/view")
@jwt_required()
@limiter.limit("60 per minute", key_func=lambda: str(get_jwt_identity()))
def floor_view(campaign_id, session_id):
    ctx, error = context(campaign_id, session_id)
    if error:
        return error
    user, campaign, session, role = ctx
    _, map_, error = _get_active_map_or_404(campaign, session)
    if error:
        return error
    deck = db.session.get(MapFloorDeck, map_.id)
    if not deck or not deck.enabled:
        return jsonify(enabled=False, map_id=map_.id)
    preview = request.args.get("token_id")
    if preview is not None and not is_operator_role(role):
        fail("forbidden", 403)
    tokens = TokenState.query.filter_by(campaign_id=campaign_id, game_session_id=session_id,
                                       map_id=map_.id, deleted_at=None).all()
    if preview is not None:
        try:
            chosen = int(preview)
        except (ValueError, TypeError):
            fail("invalid_token")
        tokens = [token for token in tokens if token.id == chosen]
        if not tokens:
            fail("not_found", 404)
    elif not is_operator_role(role):
        tokens = [token for token in tokens if token.owner_user_id == user.id and is_token_visible_to(token, role, user.id)]
    sources = rows(map_.id)
    surface = composite(map_, deck, sources)
    options = view_settings(map_.id)
    masked = not is_operator_role(role) or preview is not None
    if masked:
        walls = SceneWall.query.filter_by(campaign_map_id=map_.id).all()
        lights = SceneLight.query.filter_by(campaign_map_id=map_.id).all()
        projecting = map_.fog_enabled or options["dynamic_lighting"] and bool(lights or walls)
        if projecting:
            fog = None if preview is not None else FogOfWarState.query.filter_by(user_id=user.id, campaign_map_id=map_.id).first()
            overlay = render_overlay(*map_world_size(map_), walls, lights, tokens,
                                     ambient=options["ambient"] if options["dynamic_lighting"] else 100,
                                     explored=fog.explored_cells if fog else (), grid_size=map_.grid_size,
                                     fog_enabled=map_.fog_enabled)
            with Image.open(BytesIO(base64.b64decode(overlay.partition(",")[2]))) as image:
                darkness = image.convert("RGBA").resize(surface.size, Image.Resampling.BILINEAR)
            surface = Image.alpha_composite(surface, darkness)
    output = BytesIO()
    # Opaque final pixels: removing alpha/client overlays cannot recover secrets.
    surface.convert("RGB").save(output, format="PNG")
    png = output.getvalue()
    audience = json.dumps([campaign_id, session_id, map_.id, user.id, role,
                           g.table_context.id, preview, deck.revision, hashlib.sha256(png).hexdigest()])
    secret = str(current_app.config["SECRET_KEY"]).encode()
    key = hmac.new(secret, audience.encode(), hashlib.sha256).hexdigest()
    result = dict(enabled=True, map_id=map_.id, view_key=key, masked=masked,
                  name=next(row.name for row in sources if row.id == deck.active_floor_id))
    supplied_key = request.args.get("view_key", "")
    if re.fullmatch(r"[a-f0-9]{64}", supplied_key) and hmac.compare_digest(supplied_key, key):
        result["unchanged"] = True
    else:
        result["image"] = "data:image/png;base64," + base64.b64encode(png).decode()
    return jsonify(result)
