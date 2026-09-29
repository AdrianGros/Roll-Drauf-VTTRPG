"""Power-user document adapter over private drafts; no new core commands."""

from flask import jsonify, render_template, request

from vtt.creation_engine.canonical import parse_strict_json
from vtt.creation_engine.kernel.records import refuse
from vtt.creation_engine.store.advanced import AdvancedService
from .authoring_http import service
from .common import principal
from .http import blueprint


@blueprint.get("/authoring/advanced")
def advanced_editor():
    service().workspace(principal())
    return render_template("creation-advanced.html")


@blueprint.get("/authoring/advanced/workspace")
def advanced_workspace():
    return jsonify(AdvancedService(service()).workspace(principal()))


@blueprint.get("/authoring/workspaces/<workspace_id>/drafts/<draft_id>/document")
def advanced_document(workspace_id, draft_id):
    return jsonify(AdvancedService(service()).read(principal(), workspace_id, draft_id,
                   locale=request.args.get("locale", "en")))


def document_payload():
    raw = request.stream.read(262145)
    if len(raw) > 262144:
        refuse("PAYLOAD_TOO_LARGE")
    return parse_strict_json(raw)


@blueprint.post("/authoring/workspaces/<workspace_id>/drafts/<draft_id>/document/validate")
def validate_document(workspace_id, draft_id):
    adapter = AdvancedService(service())
    return jsonify(adapter.validate(principal(), workspace_id, draft_id, document_payload()))


@blueprint.post("/authoring/workspaces/<workspace_id>/drafts/<draft_id>/document")
def save_document(workspace_id, draft_id):
    adapter = AdvancedService(service())
    return jsonify(adapter.save(principal(), workspace_id, draft_id, document_payload()))
