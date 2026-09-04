"""M19-M24: Asset management endpoints (upload, download, list, version)."""

import io
import logging
from flask import Blueprint, request, jsonify, send_file, current_app
from flask_jwt_extended import jwt_required
from sqlalchemy import or_
from vtt.extensions import db
from vtt.models import Asset, Campaign, CampaignMember, GameSession, User
from vtt.permissions import has_platform_role, can_view_campaign, can_edit_campaign, require_campaign_access, try_reserve_storage, release_storage
from vtt.upload_security import validate_upload, UploadError
from vtt.storage import get_storage_adapter
from vtt.utils.audit import log_audit
from vtt.utils.images import generate_thumbnail
from vtt.security import current_user

logger = logging.getLogger(__name__)

assets_bp = Blueprint('assets', __name__, url_prefix='/api/assets')

LIBRARY_ALLOWED_ASSET_TYPES = {'map', 'token', 'handout', 'image'}


def _can_access_library(campaign, user):
    """Return True when the user is an active campaign member or owner."""
    if not campaign or not user:
        return False

    if campaign.owner_id == user.id:
        return True

    return CampaignMember.query.filter_by(
        campaign_id=campaign.id,
        user_id=user.id,
        status='active',
    ).first() is not None


def _handout_visible_to(asset, campaign, user) -> bool:
    """Fixed 2026-09-02: uploading a handout already required DM/CO-DM
    rights (see upload_asset's own comment, "handouts... stay DM/CO_DM-
    only exactly as before"), but every READ path here only checked
    campaign membership -- any Player could list, preview, and download
    a DM-only handout the moment it was uploaded. is_public (stored on
    every Asset, default False, but never actually read anywhere before
    this fix) is now the reveal switch: a handout is visible to a
    non-editor once its DM/CO-DM flips it public. Every other asset_type
    (map/token/image) is unaffected -- those were never reported as
    secret and this only tightens handout reads."""
    if asset.asset_type != 'handout':
        return True
    if asset.is_public:
        return True
    return can_edit_campaign(user, campaign)


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
    grouped = {
        key: [a for a in assets if _handout_visible_to(a, campaign, current_user)]
        for key, assets in grouped.items()
    }

    return jsonify({
        'campaign_id': campaign_id,
        'assets': {
            key: [a.serialize() for a in assets]
            for key, assets in grouped.items()
        }
    }), 200


@assets_bp.route('/campaigns/<int:campaign_id>/library', methods=['GET'])
@jwt_required()
def get_campaign_asset_library(campaign_id):
    """Return asset library payload for campaign hub use."""
    campaign = Campaign.query.get(campaign_id)
    if not campaign or not _can_access_library(campaign, current_user):
        return jsonify({'error': 'Forbidden'}), 403

    asset_type = (request.args.get('asset_type') or '').strip().lower() or None
    if asset_type and asset_type not in LIBRARY_ALLOWED_ASSET_TYPES:
        return jsonify({'error': 'Unsupported asset type'}), 400

    scope = (request.args.get('scope') or 'all').strip().lower()
    if scope not in {'all', 'campaign', 'session'}:
        return jsonify({'error': 'Unsupported scope'}), 400

    raw_session_id = request.args.get('session_id')
    session_id = None
    if raw_session_id:
        try:
            session_id = int(raw_session_id)
        except (TypeError, ValueError):
            return jsonify({'error': 'session_id must be a number'}), 400

    search = (request.args.get('query') or '').strip() or None
    page = request.args.get('page', 1)
    per_page = request.args.get('per_page', 24)
    try:
        page = max(1, int(page))
        per_page = min(100, max(1, int(per_page)))
    except (TypeError, ValueError):
        return jsonify({'error': 'page and per_page must be numbers'}), 400

    base_query = Asset.get_library_assets(
        campaign_id,
        asset_type=asset_type,
        scope=scope,
        session_id=session_id,
        search=search,
        include_deleted=False,
    )
    # Fixed 2026-09-02: query-level filter (not a post-fetch filter) so
    # page/per_page/total/has_more stay correct -- see _handout_visible_to.
    if not can_edit_campaign(current_user, campaign):
        base_query = base_query.filter(
            or_(Asset.asset_type != 'handout', Asset.is_public.is_(True)))

    total = base_query.count()
    assets = base_query.offset((page - 1) * per_page).limit(per_page).all()

    # Session roster for upload targets and context.
    sessions = GameSession.query.filter_by(campaign_id=campaign_id).order_by(GameSession.created_at.desc()).all()

    stats = Asset.get_library_stats(campaign_id, include_deleted=False)
    stats.update({
        'session_count': len(sessions),
        'filter_total': total,
        'active_session_count': sum(1 for session in sessions if session.status in {'in_progress', 'paused'}),
    })

    return jsonify({
        'campaign_id': campaign_id,
        'campaign_name': campaign.name,
        'filters': {
            'asset_type': asset_type,
            'scope': scope,
            'session_id': session_id,
            'query': search,
            'page': page,
            'per_page': per_page,
        },
        'stats': stats,
        'sessions': [session.serialize() for session in sessions],
        'assets': [asset.serialize() for asset in assets],
        'total': total,
        'page': page,
        'per_page': per_page,
        'has_more': (page * per_page) < total,
    }), 200


@assets_bp.route('/<int:asset_id>/preview', methods=['GET'])
@jwt_required()
def preview_asset(asset_id):
    """Preview an asset inline when the mime type supports it."""
    asset = Asset.query.get(asset_id)
    if not asset or asset.is_soft_deleted():
        return jsonify({'error': 'Asset not found'}), 404

    campaign = asset.campaign
    if not _can_access_library(campaign, current_user):
        return jsonify({'error': 'Forbidden'}), 403
    if not _handout_visible_to(asset, campaign, current_user):
        return jsonify({'error': 'Forbidden'}), 403

    if not asset.is_previewable():
        return jsonify({'error': 'Preview not supported for this asset type'}), 400

    storage = get_storage_adapter()
    try:
        content = storage.download(asset.storage_key)
    except Exception as e:
        return jsonify({'error': f'Preview failed: {str(e)}'}), 500

    response = send_file(
        io.BytesIO(content),
        mimetype=asset.mime_type,
        as_attachment=False,
        download_name=asset.filename,
    )
    response.headers['Content-Disposition'] = f'inline; filename="{asset.filename}"'
    return response


@assets_bp.route('/<int:asset_id>/thumbnail', methods=['GET'])
@jwt_required()
def get_asset_thumbnail(asset_id):
    """Serve an asset's thumbnail, falling back to the full preview when
    no thumbnail exists (older asset, or thumbnailing failed at upload
    time) so the UI grid degrades instead of breaking."""
    asset = Asset.query.get(asset_id)
    if not asset or asset.is_soft_deleted():
        return jsonify({'error': 'Asset not found'}), 404

    campaign = asset.campaign
    if not _can_access_library(campaign, current_user):
        return jsonify({'error': 'Forbidden'}), 403
    if not _handout_visible_to(asset, campaign, current_user):
        return jsonify({'error': 'Forbidden'}), 403

    storage = get_storage_adapter()

    if asset.thumbnail_key:
        try:
            content = storage.download(asset.thumbnail_key)
        except Exception as e:
            return jsonify({'error': f'Thumbnail failed: {str(e)}'}), 500

        response = send_file(
            io.BytesIO(content),
            mimetype='image/jpeg',
            as_attachment=False,
            download_name=asset.filename,
        )
        response.headers['Content-Disposition'] = f'inline; filename="{asset.filename}"'
        return response

    # No thumbnail available - fall back to the full preview.
    if not asset.is_previewable():
        return jsonify({'error': 'Preview not supported for this asset type'}), 400

    try:
        content = storage.download(asset.storage_key)
    except Exception as e:
        return jsonify({'error': f'Preview failed: {str(e)}'}), 500

    response = send_file(
        io.BytesIO(content),
        mimetype=asset.mime_type,
        as_attachment=False,
        download_name=asset.filename,
    )
    response.headers['Content-Disposition'] = f'inline; filename="{asset.filename}"'
    return response


@assets_bp.route('/<int:asset_id>/download', methods=['GET'])
@jwt_required()
def download_asset(asset_id):
    """Download asset file."""
    asset = Asset.query.get(asset_id)
    if not asset or asset.is_soft_deleted():
        return jsonify({'error': 'Asset not found'}), 404

    # Check permission
    campaign = asset.campaign
    if not _can_access_library(campaign, current_user):
        return jsonify({'error': 'Forbidden'}), 403
    if not _handout_visible_to(asset, campaign, current_user):
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
@require_campaign_access(can_view_campaign)
def upload_asset(campaign_id):
    """Upload new asset to campaign.

    F4: the route itself only requires active membership now (any Player
    included) -- non-token asset types (map, handout, generic image)
    still require campaign-editor rights, enforced explicitly below once
    asset_type is known. This lets a player upload art for a token they
    own (the play-table "Bild setzen..." control, gated correctly at the
    socket layer to owner-or-DM per token) without opening up maps or
    handouts, which stay DM/CO_DM-only exactly as before.
    """
    campaign = Campaign.query.get(campaign_id)

    # Check file presence
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file_obj = request.files['file']
    asset_type = str(request.form.get('asset_type', 'image')).strip().lower() or 'image'  # map, token, handout, image
    if asset_type not in LIBRARY_ALLOWED_ASSET_TYPES:
        return jsonify({'error': 'Unsupported asset type'}), 400

    if asset_type != 'token' and not can_edit_campaign(current_user, campaign):
        return jsonify({'error': 'Forbidden'}), 403

    # M20: Validate upload
    try:
        validation = validate_upload(file_obj, current_user)
    except UploadError as e:
        return jsonify({'error': str(e)}), 400

    # Fixed 2026-09-04 (adversarial audit): the OLD quota enforcement was
    # a plain read-modify-write AFTER storage.upload() below -- N
    # concurrent uploads under the cap could all pass validate_upload's
    # own advisory can_upload_asset check, all write to storage, and the
    # last commit clobbers the others' increments (permanent quota
    # bypass). try_reserve_storage is the real, atomic enforcement, and
    # runs BEFORE the storage write so a losing race costs nothing to
    # unwind -- no orphaned file, no Asset row to clean up.
    if not try_reserve_storage(current_user, validation['size_bytes']):
        return jsonify({'error': 'Storage quota exceeded'}), 507

    # M21: Upload to storage
    storage = get_storage_adapter()
    file_key = f'campaigns/{campaign_id}/assets/{validation["checksum_md5"][:8]}-{validation["filename"]}'

    try:
        storage.upload(file_key, validation['content'])
    except Exception as e:
        release_storage(current_user, validation['size_bytes'])
        return jsonify({'error': f'Storage upload failed: {str(e)}'}), 500

    # M4: Generate and store a thumbnail for image uploads. Best-effort -
    # a thumbnailing failure must not fail the overall upload.
    thumbnail_key = None
    if validation['mime_type'].startswith('image/'):
        try:
            thumbnail_bytes = generate_thumbnail(validation['content'])
            thumbnail_key = (
                f'campaigns/{campaign_id}/assets/thumbs/'
                f'{validation["checksum_md5"][:8]}-{validation["filename"]}.jpg'
            )
            storage.upload(thumbnail_key, thumbnail_bytes)
        except Exception as e:
            logger.warning(
                'Thumbnail generation failed for upload %s: %s',
                validation['filename'], e,
            )
            thumbnail_key = None

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
        thumbnail_key=thumbnail_key,
    )
    db.session.add(asset)
    db.session.commit()

    # Storage usage was already atomically reserved by try_reserve_storage
    # above, before the file was even written -- no separate increment
    # needed (or safe to do) here anymore.

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

    response = {
        'asset_id': asset.id,
        'filename': asset.filename,
        'size_bytes': asset.size_bytes,
        'asset_type': asset_type,
        'message': 'Asset uploaded successfully',
    }
    if 'width' in validation and 'height' in validation:
        response['width'] = validation['width']
        response['height'] = validation['height']

    return jsonify(response), 201


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
def rollback_asset(asset_id, version_number):
    """Rollback asset to previous version.

    Fixed 2026-09-04 (adversarial audit): @require_campaign_access
    resolves campaign_id from the route's own URL kwargs
    (vtt/permissions.py) -- this route only ever has asset_id, so that
    always evaluated to None, Campaign.query.get(None) always failed,
    and this endpoint 404'd unconditionally for EVERY caller, DM
    included. Not exploitable (fails closed), just permanently dead.
    Same manual look-up-then-check pattern set_asset_visibility already
    uses for the same reason."""
    asset = Asset.query.get(asset_id)
    if not asset:
        return jsonify({'error': 'Asset not found'}), 404
    if not can_edit_campaign(current_user, asset.campaign):
        return jsonify({'error': 'Forbidden'}), 403

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


# ===== Visibility (reveal/hide a handout) =====

@assets_bp.route('/<int:asset_id>/visibility', methods=['PATCH'])
@jwt_required()
def set_asset_visibility(asset_id):
    """Fixed 2026-09-02: is_public existed on every Asset (default False)
    but nothing ever set it after upload -- there was no way for a DM to
    actually reveal a handout once it was hidden. This is the missing
    write side of _handout_visible_to's read-side gate.

    Note: NOT @require_campaign_access(can_edit_campaign) -- that
    decorator resolves campaign_id from the route's own URL kwargs
    (vtt/permissions.py), which this asset_id-only route never has; it
    would silently 404 every call. Every other asset_id-keyed route in
    this file (preview/thumbnail/download/delete) already works around
    this the same way: look the asset up first, check permission
    against asset.campaign manually."""
    asset = Asset.query.get(asset_id)
    if not asset or asset.is_soft_deleted():
        return jsonify({'error': 'Asset not found'}), 404

    campaign = asset.campaign
    if not can_edit_campaign(current_user, campaign):
        return jsonify({'error': 'Forbidden'}), 403

    data = request.get_json(silent=True) or {}
    if 'is_public' not in data or not isinstance(data['is_public'], bool):
        return jsonify({'error': 'is_public (boolean) is required'}), 400

    asset.is_public = data['is_public']
    db.session.commit()

    log_audit(
        action='asset_visibility_changed',
        resource_type='asset',
        resource_id=asset.id,
        details={'filename': asset.filename, 'is_public': asset.is_public},
        performed_by=current_user
    )

    return jsonify({'asset_id': asset.id, 'is_public': asset.is_public}), 200


# ===== M19: Delete (soft) =====

@assets_bp.route('/<int:asset_id>/delete', methods=['DELETE'])
@jwt_required()
def delete_asset(asset_id):
    """Soft-delete asset (kept for retention, can be restored).

    Fixed 2026-09-04 (adversarial audit): same @require_campaign_access
    footgun as rollback_asset above -- this route also only ever has
    asset_id, so the decorator's campaign_id resolution always failed
    and this 404'd unconditionally for every caller. Dead, not
    exploitable."""
    asset = Asset.query.get(asset_id)
    if not asset or asset.is_soft_deleted():
        return jsonify({'error': 'Asset not found'}), 404
    if not can_edit_campaign(current_user, asset.campaign):
        return jsonify({'error': 'Forbidden'}), 403

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
