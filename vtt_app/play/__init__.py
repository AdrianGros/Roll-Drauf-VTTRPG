"""Play runtime blueprint."""

from flask import Blueprint

play_bp = Blueprint("play", __name__)

from vtt_app.play.routes import *  # noqa: F401,F403

__all__ = ["play_bp"]
