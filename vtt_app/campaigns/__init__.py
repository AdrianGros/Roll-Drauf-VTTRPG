"""Campaign module - campaign management routes."""

from flask import Blueprint

campaigns_bp = Blueprint('campaigns', __name__)

from vtt_app.campaigns.routes import *

__all__ = ['campaigns_bp']
