"""Authenticated backend-only homebrew test adapter; all scopes are private."""

from flask import jsonify, request

from vtt.creation_engine.canonical import parse_strict_json
from vtt.creation_engine.kernel.records import refuse
from vtt.creation_engine.store.homebrew import HomebrewService
from .authoring_http import service
from .common import principal
from .http import blueprint


@blueprint.get("/authoring/workspaces/<workspace_id>/homebrew")
def homebrew_catalog(workspace_id):
    return jsonify(HomebrewService(service()).catalog(principal(), workspace_id))


@blueprint.post("/authoring/workspaces/<workspace_id>/homebrew/commands")
def homebrew_command(workspace_id):
    adapter = HomebrewService(service())
    raw = request.stream.read(262145)
    if len(raw) > 262144:
        refuse("PAYLOAD_TOO_LARGE")
    return jsonify(adapter.submit(principal(), workspace_id, parse_strict_json(raw)))


@blueprint.get("/authoring/workspaces/<workspace_id>/homebrew/sandboxes/<sandbox_id>")
def homebrew_sandbox(workspace_id, sandbox_id):
    return jsonify(HomebrewService(service()).read(principal(), workspace_id, sandbox_id))


@blueprint.get("/authoring/workspaces/<workspace_id>/homebrew/sandboxes/<sandbox_id>/history")
def homebrew_history(workspace_id, sandbox_id):
    raw = request.args.get("after", "0")
    if not raw.isascii() or not raw.isdecimal() or len(raw) > 16:
        refuse("SCHEMA_INVALID")
    return jsonify(HomebrewService(service()).history(principal(), workspace_id, sandbox_id, after=int(raw)))
