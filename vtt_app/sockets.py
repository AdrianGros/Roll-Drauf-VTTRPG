"""LEGACY MODULE (not used by app factory, not for production runtime)."""

import os

if os.getenv("FLASK_ENV") == "production":
    raise RuntimeError("Legacy module vtt_app.sockets is disabled in production.")

from flask_socketio import emit
from .api import state


def init_sockets(socketio):
    @socketio.on('connect')
    def handle_connect(sid):
        print(f"Client connected: {sid}")

    @socketio.on('disconnect')
    def handle_disconnect(sid):
        print(f"Client disconnected: {sid}")

    @socketio.on('get_map_state')
    def handle_get_map_state(data, callback):
        callback(state.get_map())

    @socketio.on('token_update')
    def handle_token_update(token):
        for t in state.get_map()['tokens']:
            if t.get('id') == token.get('id'):
                t['x'] = token.get('x')
                t['y'] = token.get('y')
                break
        emit('token_update', token, broadcast=True, include_self=False)

    @socketio.on('token_create')
    def handle_token_create(token):
        state.add_token(token)
        emit('token_create', token, broadcast=True)

    @socketio.on('token_delete')
    def handle_token_delete(data):
        token_id = data.get('id')
        state.delete_token(token_id)
        emit('token_delete', token_id, broadcast=True)

    @socketio.on('roll_dice')
    def handle_roll_dice(data, callback):
        dice = data.get('dice', '1d20')
        from .dice import roll_dice
        result = roll_dice(dice)
        callback(result)
        emit('dice_rolled', {'player': data.get('player', 'anonymous'), 'dice': dice, 'result': result}, broadcast=True)
