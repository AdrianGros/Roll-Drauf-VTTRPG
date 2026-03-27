"""M19-M24: Asset management endpoints (upload, download, list, version)."""

import io
from flask import Blueprint, request, jsonify, send_file, current_app
from flask_jwt_extended import jwt_required
from vtt_app.extensions import db
from vtt_app.models import Asset, Campaign, User
from vtt_app.permissions import has_platform_role, can_view_campaign, can_edit_campaign, require_campaign_access
from vtt_app.upload_security import validate_upload, UploadError
from vtt_app.storage import get_storage_adapter
from vtt_app.utils.audit import log_audit
from vtt_app.security import current_user

assets_bp = Blueprint('assets', __name__, url_prefix='/api/assets')


# ===== M19: List & Download =====

@assets_bp.route('/campaigns/<int:campaign_id>/list', methods=['GET'])
@jwt_required()
def list_campaign_assets(campaign_id):
    """List all assets in campaign, grouped by type."""
    campaign = Campaign.query.get(campaign_id)
    if not campaign or not can_view_campaign(current_user, campaign):
        return jsonify({'error': 'Forbidden'}), 403

    # Get grouped assets
    grouped = Asset.get_campaign_assets_by_type(campaign_id, include_deleted=False)

    return jsonify({
        'campaign_id': campaign_id,
        'assets': {
            key: [a.serialize() for a in assets]
            for key, assets in grouped.items()
        }
    }), 200


@assets_bp.route('/<int:asset_id>/download', methods=['GET'])
@jwt_required()
def download_asset(asset_id):
    """Download asset file."""
    asset = Asset.query.get(asset_id)
    if not asset or asset.is_soft_deleted():
        return jsonify({'error': 'Asset not found'}), 404

    # Check permission
    campaign = asset.campaign
    if not can_view_campaign(current_user, campaign):
        return jsonify({'error': 'Forbidden'}), 403

    # Get from storage
    storage = get_storage_adapter()
    try:
        content = storage.download(asset.storage_key)
    except Exception as e:
        return jsonify({'error': f'Download failed: {str(e)}'}), 500

    # Log download
    log_audit(
        action='asset_downloaded',
        resource_type='asset',
        resource_id=asset.id,
        details={'filename': asset.filename},
        performed_by=current_user
    )

    return send_file(
        io.BytesIO(content),
        mimetype=asset.mime_type,
        as_attachment=True,
        download_name=asset.filename
    ), 200


# ===== M20: Upload with Security =====

@assets_bp.route('/campaigns/<int:campaign_id>/upload', methods=['POST'])
@jwt_required()
@require_campaign_access(can_edit_campaign)
def upload_asset(campaign_id):
    """Upload new asset to campaign."""
    campaign = Campaign.query.get(campaign_id)

    # Check file presence
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file_obj = request.files['file']
    asset_type = request.form.get('asset_type', 'image')  # map, token, handout, image

    # M20: Validate upload
    try:
        validation = validate_upload(file_obj, current_user)
    except UploadError as e:
        return jsonify({'error': str(e)}), 400

    # M21: Upload to storage
    storage = get_storage_adapter()
    file_key = f'campaigns/{campaign_id}/assets/{validation["checksum_md5"][:8]}-{validation["filename"]}'

    try:
        storage.upload(file_key, validation['content'])
    except Exception as e:
        return jsonify({'error': f'Storage upload failed: {str(e)}'}), 500

    # M19: Create asset record
    asset = Asset(
        campaign_id=campaign_id,
        uploaded_by=current_user.id,
        filename=validation['filename'],
        mime_type=validation['mime_type'],
        size_bytes=validation['size_bytes'],
        checksum_md5=validation['checksum_md5'],
        storage_key=file_key,
        storage_provider=current_app.config.get('STORAGE_PROVIDER', 'local'),
        asset_type=asset_type,
        scope='campaign',
        is_public=request.form.get('is_public', 'false').lower() == 'true',
    )
    db.session.add(asset)
    db.session.commit()

    # Update user's storage usage (M17)
    current_user.storage_used_gb += validation['size_bytes'] / 1024 / 1024 / 1024
    db.session.commit()

    # Log
    log_audit(
        action='asset_uploaded',
        resource_type='asset',
        resource_id=asset.id,
        details={
            'filename': asset.filename,
            'size_mb': asset.get_size_mb(),
            'asset_type': asset_type,
        },
        performed_by=current_user
    )

    return jsonify({
        'asset_id': asset.id,
        'filename': asset.filename,
        'size_bytes': asset.size_bytes,
        'asset_type': asset_type,
        'message': 'Asset uploaded successfully',
    }), 201


# ===== M19: Version History =====

@assets_bp.route('/<int:asset_id>/versions', methods=['GET'])
@jwt_required()
def get_asset_versions(asset_id):
    """Get version history of asset."""
    asset = Asset.query.get(asset_id)
    if not asset or asset.is_soft_deleted():
        return jsonify({'error': 'Asset not found'}), 404

    if not can_view_campaign(current_user, asset.campaign):
        return jsonify({'error': 'Forbidden'}), 403

    versions = asset.get_version_history()
    return jsonify({
        'asset_id': asset_id,
        'current_version': asset.asset_version,
        'versions': [v.serialize() for v in versions],
    }), 200


@assets_bp.route('/<int:asset_id>/rollback/<int:version_number>', methods=['POST'])
@jwt_required()
@require_campaign_access(can_edit_campaign)
def rollback_asset(asset_id, version_number):
    """Rollback asset to previous version."""
    asset = Asset.query.get(asset_id)
    if not asset:
        return jsonify({'error': 'Asset not found'}), 404

    versions = asset.get_version_history()
    target_version = next((v for v in versions if v.asset_version == version_number), None)

    if not target_version:
        return jsonify({'error': f'Version {version_number} not found'}), 404

    # Create new version pointing to old content
    new_asset = Asset(
        campaign_id=asset.campaign_id,
        uploaded_by=current_user.id,
        filename=target_version.filename,
        mime_type=target_version.mime_type,
        size_bytes=target_version.size_bytes,
        checksum_md5=target_version.checksum_md5,
        storage_key=target_version.storage_key,
        storage_provider=target_version.storage_provider,
        asset_type=asset.asset_type,
        asset_version=asset.asset_version + 1,
        parent_asset_id=asset.id if not asset.parent_asset_id else asset.parent_asset_id,
    )
    db.session.add(new_asset)
    db.session.commit()

    log_audit(
        action='asset_rolled_back',
        resource_type='asset',
        resource_id=asset.id,
        details={
            'from_version': asset.asset_version,
            'to_version': version_number,
        },
        performed_by=current_user
    )

    return jsonify({
        'asset_id': asset.id,
        'new_version': new_asset.asset_version,
        'message': f'Rolled back to version {version_number}',
    }), 200


# ===== M19: Delete (soft) =====

@assets_bp.route('/<int:asset_id>/delete', methods=['DELETE'])
@jwt_required()
@require_campaign_access(can_edit_campaign)
def delete_asset(asset_id):
    """Soft-delete asset (kept for retention, can be restored)."""
    asset = Asset.query.get(asset_id)
    if not asset or asset.is_soft_deleted():
        return jsonify({'error': 'Asset not found'}), 404

    asset.deleted_at = db.func.current_timestamp()
    db.session.commit()

    log_audit(
        action='asset_deleted',
        resource_type='asset',
        resource_id=asset.id,
        details={'filename': asset.filename},
        performed_by=current_user
    )

    return jsonify({'message': 'Asset deleted'}), 200


# ===== M24: Session Active Layer (Live Runtime) =====

@assets_bp.route('/sessions/<int:session_id>/active-layer', methods=['GET', 'POST'])
@jwt_required()
def get_set_active_layer(session_id):
    """Get/set currently displayed map layer in session (M24)."""
    from vtt_app.models import GameSession, SessionState

    session = GameSession.query.get(session_id)
    if not session:
        return jsonify({'error': 'Session not found'}), 404

    # Get or create SessionState for this session
    session_state = SessionState.query.filter_by(game_session_id=session_id).first()
    if not session_state:
        session_state = SessionState(
            game_session_id=session_id,
            campaign_id=session.campaign_id,
            state_status='preparing'
        )
        db.session.add(session_state)
        db.session.commit()

    if request.method == 'POST':
        data = request.get_json()
        asset_id = data.get('asset_id')

        asset = Asset.query.get(asset_id)
        if not asset or asset.campaign_id != session.campaign_id:
            return jsonify({'error': 'Invalid asset'}), 400

        # Update session state with active layer asset
        session_state.snapshot_json = session_state.snapshot_json or {}
        session_state.snapshot_json['active_asset_id'] = asset_id
        session_state.snapshot_json['asset_type'] = asset.asset_type
        session_state.bump_version()
        db.session.commit()

        log_audit(
            action='session_active_layer_changed',
            resource_type='session',
            resource_id=session_id,
            details={
                'asset_id': asset_id,
                'asset_type': asset.asset_type,
                'filename': asset.filename,
                'version': session_state.version
            },
            performed_by=current_user
        )

        return jsonify({
            'session_id': session_id,
            'active_asset_id': asset_id,
            'asset_type': asset.asset_type,
            'state_version': session_state.version,
            'message': 'Active layer updated',
        }), 200

    # GET: Return current active layer from session state
    active_asset_id = None
    asset_type = None
    if session_state.snapshot_json:
        active_asset_id = session_state.snapshot_json.get('active_asset_id')
        asset_type = session_state.snapshot_json.get('asset_type')

    return jsonify({
        'session_id': session_id,
        'active_asset_id': active_asset_id,
        'asset_type': asset_type,
        'state_version': session_state.version,
    }), 200
