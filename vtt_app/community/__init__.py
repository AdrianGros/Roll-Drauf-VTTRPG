"""Community blueprint for chat, reporting, and moderation endpoints."""

from flask import Blueprint

community_bp = Blueprint("community", __name__)

from vtt_app.community.routes import *  # noqa: F401,F403

__all__ = ["community_bp"]
