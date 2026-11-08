"""Personal map library. Ownership is independent of campaigns/table roles."""

from datetime import datetime
import json
import uuid

from flask import Blueprint, current_app, g, jsonify, request
from flask_jwt_extended import jwt_required

from vtt.extensions import db
from vtt.mapmaker_document import InvalidDocument, MAX_PROJECT_BYTES, normalize_document
from vtt.models.mapmaker_project import MapmakerProject
from vtt.models.user import User
from vtt.security import current_user
from vtt.storage import get_storage_adapter

mapmaker_bp = Blueprint("mapmaker", __name__)
GIB = 1024**3


class LibraryError(Exception):
    def __init__(self, message, status, code):
        super().__init__(message)
        self.status, self.code = status, code


@mapmaker_bp.before_request
@jwt_required()
def authorize():
    if not current_user:
        raise LibraryError("Bitte erneut anmelden.", 401, "authentication_required")
    g.mapmaker_user_id = current_user.id
    expected = request.headers.get("X-Mapmaker-Account")
    if (expected is not None and expected != str(g.mapmaker_user_id)) or (
            request.method != "GET" and expected is None):
        raise LibraryError("Das angemeldete Konto hat sich geändert. Bitte die Kartenwerkstatt neu öffnen.", 409, "account_changed")


@mapmaker_bp.after_request
def private_response(response):
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@mapmaker_bp.errorhandler(LibraryError)
def library_error(error):
    db.session.rollback()
    return jsonify(error=str(error), code=error.code), error.status


def lock_user():
    # UPDATE takes the same row lock as existing asset reservations, including
    # SQLite tests; no intermediate commit or stale ORM read of the usage counter.
    db.session.execute(db.update(User).where(User.id == g.mapmaker_user_id).values(
        storage_used_gb=db.func.coalesce(User.storage_used_gb, 0.0)))
    user = db.session.get(User, g.mapmaker_user_id, populate_existing=True)
    if user is None or not user.is_usable():
        raise LibraryError("Bitte erneut anmelden.", 401, "authentication_required")
    return user


def unlimited(user):
    return user.platform_role in ("admin", "owner") or (user.profile_tier == "headmaster" and user.storage_quota_gb is None)


def usage(user):
    cap = None if unlimited(user) else max(0, user.storage_quota_gb or 0) * GIB
    library_bytes = db.session.query(db.func.coalesce(db.func.sum(MapmakerProject.size_bytes), 0)).filter(
        MapmakerProject.owner_id == user.id).scalar()
    return {"accountId": user.id, "usedBytes": round((user.storage_used_gb or 0) * GIB),
            "libraryBytes": int(library_bytes), "quotaBytes": cap, "unlimited": cap is None}


def own_project(project_id):
    project = MapmakerProject.query.filter_by(id=project_id, owner_id=g.mapmaker_user_id).first()
    if project is None:
        raise LibraryError("Karte nicht gefunden.", 404, "not_found")
    return project


def payload():
    if request.content_length is not None and request.content_length > MAX_PROJECT_BYTES + 4096:
        raise LibraryError("Das Kartenprojekt ist größer als 50 MiB.", 413, "project_too_large")
    try:
        data = request.get_json(silent=True)
    except (RecursionError, ValueError):
        raise LibraryError("Ungültiges Kartenprojekt.", 400, "invalid_document")
    if not isinstance(data, dict):
        raise LibraryError("Kartenprojekt als JSON erwartet.", 400, "invalid_document")
    return data


def check_revision(project, data):
    if type(data.get("revision")) is not int or data["revision"] != project.revision:
        raise LibraryError("Diese Karte wurde inzwischen geändert. Öffne den aktuellen Stand oder speichere deine Änderungen als Kopie.", 409, "revision_conflict")


def adjust_quota(user, delta):
    used = user.storage_used_gb or 0
    if delta > 0 and not unlimited(user) and (
            not user.storage_quota_gb or user.storage_quota_gb <= 0 or used + delta/GIB > user.storage_quota_gb):
        raise LibraryError("Dein zugewiesener Speicherplatz reicht nicht aus. Lösche eine eigene Karte oder sichere das Projekt als Datei.", 507, "storage_quota_exceeded")
    user.storage_used_gb = max(0.0, used + delta/GIB)


def cleanup(storage, key):
    try:
        storage.delete(key)
    except Exception:
        current_app.logger.exception("Mapmaker storage cleanup failed")


def adapter(provider=None):
    if provider and provider != current_app.config.get("STORAGE_PROVIDER", "local"):
        raise LibraryError("Der Speicheranbieter dieser Karte ist momentan nicht verfügbar.", 503, "storage_unavailable")
    return get_storage_adapter()


@mapmaker_bp.get("/projects")
def list_projects():
    try:
        page = max(1, min(1000000, int(request.args.get("page", 1))))
    except (ValueError, TypeError):
        raise LibraryError("Ungültige Seite.", 400, "invalid_page")
    search = (request.args.get("q") or "").strip()[:80]
    query = MapmakerProject.query.filter_by(owner_id=g.mapmaker_user_id)
    if search:
        query = query.filter(MapmakerProject.title.ilike("%" + search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%", escape="\\"))
    total = query.count()
    projects = query.order_by(MapmakerProject.updated_at.desc(), MapmakerProject.id).offset((page-1)*24).limit(24).all()
    user = db.session.get(User, g.mapmaker_user_id)
    return jsonify(projects=[p.serialize() for p in projects], total=total, page=page, pageSize=24, storage=usage(user))


@mapmaker_bp.get("/projects/<uuid:project_id>")
def get_project(project_id):
    try:
        lock_user()
        project = own_project(str(project_id))
        document = adapter(project.storage_provider).download(project.storage_key)
        return jsonify(project=project.serialize(), document=json.loads(document))
    except LibraryError:
        raise
    except Exception:
        current_app.logger.exception("Mapmaker project read failed")
        raise LibraryError("Die gespeicherte Karte konnte nicht geladen werden. Bitte erneut versuchen.", 503, "storage_unavailable")
    finally:
        db.session.rollback()


@mapmaker_bp.post("/projects")
@mapmaker_bp.put("/projects/<uuid:project_id>")
def save_project(project_id=None):
    data = payload()
    # Avoid expensive document parsing for a guessed foreign project ID.
    if project_id is not None:
        own_project(str(project_id))
    try:
        document, encoded = normalize_document(data.get("document"))
    except (InvalidDocument, OverflowError, RecursionError, UnicodeError) as error:
        raise LibraryError(str(error), 400, "invalid_document")
    new_key = None
    storage = None
    committed = False
    try:
        user = lock_user()
        project = own_project(str(project_id)) if project_id else None
        if project:
            # Refresh after the user lock; another save may have committed while
            # validation ran. All personal writers lock user before the project.
            db.session.refresh(project)
            check_revision(project, data)
        old_key = project.storage_key if project else None
        old_provider = project.storage_provider if project else None
        adjust_quota(user, len(encoded) - (project.size_bytes if project else 0))
        identity = str(project_id) if project else str(uuid.uuid4())
        provider = current_app.config.get("STORAGE_PROVIDER", "local")
        storage = adapter(provider)
        new_key = f"users/{user.id}/mapmaker/{identity}/{uuid.uuid4()}.json"
        storage.upload(new_key, encoded)
        if project is None:
            project = MapmakerProject(id=identity, owner_id=user.id, revision=0)
            db.session.add(project)
        project.title = document["meta"]["title"]
        project.width, project.height = document["size"]["w"], document["size"]["h"]
        project.revision += 1
        project.size_bytes, project.storage_key, project.storage_provider = len(encoded), new_key, provider
        project.updated_at = datetime.utcnow()
        db.session.flush()
        response = {"project": project.serialize(), "storage": usage(user)}
        db.session.commit()
        committed = True
        if old_key:
            try:
                cleanup(adapter(old_provider), old_key)
            except Exception:
                current_app.logger.exception("Mapmaker previous provider cleanup failed")
        return jsonify(response), 200 if project_id else 201
    except LibraryError:
        raise
    except Exception:
        current_app.logger.exception("Mapmaker project save failed")
        raise LibraryError("Speichern momentan nicht möglich. Der letzte gespeicherte Stand bleibt erhalten.", 503, "storage_unavailable")
    finally:
        if not committed:
            db.session.rollback()
            if new_key and storage:
                cleanup(storage, new_key)


@mapmaker_bp.delete("/projects/<uuid:project_id>")
def delete_project(project_id):
    data = payload()
    try:
        user = lock_user()
        project = own_project(str(project_id))
        check_revision(project, data)
        storage, key = adapter(project.storage_provider), project.storage_key
        adjust_quota(user, -project.size_bytes)
        db.session.delete(project)
        db.session.flush()
        response = {"storage": usage(user)}
        db.session.commit()
    except LibraryError:
        raise
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Mapmaker project delete failed")
        raise LibraryError("Löschen momentan nicht möglich. Bitte erneut versuchen.", 503, "storage_unavailable")
    cleanup(storage, key)
    return jsonify(response)
