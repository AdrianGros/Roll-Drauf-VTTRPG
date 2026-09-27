"""Owner-only authoring reads. Mutations use the shared A1 /commands endpoint."""

from flask import current_app, jsonify, render_template, request

from vtt.creation_engine.kernel.records import refuse
from .common import authoring, gateway, principal
from .http import blueprint, view_id


def service():
    if view_id() is not None:
        refuse("OPERATION_FORBIDDEN")
    return authoring()


@blueprint.get("/authoring")
def editor():
    service().workspace(principal())
    return render_template("creation-engine.html")


@blueprint.get("/authoring/workspace")
def workspace():
    return jsonify(service().workspace(principal()))


@blueprint.get("/authoring/workspaces/<workspace_id>/drafts/<draft_id>")
def draft(workspace_id, draft_id):
    return jsonify(service().read(principal(), workspace_id, draft_id,
        locale=request.args.get("locale", "de"), mode=request.args.get("mode", "guided")))


@blueprint.get("/authoring/workspaces/<workspace_id>/drafts/<draft_id>/history")
def history(workspace_id, draft_id):
    return jsonify(service().history(principal(), workspace_id, draft_id))


@blueprint.get("/authoring/workspaces/<workspace_id>/presets/<preset_id>")
def preview(workspace_id, preset_id):
    return jsonify(service().preview(principal(), workspace_id, preset_id, locale=request.args.get("locale", "de")))


@blueprint.get("/authoring/workspaces/<workspace_id>/commands/<key>")
def workspace_result(workspace_id, key):
    return jsonify(service().command_result(principal(), workspace_id, key))


@blueprint.get("/authoring/workspaces/<workspace_id>/drafts/<draft_id>/commands/<key>")
def draft_result(workspace_id, draft_id, key):
    return jsonify(service().command_result(principal(), workspace_id, key, draft_id=draft_id))


def native_service():
    service()
    host = gateway()
    if not hasattr(host.kernel, "native"):
        refuse("NOT_FOUND")
    return host, host.kernel.native


@blueprint.get("/authoring/sandboxes")
def sandbox_catalog():
    host, native = native_service()
    return jsonify({**native.catalog(principal()), "runtimeEnabled": bool(current_app.config.get("CE_RUNTIME"))})


@blueprint.get("/authoring/sandboxes/<scope_id>")
def sandbox(scope_id):
    host, native = native_service()
    return jsonify(native.summary(host, principal(), scope_id))
