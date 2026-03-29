"""M45: Socket.IO real-time sync handlers for sessions (map, tokens, initiative, session state)."""

from flask import request
from flask_socketio import emit, join_room, leave_room
from time import monotonic
from collections import defaultdict
import logging

from vtt_app.extensions import db
from vtt_app.models import GameSession, SessionMapLayer, SessionToken, SessionInitiative, Campaign
from vtt_app.utils.realtime import build_event_envelope, current_event_seq
from vtt_app.utils.time import utcnow

logger = logging.getLogger(__name__)

# Track token movement debouncing (batch every 100ms)
_token_move_queue = defaultdict(dict)  # session_id -> {token_id: last_move_event}
_last_token_flush = defaultdict(float)  # session_id -> last flush timestamp


def _session_room(session_id):
    """Get room name for session."""
    return f"session:{session_id}"


def _session_gm_room(session_id):
    """Get room name for GM-only events."""
    return f"session:{session_id}:gm"


def _emit_session_event(event_name, session_id, payload=None, room_override=None, include_sequence=True):
    """
    Emit event to session room with sequence numbering.

    Args:
        event_name: Socket event name
        session_id: Session ID
        payload: Event data
        room_override: Override default room (e.g., for GM-only events)
        include_sequence: Include sequence number in envelope
    """
    room = room_override or _session_room(session_id)
    event_payload = build_event_envelope(None, session_id, payload, advance=include_sequence) if include_sequence else payload
    emit(event_name, event_payload, room=room)


def _get_user_from_token():
    """Extract user from JWT token in socket request."""
    from flask_jwt_extended import decode_token
    token = request.args.get('token')
    if not token:
        return None
    try:
        decoded = decode_token(token)
        return decoded.get('sub')  # user_id
    except:
        return None


def _is_gm(session_id, user_id):
    """Check if user is GM of the session."""
    session = GameSession.query.get(session_id)
    if not session:
        return False
    campaign = Campaign.query.get(session.campaign_id)
    return campaign and campaign.dm_id == user_id


# ============= M45: Socket Registration =============

def register_session_handlers(socketio):
    """Register all session socket handlers with socketio instance."""

    @socketio.on('session:join')
    def on_session_join(data):
        """
        Join session room for real-time updates.

        Payload:
            - session_id: int
            - user_id: int
        """
        session_id = data.get('session_id')
        user_id = _get_user_from_token()

        if not session_id or not user_id:
            emit('error', {'message': 'Invalid session or user'})
            return

        session = GameSession.query.get(session_id)
        if not session:
            emit('error', {'message': 'Session not found'})
            return

        room = _session_room(session_id)
        join_room(room)

        # Also join GM room if user is GM
        if _is_gm(session_id, user_id):
            join_room(_session_gm_room(session_id))

        logger.info(f"User {user_id} joined session {session_id} room")
        _emit_session_event('session:user_joined', session_id, {'user_id': user_id})

    @socketio.on('session:leave')
    def on_session_leave(data):
        """Leave session room."""
        session_id = data.get('session_id')
        user_id = _get_user_from_token()

        if session_id:
            room = _session_room(session_id)
            leave_room(room)
            gm_room = _session_gm_room(session_id)
            leave_room(gm_room)

            logger.info(f"User {user_id} left session {session_id} room")
            _emit_session_event('session:user_left', session_id, {'user_id': user_id})

    @socketio.on('session:resync')
    def on_session_resync(data):
        """
        Request full resync of session state (for reconnects).

        Payload:
            - session_id: int
            - client_seq: int (optional, client's last known sequence)
        """
        session_id = data.get('session_id')
        user_id = _get_user_from_token()

        if not session_id or not user_id:
            emit('error', {'message': 'Invalid request'})
            return

        session = GameSession.query.get(session_id)
        if not session:
            emit('error', {'message': 'Session not found'})
            return

        # Send full state snapshot
        try:
            layers = SessionMapLayer.get_session_layers(session_id)
            tokens = SessionToken.get_session_tokens(session_id)
            initiative = SessionInitiative.get_session_initiative(session_id)

            resync_data = {
                'session': session.serialize(),
                'map_layers': [l.serialize() for l in layers],
                'tokens': [t.serialize() for t in tokens],
                'initiative': [i.serialize() for i in initiative],
            }

            emit('session:resync_data', resync_data)
            logger.info(f"Resync sent to user {user_id} for session {session_id}")
        except Exception as e:
            logger.exception(f"Error during resync for session {session_id}")
            emit('error', {'message': 'Resync failed'})

    # ===== M45: Map Layer Events =====

    @socketio.on('map:layer_changed')
    def on_layer_changed(data):
        """
        Layer properties changed (visibility, size, FOW, etc).

        Payload:
            - session_id: int
            - layer_id: int
            - changes: dict (properties that changed)
        """
        session_id = data.get('session_id')
        user_id = _get_user_from_token()

        if not _is_gm(session_id, user_id):
            emit('error', {'message': 'Only GM can change layers'})
            return

        layer = SessionMapLayer.query.get(data.get('layer_id'))
        if not layer or layer.session_id != session_id:
            emit('error', {'message': 'Layer not found'})
            return

        try:
            # Update layer properties
            for key, value in (data.get('changes') or {}).items():
                if hasattr(layer, key):
                    setattr(layer, key, value)

            db.session.commit()
            _emit_session_event('map:layer_changed', session_id, {
                'layer_id': layer.id,
                'layer': layer.serialize(),
            })
        except Exception as e:
            db.session.rollback()
            logger.exception(f"Error updating layer {data.get('layer_id')}")
            emit('error', {'message': 'Update failed'})

    @socketio.on('map:layer_visibility_changed')
    def on_layer_visibility_changed(data):
        """Toggle layer visibility (GM only)."""
        session_id = data.get('session_id')
        user_id = _get_user_from_token()

        if not _is_gm(session_id, user_id):
            emit('error', {'message': 'Only GM can change visibility'})
            return

        layer = SessionMapLayer.query.get(data.get('layer_id'))
        if not layer or layer.session_id != session_id:
            emit('error', {'message': 'Layer not found'})
            return

        layer.is_visible = data.get('is_visible', not layer.is_visible)
        db.session.commit()

        _emit_session_event('map:layer_visibility_changed', session_id, {
            'layer_id': layer.id,
            'is_visible': layer.is_visible,
        })

    @socketio.on('map:layer_removed')
    def on_layer_removed(data):
        """Layer deleted (GM only)."""
        session_id = data.get('session_id')
        user_id = _get_user_from_token()

        if not _is_gm(session_id, user_id):
            emit('error', {'message': 'Only GM can remove layers'})
            return

        layer = SessionMapLayer.query.get(data.get('layer_id'))
        if not layer or layer.session_id != session_id:
            emit('error', {'message': 'Layer not found'})
            return

        layer_id = layer.id
        db.session.delete(layer)
        db.session.commit()

        _emit_session_event('map:layer_removed', session_id, {'layer_id': layer_id})

    # ===== M45: Token Events =====

    @socketio.on('token:moved')
    def on_token_moved(data):
        """
        Token moved on map (debounced, batched every 100ms).

        Payload:
            - session_id: int
            - token_id: int
            - x: int
            - y: int
        """
        session_id = data.get('session_id')
        user_id = _get_user_from_token()
        token_id = data.get('token_id')

        if not _is_gm(session_id, user_id):
            emit('error', {'message': 'Only GM can move tokens'})
            return

        token = SessionToken.query.get(token_id)
        if not token or token.session_id != session_id:
            emit('error', {'message': 'Token not found'})
            return

        # Queue token movement for debouncing
        _token_move_queue[session_id][token_id] = {
            'x': data.get('x'),
            'y': data.get('y'),
            'timestamp': utcnow(),
        }

        # Flush if enough time has passed
        now = monotonic()
        if (now - _last_token_flush[session_id]) > 0.1:  # 100ms
            _flush_token_moves(session_id)

    def _flush_token_moves(session_id):
        """Flush queued token movements and broadcast to session."""
        moves = _token_move_queue.get(session_id, {})
        if not moves:
            return

        try:
            for token_id, move_data in moves.items():
                token = SessionToken.query.get(token_id)
                if token:
                    token.x = move_data['x']
                    token.y = move_data['y']

            db.session.commit()

            # Emit single event with all moves
            emit_data = {
                'moves': [
                    {'token_id': tid, 'x': move['x'], 'y': move['y']}
                    for tid, move in moves.items()
                ],
            }
            _emit_session_event('token:batch_moved', session_id, emit_data)

            _token_move_queue[session_id].clear()
            _last_token_flush[session_id] = monotonic()
        except Exception as e:
            db.session.rollback()
            logger.exception(f"Error flushing token moves for session {session_id}")

    @socketio.on('token:created')
    def on_token_created(data):
        """Token created (emitted for broadcast)."""
        session_id = data.get('session_id')
        user_id = _get_user_from_token()

        if not _is_gm(session_id, user_id):
            emit('error', {'message': 'Only GM can create tokens'})
            return

        token = SessionToken.query.get(data.get('token_id'))
        if not token or token.session_id != session_id:
            emit('error', {'message': 'Token not found'})
            return

        _emit_session_event('token:created', session_id, {'token': token.serialize()})

    @socketio.on('token:deleted')
    def on_token_deleted(data):
        """Token deleted (emitted for broadcast)."""
        session_id = data.get('session_id')
        user_id = _get_user_from_token()

        if not _is_gm(session_id, user_id):
            emit('error', {'message': 'Only GM can delete tokens'})
            return

        token_id = data.get('token_id')
        _emit_session_event('token:deleted', session_id, {'token_id': token_id})

    # ===== M45: Initiative Events =====

    @socketio.on('initiative:updated')
    def on_initiative_updated(data):
        """Initiative order updated."""
        session_id = data.get('session_id')
        user_id = _get_user_from_token()

        if not _is_gm(session_id, user_id):
            emit('error', {'message': 'Only GM can update initiative'})
            return

        entries = SessionInitiative.get_session_initiative(session_id)
        _emit_session_event('initiative:updated', session_id, {
            'initiative': [e.serialize() for e in entries],
        })

    @socketio.on('initiative:turn_changed')
    def on_turn_changed(data):
        """Current turn changed."""
        session_id = data.get('session_id')
        user_id = _get_user_from_token()

        if not _is_gm(session_id, user_id):
            emit('error', {'message': 'Only GM can advance turns'})
            return

        current = SessionInitiative.get_current_turn(session_id)
        _emit_session_event('initiative:turn_changed', session_id, {
            'current_turn': current.serialize() if current else None,
        })

    # ===== M45: Session State Events =====

    @socketio.on('session:paused')
    def on_session_paused(data):
        """Session paused (broadcast)."""
        session_id = data.get('session_id')
        session = GameSession.query.get(session_id)

        if session:
            _emit_session_event('session:paused', session_id, {
                'session': session.serialize(),
                'paused_at': session.paused_at.isoformat() if session.paused_at else None,
            })

    @socketio.on('session:resumed')
    def on_session_resumed(data):
        """Session resumed (broadcast)."""
        session_id = data.get('session_id')
        session = GameSession.query.get(session_id)

        if session:
            _emit_session_event('session:resumed', session_id, {
                'session': session.serialize(),
            })

    @socketio.on('session:ended')
    def on_session_ended(data):
        """Session ended (broadcast)."""
        session_id = data.get('session_id')
        session = GameSession.query.get(session_id)

        if session:
            _emit_session_event('session:ended', session_id, {
                'session': session.serialize(),
                'ended_at': session.ended_at.isoformat() if session.ended_at else None,
            })

    @socketio.on('session:player_joined')
    def on_player_joined(data):
        """Player joined session."""
        session_id = data.get('session_id')
        user_id = data.get('user_id')

        _emit_session_event('session:player_joined', session_id, {
            'user_id': user_id,
        })

    @socketio.on('session:player_left')
    def on_player_left(data):
        """Player left session."""
        session_id = data.get('session_id')
        user_id = data.get('user_id')

        _emit_session_event('session:player_left', session_id, {
            'user_id': user_id,
        })

    # ===== M45: Chat and Action Events =====

    @socketio.on('chat:message_sent')
    def on_chat_message_sent(data):
        """Chat message broadcast (with sequence)."""
        session_id = data.get('session_id')

        _emit_session_event('chat:message_sent', session_id, {
            'message': data.get('message'),
            'sender_id': data.get('sender_id'),
            'sender_name': data.get('sender_name'),
            'timestamp': utcnow().isoformat(),
        })

    @socketio.on('action:performed')
    def on_action_performed(data):
        """Action performed (broadcast)."""
        session_id = data.get('session_id')

        _emit_session_event('action:performed', session_id, {
            'action': data.get('action'),
            'actor_id': data.get('actor_id'),
            'details': data.get('details'),
        })

    # ===== M45: Sheet Updates =====

    @socketio.on('sheet:hp_updated')
    def on_hp_updated(data):
        """Character HP updated."""
        session_id = data.get('session_id')

        _emit_session_event('sheet:hp_updated', session_id, {
            'character_id': data.get('character_id'),
            'current_hp': data.get('current_hp'),
            'max_hp': data.get('max_hp'),
        })

    @socketio.on('sheet:spell_cast')
    def on_spell_cast(data):
        """Spell cast event."""
        session_id = data.get('session_id')

        _emit_session_event('sheet:spell_cast', session_id, {
            'character_id': data.get('character_id'),
            'spell_name': data.get('spell_name'),
            'details': data.get('details'),
        })

    logger.info("Session socket handlers registered")
