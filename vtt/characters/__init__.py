"""Characters blueprint."""

from flask import Blueprint

characters_bp = Blueprint('characters', __name__)

from vtt.characters.routes import *
