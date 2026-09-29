"""Versioned VTT sheet adapter, separate from the frozen engine commands."""

from flask import jsonify, request
from vtt.creation_engine.canonical import parse_strict_json
from vtt.creation_engine.kernel.records import refuse
from vtt.creation_engine.store.race_sheets import RaceSheetService
from .authoring_http import service
from .common import principal
from .http import blueprint


@blueprint.get("/authoring/workspaces/<workspace_id>/sheets")
def sheet_catalog(workspace_id):
    return jsonify(RaceSheetService(service()).catalog(principal(), workspace_id))


@blueprint.post("/authoring/workspaces/<workspace_id>/sheets")
def apply_race(workspace_id):
    authoring = service()
    raw = request.stream.read(131073)
    if len(raw) > 131072:
        refuse("PAYLOAD_TOO_LARGE")
    return jsonify(RaceSheetService(authoring).apply(principal(), workspace_id, parse_strict_json(raw)))
