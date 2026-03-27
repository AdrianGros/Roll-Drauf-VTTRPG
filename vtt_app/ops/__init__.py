"""Operational endpoints blueprint (health, readiness, metrics)."""

from flask import Blueprint

ops_bp = Blueprint("ops", __name__)

from vtt_app.ops.routes import *  # noqa: F401,F403

__all__ = ["ops_bp"]
