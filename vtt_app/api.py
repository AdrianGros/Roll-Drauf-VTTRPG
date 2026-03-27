"""LEGACY MODULE (not used by app factory, not for production runtime)."""

import os

if os.getenv("FLASK_ENV") == "production":
    raise RuntimeError("Legacy module vtt_app.api is disabled in production.")

from flask import Blueprint, jsonify, request, send_file, send_from_directory

from .dice import roll_dice
from .game_state import GameState

bp = Blueprint('api', __name__)

state = GameState()


@bp.route('/')
def index():
    return send_file('index.html')


@bp.route('/<path:path>')
def serve_static(path):
    if path.startswith('src/'):
        return send_from_directory('', path)
    return send_file('index.html')


@bp.route('/api/dice/roll', methods=['POST'])
def api_roll_dice():
    payload = request.get_json() or {}
    dice = payload.get('dice', '1d20')
    result = roll_dice(dice)
    return jsonify(result)


@bp.route('/api/game/state', methods=['GET'])
def api_get_state():
    return jsonify(state.get_map())


@bp.route('/api/tokens', methods=['POST'])
def api_create_token():
    data = request.get_json() or {}
    token = state.add_token(data)
    from .extensions import socketio
    socketio.emit('token_create', token)
    return jsonify(token)


@bp.route('/api/tokens/<token_id>', methods=['PUT'])
def api_update_token(token_id):
    data = request.get_json() or {}
    token = state.update_token(token_id, data)
    if not token:
        return jsonify({'error': 'Token not found'}), 404
    from .extensions import socketio
    socketio.emit('token_update', token)
    return jsonify(token)


@bp.route('/api/tokens/<token_id>', methods=['DELETE'])
def api_delete_token(token_id):
    state.delete_token(token_id)
    from .extensions import socketio
    socketio.emit('token_delete', token_id)
    return jsonify({'success': True})
