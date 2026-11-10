"""Creation Engine companion for Species: playability check and publication as a playable 2024 origin.

Lives beside the Flight Control contract (routes.py) on the same blueprint, so CE_AUTHORING still gates it;
CE_PLAYABLE_SPECIES gates it in addition. These are VTT endpoints, answered with HTTP status codes.
Reads use the author's current rights on the Eagle document (world they lead, or their own Library).
"""

import copy

from flask import current_app, jsonify, request
from sqlalchemy import and_, or_
from sqlalchemy.exc import IntegrityError

from vtt.extensions import db, limiter
from vtt.rules_content.creator_rules import load_creator_data

from . import species as conversion
from .canonical import content_digest
from .documents import RequestFailure
from .errors import ContractViolation
from .models import CeSpeciesRevision
from .routes import blueprint, current_user, find, led_campaigns, read_failure, resolve_world, scope_of

MAX_SPECIES_BODY = 70_000


def _error(code, detail, status, **extra):
    return jsonify({"error": code, "detail": detail, **extra}), status


def _skills():
    return {skill["id"]: skill["name"] for skill in load_creator_data()["skills"]}


def _request_source(user, body):
    """(row, error response) for the Eagle Species named by body.world/body.uuid."""
    try:
        world = resolve_world(user, body.get("world"))
        scope, document_name, document_id = scope_of(user, world, body.get("uuid"))
    except RequestFailure as failure:
        return None, read_failure(failure)
    row = find(scope, document_name, document_id)
    if row is None:
        return None, _error("not-found", "Dokument nicht gefunden.", 404)
    if row.doc_type != "race":
        return None, _error("not-species", "Nur Spezies können als spielbare Herkunft geprüft werden.", 422)
    return row, None


def _body():
    if not current_app.config.get("CE_PLAYABLE_SPECIES"):
        return None, _error("not-found", "Spielbare Spezies sind nicht eingeschaltet.", 404)
    if (request.content_length or 0) > MAX_SPECIES_BODY:
        return None, _error("too-large", "Anfrage zu groß.", 413)
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return None, _error("invalid-request", "JSON-Objekt erwartet.", 400)
    return body, None


def _lineage(row, user=None):
    source = f"{row.scope_kind}:{row.scope_id}:{row.uuid}"
    return f"author:{user.id}:{source}" if user is not None else source


def _digest(row):
    try:
        return content_digest(row.source)
    except ContractViolation as exc:
        raise RequestFailure("invalid-payload", f"Das Dokument ist kein kanonisches JSON: {exc.detail}") from None


def _lead_scopes(user):
    return [("personal", user.id)] + [("campaign", campaign.id) for campaign in led_campaigns(user)]


def _publications(user, source=None):
    scopes = [
        and_(CeSpeciesRevision.scope_kind == kind, CeSpeciesRevision.scope_id == scope_id)
        for kind, scope_id in _lead_scopes(user)
    ]
    scopes.append(and_(CeSpeciesRevision.scope_kind == "global", CeSpeciesRevision.scope_id == 0,
                       CeSpeciesRevision.published_by == user.id))
    query = CeSpeciesRevision.query.filter(or_(*scopes))
    if source is not None:
        query = query.filter(CeSpeciesRevision.lineage.in_((_lineage(source), _lineage(source, user))))
    rows = query.order_by(CeSpeciesRevision.id.desc()).limit(200).all()
    return [{**row.summary(), "lineage": row.lineage, "supplement": row.supplement} for row in rows]


@blueprint.post("/authoring/species/check")
@limiter.limit("240 per hour")
def species_check():
    user = current_user()
    body, error = _body()
    if error:
        return error
    row, error = _request_source(user, body)
    if error:
        return error
    try:
        digest = _digest(row)
    except RequestFailure as failure:
        return _error(failure.reason, failure.detail, 422)
    result = conversion.inspect(row.source, body.get("supplement"), skills=_skills(), pack=row.pack)
    return jsonify({
        "source": {"uuid": row.uuid, "name": row.name, "revision": row.revision, "digest": digest},
        "report": {"playable": result["playable"], "edition": result["edition"], "entries": result["entries"]},
        "profile": result["profile"],
        "publications": _publications(user, row),
    })


@blueprint.post("/authoring/species/publish")
@limiter.limit("60 per hour")
def species_publish():
    user = current_user()
    body, error = _body()
    if error:
        return error
    row, error = _request_source(user, body)
    if error:
        return error
    try:
        digest = _digest(row)
        target = body.get("scope") or body.get("world")
        kind, scope_id = ("global", 0) if target == "global" else resolve_world(user, target)
    except RequestFailure as failure:
        return read_failure(failure)
    if body.get("expectedDigest") != digest:
        return _error("source-changed", "Die Spezies wurde seit der Prüfung geändert. Prüfe sie erneut und veröffentliche dann.",
                      409, sourceDigest=digest)
    supplement = body.get("supplement") if body.get("supplement") is not None else {}
    result = conversion.inspect(row.source, supplement, skills=_skills(), pack=row.pack)
    report = {"playable": result["playable"], "edition": result["edition"], "entries": result["entries"]}
    if not result["playable"]:
        return _error("not-playable", "Die Spezies ist noch nicht spielbar; siehe die blockierenden Punkte.", 422, report=report)
    profile_digest = content_digest(result["profile"])
    lineage = _lineage(row, user if kind == "global" else None)
    latest = (CeSpeciesRevision.query.filter_by(scope_kind=kind, scope_id=scope_id, lineage=lineage)
              .order_by(CeSpeciesRevision.revision_number.desc()).first())
    if latest is not None and latest.profile_digest == profile_digest and latest.source_digest == digest and latest.supplement == supplement:
        return jsonify({"created": False, "revision": latest.summary(), "report": report})
    revision = CeSpeciesRevision(
        scope_kind=kind, scope_id=scope_id, lineage=lineage,
        revision_number=(latest.revision_number if latest else 0) + 1,
        name=result["profile"]["name"], edition=result["edition"], source_uuid=row.uuid,
        source_revision=row.revision, source_digest=digest, source=copy.deepcopy(row.source),
        supplement=copy.deepcopy(supplement), profile=result["profile"], profile_digest=profile_digest,
        report=result["entries"], published_by=user.id,
    )
    db.session.add(revision)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return _error("publish-conflict", "Gleichzeitig wurde eine andere Fassung veröffentlicht. Bitte erneut versuchen.", 409)
    return jsonify({"created": True, "revision": revision.summary(), "report": report}), 201


@blueprint.get("/authoring/species/publications")
def species_publications():
    user = current_user()
    if not current_app.config.get("CE_PLAYABLE_SPECIES"):
        return _error("not-found", "Spielbare Spezies sind nicht eingeschaltet.", 404)
    return jsonify({"publications": _publications(user)})
