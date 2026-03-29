"""M41-M45: Session management endpoints for state machine, map layers, tokens, initiative, and real-time sync."""

from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required
from vtt_app.extensions import db
from vtt_app.models import GameSession, Campaign, AuditLog
from vtt_app.security import current_user
from vtt_app.utils.time import utcnow
from vtt_app.models import SessionMapLayer, SessionToken, SessionInitiative, Asset
from vtt_app.upload_security import validate_upload, UploadError
from vtt_app.storage import get_storage_adapter
import logging

logger = logging.getLogger(__name__)

ALLOWED_SESSION_ASSET_TYPES = {'map', 'token', 'handout', 'image'}

bp = Blueprint('sessions', __name__, url_prefix='/api/sessions')


# ============= Helper Functions =============

def _is_gm(session, user):
    """Check if user is GM of the session's campaign."""
    if not user or not session:
        return False
    campaign = Campaign.query.get(session.campaign_id)
    return campaign and campaign.dm_id == user.id


def _audit_log(action, resource_id, details=None, resource_type='session'):
    """Log action to audit trail."""
    if not current_user:
        return
    log_entry = AuditLog(
        user_id=current_user.id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details or {},
        timestamp=utcnow(),
    )
    db.session.add(log_entry)
    db.session.commit()


# ============= M41: Session State Machine =============

@bp.route('/<int:session_id>/start', methods=['POST'])
@jwt_required()
def start_session(session_id):
    """
    POST /api/sessions/<id>/start
    Transition session to active state (M41).
    """
    session = GameSession.query.get_or_404(session_id)

    if not _is_gm(session, current_user):
        return jsonify({'error': 'Only GM can start session'}), 403

    try:
        session.start()
        _audit_log('session_start', session_id, {'old_state': session.session_state})
        return jsonify(session.serialize()), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


@bp.route('/<int:session_id>/pause', methods=['POST'])
@jwt_required()
def pause_session(session_id):
    """
    POST /api/sessions/<id>/pause
    Pause an active session (M41).
    """
    session = GameSession.query.get_or_404(session_id)

    if not _is_gm(session, current_user):
        return jsonify({'error': 'Only GM can pause session'}), 403

    try:
        session.pause()
        _audit_log('session_pause', session_id, {'paused_at': session.paused_at.isoformat()})
        return jsonify(session.serialize()), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


@bp.route('/<int:session_id>/resume', methods=['POST'])
@jwt_required()
def resume_session(session_id):
    """
    POST /api/sessions/<id>/resume
    Resume a paused session (M41).
    """
    session = GameSession.query.get_or_404(session_id)

    if not _is_gm(session, current_user):
        return jsonify({'error': 'Only GM can resume session'}), 403

    try:
        session.resume()
        _audit_log('session_resume', session_id, {})
        return jsonify(session.serialize()), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


@bp.route('/<int:session_id>/end', methods=['POST'])
@jwt_required()
def end_session(session_id):
    """
    POST /api/sessions/<id>/end
    End the session and generate report (M41).
    """
    session = GameSession.query.get_or_404(session_id)

    if not _is_gm(session, current_user):
        return jsonify({'error': 'Only GM can end session'}), 403

    try:
        session.end()
        _audit_log('session_end', session_id, {
            'ended_at': session.ended_at.isoformat(),
            'duration_minutes': session.duration_minutes
        })
        return jsonify(session.serialize()), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


@bp.route('/<int:session_id>/archive', methods=['POST'])
@jwt_required()
def archive_session(session_id):
    """
    POST /api/sessions/<id>/archive
    Archive the session (M41).
    Can only be called after 30+ days from completion.
    """
    session = GameSession.query.get_or_404(session_id)

    if not _is_gm(session, current_user):
        return jsonify({'error': 'Only GM can archive session'}), 403

    try:
        session.archive()
        _audit_log('session_archive', session_id, {})
        return jsonify(session.serialize()), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


# ============= M42: Map Layers =============

@bp.route('/<int:session_id>/map-layers', methods=['POST'])
@jwt_required()
def create_map_layer(session_id):
    """
    POST /api/sessions/<id>/map-layers
    Create a new map layer (M42).
    """
    session = GameSession.query.get_or_404(session_id)

    if not _is_gm(session, current_user):
        return jsonify({'error': 'Only GM can create map layers'}), 403

    # Check layer limit (max 10)
    can_add, count = SessionMapLayer.check_layer_limit(session_id)
    if not can_add:
        return jsonify({'error': f'Maximum 10 layers per session (current: {count})'}), 400

    data = request.get_json() or {}

    # Validate required fields
    required = ['layer_name', 'width', 'height']
    if not all(k in data for k in required):
        return jsonify({'error': f'Missing required fields: {required}'}), 400

    # Get next layer order
    existing_layers = SessionMapLayer.get_session_layers(session_id)
    next_order = len(existing_layers)

    try:
        layer = SessionMapLayer(
            session_id=session_id,
            layer_name=data['layer_name'],
            layer_order=next_order,
            asset_id=data.get('asset_id'),
            width=int(data['width']),
            height=int(data['height']),
            grid_size=int(data.get('grid_size', 70)),
            is_visible=data.get('is_visible', True),
            fog_of_war_enabled=data.get('fog_of_war_enabled', False),
        )
        db.session.add(layer)
        db.session.commit()
        _audit_log('map_layer_create', session_id, {'layer_id': layer.id, 'layer_name': layer.layer_name}, 'session_map_layer')
        return jsonify(layer.serialize()), 201
    except (ValueError, TypeError) as e:
        db.session.rollback()
        return jsonify({'error': f'Invalid data: {str(e)}'}), 400


@bp.route('/<int:session_id>/map-layers', methods=['GET'])
@jwt_required()
def list_map_layers(session_id):
    """
    GET /api/sessions/<id>/map-layers
    List all map layers for session (M42).
    """
    session = GameSession.query.get_or_404(session_id)

    # Verify access (GM or campaign member)
    campaign = Campaign.query.get(session.campaign_id)
    if not campaign or (campaign.dm_id != current_user.id and not campaign.get_member(current_user.id)):
        return jsonify({'error': 'Access denied'}), 403

    layers = SessionMapLayer.get_session_layers(session_id)
    return jsonify([layer.serialize() for layer in layers]), 200


@bp.route('/<int:session_id>/map-layers/<int:layer_id>', methods=['PATCH'])
@jwt_required()
def update_map_layer(session_id, layer_id):
    """
    PATCH /api/sessions/<id>/map-layers/<layer_id>
    Update a map layer (M42).
    """
    session = GameSession.query.get_or_404(session_id)
    layer = SessionMapLayer.query.get_or_404(layer_id)

    if not _is_gm(session, current_user):
        return jsonify({'error': 'Only GM can update map layers'}), 403

    if layer.session_id != session_id:
        return jsonify({'error': 'Layer does not belong to this session'}), 400

    data = request.get_json() or {}

    try:
        if 'layer_name' in data:
            layer.layer_name = data['layer_name']
        if 'asset_id' in data:
            layer.asset_id = data['asset_id']
        if 'width' in data:
            layer.width = int(data['width'])
        if 'height' in data:
            layer.height = int(data['height'])
        if 'grid_size' in data:
            layer.grid_size = int(data['grid_size'])
        if 'is_visible' in data:
            layer.is_visible = bool(data['is_visible'])
        if 'fog_of_war_enabled' in data:
            layer.fog_of_war_enabled = bool(data['fog_of_war_enabled'])
        if 'fog_of_war_data' in data:
            layer.fog_of_war_data = data['fog_of_war_data']

        db.session.commit()
        _audit_log('map_layer_update', session_id, {'layer_id': layer_id}, 'session_map_layer')
        return jsonify(layer.serialize()), 200
    except (ValueError, TypeError) as e:
        db.session.rollback()
        return jsonify({'error': f'Invalid data: {str(e)}'}), 400


@bp.route('/<int:session_id>/map-layers/<int:layer_id>', methods=['DELETE'])
@jwt_required()
def delete_map_layer(session_id, layer_id):
    """
    DELETE /api/sessions/<id>/map-layers/<layer_id>
    Delete a map layer (M42).
    """
    session = GameSession.query.get_or_404(session_id)
    layer = SessionMapLayer.query.get_or_404(layer_id)

    if not _is_gm(session, current_user):
        return jsonify({'error': 'Only GM can delete map layers'}), 403

    if layer.session_id != session_id:
        return jsonify({'error': 'Layer does not belong to this session'}), 400

    try:
        db.session.delete(layer)
        db.session.commit()
        _audit_log('map_layer_delete', session_id, {'layer_id': layer_id}, 'session_map_layer')
        return jsonify({'message': 'Layer deleted'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/<int:session_id>/map-layers/<int:layer_id>/set-active', methods=['POST'])
@jwt_required()
def set_active_layer(session_id, layer_id):
    """
    POST /api/sessions/<id>/map-layers/<layer_id>/set-active
    Make a layer visible (active) (M42).
    """
    session = GameSession.query.get_or_404(session_id)
    layer = SessionMapLayer.query.get_or_404(layer_id)

    if not _is_gm(session, current_user):
        return jsonify({'error': 'Only GM can modify layers'}), 403

    if layer.session_id != session_id:
        return jsonify({'error': 'Layer does not belong to this session'}), 400

    layer.is_visible = True
    db.session.commit()
    _audit_log('map_layer_set_active', session_id, {'layer_id': layer_id}, 'session_map_layer')
    return jsonify(layer.serialize()), 200


# ============= M43: Session Tokens =============

@bp.route('/<int:session_id>/tokens', methods=['POST'])
@jwt_required()
def create_token(session_id):
    """
    POST /api/sessions/<id>/tokens
    Create a token on the map (M43).
    """
    session = GameSession.query.get_or_404(session_id)

    if not _is_gm(session, current_user):
        return jsonify({'error': 'Only GM can create tokens'}), 403

    data = request.get_json() or {}

    required = ['layer_id', 'name', 'x', 'y']
    if not all(k in data for k in required):
        return jsonify({'error': f'Missing required fields: {required}'}), 400

    layer = SessionMapLayer.query.get_or_404(data['layer_id'])
    if layer.session_id != session_id:
        return jsonify({'error': 'Layer does not belong to this session'}), 400

    try:
        token = SessionToken(
            session_id=session_id,
            layer_id=data['layer_id'],
            character_id=data.get('character_id'),
            name=data['name'],
            x=int(data['x']),
            y=int(data['y']),
            size=int(data.get('size', 70)),
            color=data.get('color', '#FF0000'),
            rotation=int(data.get('rotation', 0)),
            is_visible_to_players=data.get('is_visible_to_players', True),
        )
        db.session.add(token)
        db.session.commit()
        _audit_log('token_create', session_id, {'token_id': token.id, 'name': token.name}, 'session_token')
        return jsonify(token.serialize()), 201
    except (ValueError, TypeError) as e:
        db.session.rollback()
        return jsonify({'error': f'Invalid data: {str(e)}'}), 400


@bp.route('/<int:session_id>/tokens/<int:token_id>', methods=['PATCH'])
@jwt_required()
def update_token(session_id, token_id):
    """
    PATCH /api/sessions/<id>/tokens/<token_id>
    Update a token (M43).
    """
    session = GameSession.query.get_or_404(session_id)
    token = SessionToken.query.get_or_404(token_id)

    if not _is_gm(session, current_user):
        return jsonify({'error': 'Only GM can update tokens'}), 403

    if token.session_id != session_id:
        return jsonify({'error': 'Token does not belong to this session'}), 400

    data = request.get_json() or {}

    try:
        if 'name' in data:
            token.name = data['name']
        if 'x' in data or 'y' in data:
            x = int(data.get('x', token.x))
            y = int(data.get('y', token.y))
            token.move(x, y)
        if 'size' in data:
            token.size = int(data['size'])
        if 'color' in data:
            token.color = data['color']
        if 'rotation' in data:
            token.rotate(int(data['rotation']))
        if 'is_visible_to_players' in data:
            token.is_visible_to_players = bool(data['is_visible_to_players'])

        db.session.commit()
        _audit_log('token_update', session_id, {'token_id': token_id}, 'session_token')
        return jsonify(token.serialize()), 200
    except (ValueError, TypeError) as e:
        db.session.rollback()
        return jsonify({'error': f'Invalid data: {str(e)}'}), 400


@bp.route('/<int:session_id>/tokens/<int:token_id>', methods=['DELETE'])
@jwt_required()
def delete_token(session_id, token_id):
    """
    DELETE /api/sessions/<id>/tokens/<token_id>
    Delete a token (M43).
    """
    session = GameSession.query.get_or_404(session_id)
    token = SessionToken.query.get_or_404(token_id)

    if not _is_gm(session, current_user):
        return jsonify({'error': 'Only GM can delete tokens'}), 403

    if token.session_id != session_id:
        return jsonify({'error': 'Token does not belong to this session'}), 400

    try:
        db.session.delete(token)
        db.session.commit()
        _audit_log('token_delete', session_id, {'token_id': token_id}, 'session_token')
        return jsonify({'message': 'Token deleted'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ============= M43: Initiative =============

@bp.route('/<int:session_id>/initiative', methods=['GET'])
@jwt_required()
def get_initiative(session_id):
    """
    GET /api/sessions/<id>/initiative
    Get initiative order for session (M43).
    """
    session = GameSession.query.get_or_404(session_id)

    # Verify access
    campaign = Campaign.query.get(session.campaign_id)
    if not campaign or (campaign.dm_id != current_user.id and not campaign.get_member(current_user.id)):
        return jsonify({'error': 'Access denied'}), 403

    entries = SessionInitiative.get_session_initiative(session_id)
    return jsonify([entry.serialize() for entry in entries]), 200


@bp.route('/<int:session_id>/initiative/add', methods=['POST'])
@jwt_required()
def add_initiative(session_id):
    """
    POST /api/sessions/<id>/initiative/add
    Add character/NPC to initiative (M43).
    """
    session = GameSession.query.get_or_404(session_id)

    if not _is_gm(session, current_user):
        return jsonify({'error': 'Only GM can manage initiative'}), 403

    data = request.get_json() or {}

    required = ['character_name', 'initiative_roll']
    if not all(k in data for k in required):
        return jsonify({'error': f'Missing required fields: {required}'}), 400

    # Get next turn order
    existing = SessionInitiative.get_session_initiative(session_id)
    next_order = len(existing)

    try:
        entry = SessionInitiative(
            session_id=session_id,
            character_id=data.get('character_id'),
            character_name=data['character_name'],
            initiative_roll=int(data['initiative_roll']),
            turn_order=next_order,
            is_current_turn=(next_order == 0),  # First entry gets current turn
        )
        db.session.add(entry)
        db.session.commit()
        _audit_log('initiative_add', session_id, {'character': data['character_name'], 'roll': data['initiative_roll']}, 'session_initiative')
        return jsonify(entry.serialize()), 201
    except (ValueError, TypeError) as e:
        db.session.rollback()
        return jsonify({'error': f'Invalid data: {str(e)}'}), 400


@bp.route('/<int:session_id>/initiative/roll', methods=['POST'])
@jwt_required()
def roll_initiative(session_id):
    """
    POST /api/sessions/<id>/initiative/roll
    Auto-sort initiative by rolls (M43).
    """
    session = GameSession.query.get_or_404(session_id)

    if not _is_gm(session, current_user):
        return jsonify({'error': 'Only GM can manage initiative'}), 403

    try:
        entries = SessionInitiative.get_session_initiative(session_id)

        # Sort by roll descending
        entries.sort(key=lambda e: e.initiative_roll, reverse=True)

        # Update turn order
        for i, entry in enumerate(entries):
            entry.turn_order = i
            entry.is_current_turn = (i == 0)

        db.session.commit()
        _audit_log('initiative_roll', session_id, {'count': len(entries)}, 'session_initiative')
        return jsonify([e.serialize() for e in entries]), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/<int:session_id>/initiative/next-turn', methods=['POST'])
@jwt_required()
def next_turn(session_id):
    """
    POST /api/sessions/<id>/initiative/next-turn
    Advance to next turn (M43).
    """
    session = GameSession.query.get_or_404(session_id)

    if not _is_gm(session, current_user):
        return jsonify({'error': 'Only GM can manage initiative'}), 403

    try:
        current = SessionInitiative.get_current_turn(session_id)
        if current:
            current.advance_turn()
        entries = SessionInitiative.get_session_initiative(session_id)
        _audit_log('initiative_next_turn', session_id, {}, 'session_initiative')
        return jsonify([e.serialize() for e in entries]), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/<int:session_id>/initiative/<int:entry_id>', methods=['PATCH'])
@jwt_required()
def update_initiative(session_id, entry_id):
    """
    PATCH /api/sessions/<id>/initiative/<entry_id>
    Update an initiative entry (M43).
    """
    session = GameSession.query.get_or_404(session_id)
    entry = SessionInitiative.query.get_or_404(entry_id)

    if not _is_gm(session, current_user):
        return jsonify({'error': 'Only GM can manage initiative'}), 403

    if entry.session_id != session_id:
        return jsonify({'error': 'Entry does not belong to this session'}), 400

    data = request.get_json() or {}

    try:
        if 'character_name' in data:
            entry.character_name = data['character_name']
        if 'initiative_roll' in data:
            entry.initiative_roll = int(data['initiative_roll'])
        if 'is_current_turn' in data:
            entry.is_current_turn = bool(data['is_current_turn'])

        db.session.commit()
        _audit_log('initiative_update', session_id, {'entry_id': entry_id}, 'session_initiative')
        return jsonify(entry.serialize()), 200
    except (ValueError, TypeError) as e:
        db.session.rollback()
        return jsonify({'error': f'Invalid data: {str(e)}'}), 400


# ============= M44: Session Assets =============

@bp.route('/<int:session_id>/assets/upload', methods=['POST'])
@jwt_required()
def upload_session_asset(session_id):
    """
    POST /api/sessions/<id>/assets/upload
    Upload an asset for session use (M44).
    Max 50MB, 100 files/session.
    """
    session = GameSession.query.get_or_404(session_id)

    if not _is_gm(session, current_user):
        return jsonify({'error': 'Only GM can upload session assets'}), 403

    # Check file count limit
    asset_count = Asset.query.filter_by(session_id=session_id).count()
    if asset_count >= 100:
        return jsonify({'error': 'Maximum 100 assets per session'}), 400

    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    if not file or file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    try:
        validation = validate_upload(file, current_user)
    except UploadError as err:
        return jsonify({'error': str(err)}), 400

    asset_type = str(request.form.get('asset_type', 'image')).strip().lower() or 'image'
    if asset_type not in ALLOWED_SESSION_ASSET_TYPES:
        return jsonify({'error': 'Unsupported asset type'}), 400

    storage = get_storage_adapter()
    file_key = f"sessions/{session_id}/assets/{validation['checksum_md5'][:8]}-{validation['filename']}"

    try:
        storage.upload(file_key, validation['content'])

        asset = Asset(
            campaign_id=session.campaign_id,
            session_id=session_id,
            uploaded_by=current_user.id,
            filename=validation['filename'],
            mime_type=validation['mime_type'],
            size_bytes=validation['size_bytes'],
            checksum_md5=validation['checksum_md5'],
            asset_type=asset_type,
            scope='session',
            storage_key=file_key,
            storage_provider=current_app.config.get('STORAGE_PROVIDER', 'local'),
        )
        db.session.add(asset)

        # M17 quota integration: keep user storage counter in sync.
        current_user.storage_used_gb += validation['size_bytes'] / 1024 / 1024 / 1024

        db.session.commit()

        _audit_log(
            'asset_upload',
            session_id,
            {
                'asset_id': asset.id,
                'filename': validation['filename'],
                'size_bytes': validation['size_bytes'],
                'storage_provider': asset.storage_provider,
            },
            'asset',
        )
        return jsonify(asset.serialize()), 201
    except Exception as e:
        db.session.rollback()
        logger.exception(f"Error uploading asset to session {session_id}")
        return jsonify({'error': 'Upload failed'}), 500
