"""Private map library -> table snapshot (C04).

One operator-only, bounded multipart command. The browser renders the stored
project with the existing Mapmaker pipeline and uploads the resulting PNG; this
route only proves ownership/revision/dimensions, keeps the shared image as a new
campaign Asset and CampaignMap, and never exposes the private project source or
its storage keys. Scene-stack add/activate stay separate existing endpoints.
"""

from __future__ import annotations

from hashlib import sha256
import io
import re
import uuid

from flask import current_app, g, jsonify, request
from flask_jwt_extended import jwt_required
from PIL import Image
from werkzeug.datastructures import FileStorage

from vtt.endpoints.mapmaker import LibraryError, adjust_quota, cleanup
from vtt.extensions import db, limiter
from vtt.models import Asset, CampaignMap, User
from vtt.models.character_hotbar import TableRequestReceipt
from vtt.models.mapmaker_project import MapmakerProject
from vtt.play import play_bp
from vtt.play import contexts, receipts
from vtt.play.routes import _get_context
from vtt.play.service import is_operator_role
from vtt.storage import get_storage_adapter
from vtt.upload_security import MAX_FILE_SIZE_BYTES, UploadError, validate_upload
from vtt.utils.images import generate_thumbnail

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
OVERHEAD_BYTES = 64 * 1024
CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")
MAX_CREDITS = 600
OPERATION = "map-library-snapshot"


def _fail(code, status, message=None):
    return jsonify(error=code, **({"message": message} if message else {})), status


def _text(value, low, high):
    if not isinstance(value, str):
        return None
    value = CONTROL.sub("", value).strip()
    return value if low <= len(value) <= high else None


def _int(value, low, high):
    # Up to 10 digits so the whole approved range (revision <= 2**31 - 1) is accepted.
    if not isinstance(value, str) or not re.fullmatch(r"\d{1,10}", value.strip()):
        return None
    number = int(value)
    return number if low <= number <= high else None


def _parse_form():
    form = request.form
    try:
        project_id = str(uuid.UUID(form.get("project_id", "")))
    except ValueError:
        return None, "invalid_project_id"
    revision = _int(form.get("revision"), 1, 2**31 - 1)
    grid_size = _int(form.get("grid_size"), 16, 300)
    name = _text(form.get("name"), 1, 120)
    request_id = form.get("request_id")
    credits = _text(form.get("credits", ""), 0, MAX_CREDITS) if form.get("credits") else ""
    if revision is None:
        return None, "invalid_revision"
    if grid_size is None:
        return None, "invalid_grid_size"
    if name is None:
        return None, "invalid_name"
    if not isinstance(request_id, str) or not 8 <= len(request_id) <= 120:
        return None, "request_id_required"
    if credits is None:
        return None, "invalid_credits"
    return {"project_id": project_id, "revision": revision, "grid_size": grid_size,
            "name": name, "request_id": request_id, "credits": credits}, None


def _read_png(file_obj, project):
    if file_obj is None:
        return None, _fail("file_required", 400)
    data = file_obj.stream.read(MAX_FILE_SIZE_BYTES + 1)
    if len(data) > MAX_FILE_SIZE_BYTES:
        return None, _fail("file_too_large", 413)
    if not data.startswith(PNG_SIGNATURE):
        return None, _fail("invalid_png", 400)
    try:
        checked = validate_upload(FileStorage(io.BytesIO(data), filename="snapshot.png",
                                              content_type="image/png"), None, check_quota=False)
    except UploadError:
        return None, _fail("invalid_png", 400)
    if checked.get("mime_type") != "image/png":
        return None, _fail("invalid_png", 400)
    if (checked["width"], checked["height"]) != (project.width, project.height):
        return None, _fail("dimension_mismatch", 400,
                           "Das Bild passt nicht zur gespeicherten Karte.")
    try:
        with Image.open(io.BytesIO(data)) as image:
            image.load()
    except Exception:
        return None, _fail("invalid_png", 400)
    return checked, None


def _safe_filename(name):
    stem = re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip(".-_")[:80] or "karte"
    return stem + ".png"


def _reserve(user, size):
    if user.platform_role in ("admin", "owner"):
        return
    adjust_quota(user, size)


@play_bp.post("/campaigns/<int:campaign_id>/sessions/<int:session_id>/map-library-snapshots")
@limiter.limit("30 per hour")
@jwt_required()
def create_map_library_snapshot(campaign_id, session_id):
    user, campaign, game_session, role = _get_context(campaign_id, session_id)
    if isinstance(role, tuple):
        return role
    context = getattr(g, "table_context", None)
    # Campaign ownership never lifts a Player-mode context.
    if context is None or context.mode != "dm" or not is_operator_role(role):
        return _fail("forbidden", 403)
    if request.content_length is None or request.content_length > MAX_FILE_SIZE_BYTES + OVERHEAD_BYTES:
        return _fail("file_too_large", 413)

    fields, problem = _parse_form()
    if problem:
        return _fail(problem, 400)
    project = MapmakerProject.query.filter_by(id=fields["project_id"], owner_id=user.id).first()
    if project is None:
        return _fail("not_found", 404)
    checked, failure = _read_png(request.files.get("file"), project)
    if failure:
        return failure

    png_sha = sha256(checked["content"]).hexdigest()
    normalized = {k: fields[k] for k in ("project_id", "revision", "grid_size", "name", "credits")}
    normalized["png_sha256"] = png_sha
    receipt, replay = receipts.claim(context, fields["request_id"], OPERATION, normalized)
    if replay:
        payload, status = replay
        response = jsonify(payload)
        response.status_code = status
        response.headers["X-Request-Replayed"] = "true"
        return response

    storage = None
    keys = []
    committed = False
    try:
        # Existing personal writers lock the user row before touching a project.
        db.session.execute(db.update(User).where(User.id == user.id).values(
            storage_used_gb=db.func.coalesce(User.storage_used_gb, 0.0)))
        locked = db.session.get(User, user.id, populate_existing=True)
        if locked is None or not locked.is_usable():
            return _release(receipt, _fail("forbidden", 403))
        if not contexts.validate(context, locked.id, campaign.id, game_session.id):
            return _release(receipt, _fail("table_context_required", 403))
        project = MapmakerProject.query.filter_by(id=fields["project_id"], owner_id=locked.id).first()
        if project is None:
            return _release(receipt, _fail("not_found", 404))
        db.session.refresh(project)
        if project.revision != fields["revision"]:
            return _release(receipt, _fail(
                "revision_conflict", 409, "Diese Karte wurde inzwischen geändert. Bitte die Vorschau neu laden."))
        if (project.width, project.height) != (checked["width"], checked["height"]):
            return _release(receipt, _fail("dimension_mismatch", 400))
        try:
            _reserve(locked, checked["size_bytes"])
        except LibraryError:
            return _release(receipt, _fail("storage_quota_exceeded", 507,
                                           "Dein zugewiesener Speicherplatz reicht nicht aus."))

        storage = get_storage_adapter()
        base = f"campaigns/{campaign.id}/assets/library-{uuid.uuid4().hex}"
        file_key = base + "-" + _safe_filename(fields["name"])
        # Register the prospective key first: a write that stores bytes and then raises
        # must still be cleaned up by the failure path.
        keys.append(file_key)
        storage.upload(file_key, checked["content"])
        thumbnail_key = base + "-thumb.jpg"
        keys.append(thumbnail_key)
        try:
            storage.upload(thumbnail_key, generate_thumbnail(checked["content"]))
        except Exception:
            current_app.logger.warning("Map library thumbnail failed", exc_info=True)
            keys.remove(thumbnail_key)
            cleanup(storage, thumbnail_key)  # a partial write must not stay behind
            thumbnail_key = None

        asset = Asset(
            campaign_id=campaign.id, uploaded_by=locked.id, filename=_safe_filename(fields["name"]),
            mime_type="image/png", size_bytes=checked["size_bytes"],
            checksum_md5=checked["checksum_md5"], storage_key=file_key,
            storage_provider=current_app.config.get("STORAGE_PROVIDER", "local"),
            asset_type="map", scope="campaign", is_public=False, thumbnail_key=thumbnail_key)
        db.session.add(asset)
        db.session.flush()
        description = f"Schnappschuss aus der eigenen Kartenbibliothek: „{project.title}“, Revision {project.revision}."
        if fields["credits"]:
            description += "\nCredits: " + fields["credits"]
        campaign_map = CampaignMap(
            campaign_id=campaign.id, name=fields["name"], description=description,
            grid_type="square", grid_size=fields["grid_size"], width=checked["width"],
            height=checked["height"], background_url=f"/api/assets/{asset.id}/preview",
            fog_enabled=False, light_rules={}, created_by=locked.id)
        db.session.add(campaign_map)
        db.session.flush()
        payload = {"map_id": campaign_map.id, "asset_id": asset.id, "map": campaign_map.serialize(),
                   "width": checked["width"], "height": checked["height"],
                   "revision": project.revision}
        receipt.response = payload
        receipt.status_code = 201
        db.session.commit()
        committed = True
        response = jsonify(payload)
        response.status_code = 201
        response.headers["X-Request-ID"] = fields["request_id"]
        return response
    except Exception:
        current_app.logger.exception("Map library snapshot failed")
        db.session.rollback()
        # A failed commit may still have succeeded; only a completed receipt proves it.
        done = db.session.get(TableRequestReceipt, receipt.id, populate_existing=True) if receipt.id else None
        if done is not None and done.status_code is not None:
            committed = True
            response = jsonify(done.response)
            response.status_code = done.status_code
            return response
        return _release(receipt, _fail("storage_unavailable", 503,
                                       "Die Karte konnte nicht übernommen werden. Bitte erneut versuchen."))
    finally:
        if not committed and storage is not None:
            db.session.rollback()
            for key in keys:
                cleanup(storage, key)


def _release(receipt, response):
    """No side effect survived: free the claim so a corrected retry can run."""
    try:
        db.session.rollback()
        row = db.session.get(TableRequestReceipt, receipt.id)
        if row is not None and row.status_code is None:
            db.session.delete(row)
            db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Map library receipt release failed")
    return response
