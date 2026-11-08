"""Campaign module - campaign management routes."""

from flask import Blueprint

campaigns_bp = Blueprint('campaigns', __name__)

from vtt.campaigns.routes import *
from vtt.campaigns import calendar_routes

__all__ = ['campaigns_bp']
