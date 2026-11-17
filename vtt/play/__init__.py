"""Play runtime blueprint."""

from flask import Blueprint

play_bp = Blueprint("play", __name__)

from vtt.play.routes import *  # noqa: F401,F403
from vtt.play import presentation  # noqa: F401,E402
from vtt.play import personal_actions  # noqa: F401,E402
from vtt.play import map_library  # noqa: F401,E402
from vtt.play import token_library, rolls  # noqa: F401,E402

__all__ = ["play_bp"]

from vtt.play import scene_settings  # noqa: F401,E402
from vtt.play import lighting_routes  # noqa: F401,E402
