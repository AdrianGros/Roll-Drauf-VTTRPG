"""Characters blueprint."""

from flask import Blueprint

characters_bp = Blueprint('characters', __name__)

from vtt_app.characters.routes import *
