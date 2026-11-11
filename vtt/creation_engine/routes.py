"""Creation Engine HTTP surface: the page hosting Eagle Homebrew and the Flight Control request contract.

The editor (vendor/eagle-homebrew, built by frontend/eagle-homebrew-host) sends exactly the requests it sends
to Eagle Flight Control in Foundry. Contract failures are answered as Flight Control answers them,
`{"ok": false, "reason", "detail"}` with HTTP 200, because the editor treats them as outcomes, not transport
errors. Only authentication and account problems use HTTP status codes.
"""

import copy
import re

from flask import Blueprint, current_app, jsonify, redirect, render_template, request
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from flask_jwt_extended.exceptions import JWTExtendedException
from jwt import PyJWTError
from sqlalchemy import func

from vtt.extensions import db
from vtt.models import Campaign, CampaignMember, User

from . import documents as rules
from .capability import account_usable
from .documents import RequestFailure, fail
from .models import CeEagleDocument

blueprint = Blueprint("creation_engine", __name__)

PERSONAL_WORLD = "personal"
WORLD_PATTERN = re.compile(r"^campaign:(\d{1,10})$")
# The VTT's rules corpus is SRD 5.2.1, so new documents default to dnd5e's "modern" (2024) rules,
# the same value Foundry's dnd5e setting holds by default.
RULES_VERSION = "modern"
MAX_BODY_BYTES = rules.MAX_DOCUMENT_BYTES + rules.MAX_REQUEST_BYTES
MAX_IMPORT_SOURCES = 50


class Unauthorized(Exception):
    pass


@blueprint.before_request
def engine_enabled():
    # CE_AUTHORING is read per request, so the switch works without re-creating the app.
    if not current_app.config.get("CE_AUTHORING"):
        return jsonify({"error": "not found"}), 404
    return None


@blueprint.after_request
def private_response(response):
    response.headers["Cache-Control"] = "private, no-store"
    return response


@blueprint.errorhandler(Unauthorized)
def unauthorized(_exc):
    return jsonify({"error": "unauthorized"}), 401


def current_user(*, optional=False):
    try:
        verify_jwt_in_request(optional=optional)
        identity = get_jwt_identity()
    except (JWTExtendedException, PyJWTError):
        identity = None
    try:
        user = db.session.get(User, int(identity)) if identity is not None else None
    except (TypeError, ValueError):
        user = None
    if user is None or not account_usable(user):
        if optional:
            return None
        raise Unauthorized()
    return user


def leads_campaign(campaign, user_id):
    if campaign.owner_id == user_id:
        return True
    member = CampaignMember.query.filter_by(campaign_id=campaign.id, user_id=user_id, status="active").first()
    return bool(member) and str(member.campaign_role).strip().upper() in {"DM", "CO_DM", "CODM"}


def led_campaigns(user):
    owned = Campaign.query.filter(Campaign.owner_id == user.id, Campaign.deleted_at.is_(None)).all()
    led = (Campaign.query.join(CampaignMember, CampaignMember.campaign_id == Campaign.id)
           .filter(CampaignMember.user_id == user.id, CampaignMember.status == "active",
                   func.upper(CampaignMember.campaign_role).in_(["DM", "CO_DM", "CODM"]),
                   Campaign.deleted_at.is_(None)).all())
    unique = {campaign.id: campaign for campaign in [*owned, *led]}
    return sorted(unique.values(), key=lambda campaign: (campaign.name or "").lower())


def resolve_world(user, raw):
    """(scope_kind, scope_id) of the world the editor works in; the user must lead it."""
    if raw in (None, "", PERSONAL_WORLD):
        return "personal", user.id
    match = WORLD_PATTERN.match(raw) if isinstance(raw, str) else None
    if not match:
        fail("invalid-request", "unknown world")
    campaign = db.session.get(Campaign, int(match.group(1)))
    if campaign is None or campaign.deleted_at is not None or not leads_campaign(campaign, user.id):
        fail("not-permitted", "only the campaign's game masters can create its homebrew")
    return "campaign", campaign.id


def scope_of(user, world, uuid):
    side, pack, document_name, document_id = rules.parse_uuid(uuid)
    if side == "library":
        return ("library", user.id, pack), document_name, document_id
    return (*world, ""), document_name, document_id


def find(scope, document_name, document_id):
    kind, scope_id, pack = scope
    return CeEagleDocument.query.filter_by(scope_kind=kind, scope_id=scope_id, pack=pack,
                                           document_name=document_name, document_id=document_id).first()


def within_quota(kind, scope_id):
    count = CeEagleDocument.query.filter_by(scope_kind=kind, scope_id=scope_id).count()
    if count >= rules.MAX_DOCUMENTS_PER_SCOPE:
        fail("not-permitted", f"at most {rules.MAX_DOCUMENTS_PER_SCOPE} documents per Library or world")


def allowed_subtypes(document_name):
    return {subtype for name, subtype, _ in rules.CATALOG.values() if name == document_name}


def store(user, scope, document_name, document_id, source):
    kind, scope_id, pack = scope
    within_quota(kind, scope_id)
    row = CeEagleDocument(scope_kind=kind, scope_id=scope_id, pack=pack, document_name=document_name,
                          document_id=document_id, doc_type=source.get("type"), name=source["name"],
                          source=source, created_by=user.id, updated_by=user.id)
    db.session.add(row)
    db.session.flush()
    return row


def exact(payload, keys):
    if not isinstance(payload, dict) or set(payload) != set(keys):
        fail("invalid-payload", f"payload must have exactly {', '.join(keys)}")
    return payload


def document_create(user, world, payload):
    exact(payload, ("target", "id", "data"))
    target, document_id, data = payload["target"], rules.check_id(payload["id"]), payload["data"]
    rules.check_json(data)
    if not isinstance(target, dict) or len(target) != 1:
        fail("invalid-payload", "target must name one pack or one world document type")
    if "pack" in target:
        _, document_name, subtype = rules.pack_entry(target["pack"])
        scope = ("library", user.id, target["pack"])
    elif target.get("world") in rules.DOCUMENT_NAMES:
        document_name = target["world"]
        subtype = data.get("type") if isinstance(data, dict) else None
        if subtype not in allowed_subtypes(document_name):
            fail("invalid-payload", f"{document_name} type {str(subtype)[:40]} is not supported")
        scope = (*world, "")
    else:
        fail("invalid-payload", "unknown target")
    source = {**copy.deepcopy(data), "_id": document_id}
    rules.check_document(source, document_name, subtype)
    existing = find(scope, document_name, document_id)
    if existing is not None:
        return {"created": False, "uuid": existing.uuid}
    return {"created": True, "uuid": store(user, scope, document_name, document_id, source).uuid}


def document_update(user, world, payload):
    exact(payload, ("uuid", "changes"))
    scope, document_name, document_id = scope_of(user, world, payload["uuid"])
    row = find(scope, document_name, document_id)
    if row is None:
        fail("invalid-payload", "document not found")
    source = copy.deepcopy(row.source)
    changed = rules.apply_update(source, payload["changes"])
    subtype = source.get("type") if document_name != "RollTable" else None
    rules.check_document(source, document_name, subtype)
    row.source = source
    row.name = source["name"]
    row.revision += 1
    row.updated_by = user.id
    return {"uuid": row.uuid, "changed": changed}


def compendium_import(user, world, payload):
    exact(payload, ("pack", "sources"))
    pack, sources = payload["pack"], payload["sources"]
    _, document_name, subtype = rules.pack_entry(pack)
    if not isinstance(sources, list) or not 1 <= len(sources) <= MAX_IMPORT_SOURCES:
        fail("invalid-payload", f"sources must hold 1-{MAX_IMPORT_SOURCES} entries")
    created, existed = [], []
    for entry in sources:
        if not isinstance(entry, dict) or not {"source", "id"} <= set(entry) <= {"source", "id", "changes"}:
            fail("invalid-payload", "each source needs source and id")
        side, _, source_name, source_id = rules.parse_uuid(entry["source"])
        if side != "world" or source_name != document_name or rules.check_id(entry["id"]) != source_id:
            fail("invalid-payload", "only a world document can be imported, under its own id")
        world_row = find((*world, ""), source_name, source_id)
        if world_row is None:
            fail("invalid-payload", "world document not found")
        if subtype is not None and world_row.doc_type != subtype:
            fail("invalid-payload", f"{world_row.doc_type} does not belong in {pack}")
        scope = ("library", user.id, pack)
        existing = find(scope, document_name, source_id)
        if existing is not None:
            existed.append({"uuid": existing.uuid})
            continue
        source = copy.deepcopy(world_row.source)
        if entry.get("changes"):
            rules.apply_update(source, entry["changes"])
        rules.check_document(source, document_name, subtype)
        created.append({"uuid": store(user, scope, document_name, source_id, source).uuid})
    return {"created": created, "existed": existed}


HANDLERS = {"document.create": document_create, "document.update": document_update,
            "compendium.import": compendium_import}


@blueprint.get("/authoring")
def editor_page():
    if current_user(optional=True) is None:
        return redirect("/login.html?next=/api/ce/authoring")
    return render_template("creation-engine.html")


@blueprint.get("/authoring/worlds")
def worlds():
    user = current_user()
    return jsonify({
        "rulesVersion": RULES_VERSION,
        "worlds": [{"id": PERSONAL_WORLD, "label": "Persönliche Werkstatt", "kind": "personal"},
                   *({"id": f"campaign:{campaign.id}", "label": campaign.name, "kind": "campaign"}
                     for campaign in led_campaigns(user))],
    })


@blueprint.post("/authoring/request")
def submit():
    user = current_user()
    if (request.content_length or 0) > MAX_BODY_BYTES:
        return jsonify({"ok": False, "reason": "invalid-request", "detail": "request too large"})
    body = request.get_json(silent=True)
    if not isinstance(body, dict) or set(body) != {"world", "type", "payload"}:
        return jsonify({"ok": False, "reason": "invalid-request", "detail": "expected world, type and payload"})
    handler = HANDLERS.get(body["type"])
    if handler is None:
        return jsonify({"ok": False, "reason": "unknown-request", "detail": str(body["type"])[:80]})
    try:
        world = resolve_world(user, body["world"])
        value = handler(user, world, body["payload"])
        db.session.commit()
    except RequestFailure as failure:
        db.session.rollback()
        return jsonify({"ok": False, "reason": failure.reason, "detail": failure.detail})
    return jsonify({"ok": True, "value": value})


def read_failure(failure):
    status = 403 if failure.reason == "not-permitted" else 400
    return jsonify({"error": failure.reason, "detail": failure.detail}), status


@blueprint.get("/authoring/index")
def pack_index():
    user = current_user()
    try:
        pack = request.args.get("pack", "")
        rules.pack_entry(pack)
    except RequestFailure as failure:
        return read_failure(failure)
    rows = CeEagleDocument.query.filter_by(scope_kind="library", scope_id=user.id, pack=pack).all()
    return jsonify({"index": [rules.index_row(row.source) for row in rows]})


@blueprint.get("/authoring/document")
def read_document():
    user = current_user()
    try:
        world = resolve_world(user, request.args.get("world"))
        scope, document_name, document_id = scope_of(user, world, request.args.get("uuid"))
    except RequestFailure as failure:
        return read_failure(failure)
    row = find(scope, document_name, document_id)
    return jsonify({"document": {**row.summary(), "source": row.source} if row else None})


@blueprint.get("/authoring/documents")
def list_documents():
    """World documents plus the user's Library: the VTT's stand-in for Foundry's sidebar and compendia."""
    user = current_user()
    try:
        kind, scope_id = resolve_world(user, request.args.get("world"))
    except RequestFailure as failure:
        return read_failure(failure)
    names = [name for name in request.args.getlist("documentName") if name in rules.DOCUMENT_NAMES] or list(rules.DOCUMENT_NAMES)
    world_rows = CeEagleDocument.query.filter(CeEagleDocument.scope_kind == kind, CeEagleDocument.scope_id == scope_id,
                                              CeEagleDocument.document_name.in_(names))
    library_rows = CeEagleDocument.query.filter(CeEagleDocument.scope_kind == "library", CeEagleDocument.scope_id == user.id,
                                                CeEagleDocument.document_name.in_(names))
    order = lambda row: (row.document_name, (row.name or "").lower())  # noqa: E731
    return jsonify({"world": [row.summary() for row in sorted(world_rows, key=order)],
                    "library": [row.summary() for row in sorted(library_rows, key=order)]})


@blueprint.delete("/authoring/document")
def delete_document():
    user = current_user()
    try:
        world = resolve_world(user, request.args.get("world"))
        scope, document_name, document_id = scope_of(user, world, request.args.get("uuid"))
    except RequestFailure as failure:
        return read_failure(failure)
    row = find(scope, document_name, document_id)
    if row is None:
        return jsonify({"error": "not found"}), 404
    db.session.delete(row)
    db.session.commit()
    return jsonify({"deleted": row.uuid})


from . import species_routes  # noqa: E402,F401  (registers the Species check/publish routes on this blueprint)

from . import origin_routes  # noqa: E402,F401
