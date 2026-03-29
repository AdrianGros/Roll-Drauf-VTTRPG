"""M38-M40: Registration key management endpoints for bulk generation and admin dashboard."""

import random
import string
import uuid
from flask import Blueprint, request, jsonify
from sqlalchemy import func, desc
from vtt_app.extensions import db, limiter
from vtt_app.models import RegistrationKey, User
from vtt_app.permissions import has_platform_role
from vtt_app.security import current_user
from vtt_app.utils.time import utcnow
from vtt_app.utils.audit import log_audit

registration_keys_bp = Blueprint('registration_keys', __name__, url_prefix='/api')

# ============= M38: BULK GENERATION =============


def _generate_key_code() -> str:
    """
    Generate a unique registration key in format: SPELL-XXXX-XXXX-XXXX

    Returns:
        str: Generated key code in the specified format
    """
    chars = string.ascii_uppercase + string.digits
    parts = [
        ''.join(random.choices(chars, k=4)),
        ''.join(random.choices(chars, k=4)),
        ''.join(random.choices(chars, k=4)),
    ]
    return f"SPELL-{'-'.join(parts)}"


def _ensure_unique_key() -> str:
    """
    Generate a key and ensure it doesn't already exist in database.

    Returns:
        str: Unique key code
    """
    max_attempts = 100
    for _ in range(max_attempts):
        key_code = _generate_key_code()
        if not RegistrationKey.query.filter_by(key_code=key_code).first():
            return key_code
    raise RuntimeError("Failed to generate unique key after 100 attempts")


@registration_keys_bp.route('/admin/keys/generate', methods=['POST'])
@has_platform_role('admin', 'owner')
@limiter.limit("10 per hour")
def generate_keys():
    """
    Generate a batch of registration keys.

    Expected JSON:
    {
        "count": 100,
        "tier": "dm",
        "batch_name": "Campaign Batch 1",
        "expires_in_days": 30  # optional
    }

    Returns:
        JSON with generated key codes and batch_id
    """
    data = request.get_json() or {}
    count = data.get('count', 1)
    tier = data.get('tier', 'player')
    batch_name = data.get('batch_name', f'Batch {uuid.uuid4().hex[:8]}')
    expires_in_days = data.get('expires_in_days')

    # Validation
    if not isinstance(count, int) or count < 1 or count > 10000:
        return jsonify({'error': 'count must be between 1 and 10000'}), 400

    valid_tiers = ['free', 'player', 'dm', 'headmaster']
    if tier not in valid_tiers:
        return jsonify({'error': f'tier must be one of {valid_tiers}'}), 400

    if not batch_name or len(batch_name) > 255:
        return jsonify({'error': 'batch_name must be 1-255 characters'}), 400

    # Generate batch ID
    batch_id = f"batch_{uuid.uuid4().hex[:12]}"

    # Calculate expiration if specified
    expires_at = None
    if expires_in_days and isinstance(expires_in_days, int) and expires_in_days > 0:
        from datetime import timedelta
        expires_at = utcnow() + timedelta(days=expires_in_days)

    # Generate all keys in transaction
    generated_keys = []
    try:
        for _ in range(count):
            key_code = _ensure_unique_key()
            key = RegistrationKey(
                key_code=key_code,
                key_name=batch_name,
                key_batch_id=batch_id,
                tier=tier,
                max_uses=1,
                uses_remaining=1,
                expires_at=expires_at,
            )
            db.session.add(key)
            generated_keys.append(key_code)

        db.session.commit()

        # Audit log
        log_audit(
            action='key_batch_generated',
            resource_type='registration_key',
            resource_id=None,
            details={
                'batch_id': batch_id,
                'batch_name': batch_name,
                'tier': tier,
                'count': count,
                'expires_at': expires_at.isoformat() if expires_at else None,
            },
            performed_by=current_user,
        )

        return jsonify({
            'batch_id': batch_id,
            'batch_name': batch_name,
            'tier': tier,
            'count': count,
            'keys': generated_keys,
            'expires_at': expires_at.isoformat() if expires_at else None,
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@registration_keys_bp.route('/admin/keys/batches', methods=['GET'])
@has_platform_role('admin', 'owner')
def list_batches():
    """
    List all registration key batches.

    Query params:
    - page: pagination page (default 1)
    - per_page: items per page (default 20)

    Returns:
        JSON with list of batches and pagination info
    """
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    if per_page < 1 or per_page > 100:
        per_page = 20

    # Get distinct batches with usage stats
    batches_query = db.session.query(
        RegistrationKey.key_batch_id,
        RegistrationKey.key_name,
        RegistrationKey.tier,
        RegistrationKey.created_at,
        func.count(RegistrationKey.id).label('total_count'),
        func.sum(func.cast(RegistrationKey.uses_remaining == 0, db.Integer)).label('used_count'),
        func.sum(func.cast(RegistrationKey.is_revoked, db.Integer)).label('revoked_count'),
    ).group_by(
        RegistrationKey.key_batch_id
    ).order_by(
        desc(RegistrationKey.created_at)
    ).paginate(page=page, per_page=per_page, error_out=False)

    batches = []
    for batch in batches_query.items:
        total = batch.total_count or 0
        used = batch.used_count or 0
        revoked = batch.revoked_count or 0
        usage_pct = (used / total * 100) if total > 0 else 0

        batches.append({
            'batch_id': batch.key_batch_id,
            'batch_name': batch.key_name,
            'tier': batch.tier,
            'created_at': batch.created_at.isoformat(),
            'total_keys': total,
            'used_keys': used,
            'revoked_keys': revoked,
            'available_keys': total - used - revoked,
            'usage_percent': round(usage_pct, 2),
        })

    return jsonify({
        'batches': batches,
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': batches_query.total,
            'pages': batches_query.pages,
        }
    }), 200


@registration_keys_bp.route('/admin/keys/batch/<batch_id>', methods=['GET'])
@has_platform_role('admin', 'owner')
def get_batch_details(batch_id):
    """
    Get detailed information about a specific batch.

    Query params:
    - page: pagination for keys (default 1)
    - per_page: keys per page (default 20)
    - status: filter by 'available', 'used', 'revoked' (optional)

    Returns:
        JSON with batch details and paginated key list
    """
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    status = request.args.get('status')

    if per_page < 1 or per_page > 100:
        per_page = 20

    # Get batch metadata
    batch_keys = RegistrationKey.query.filter_by(key_batch_id=batch_id)
    batch_count = batch_keys.count()

    if batch_count == 0:
        return jsonify({'error': 'Batch not found'}), 404

    # Get first key for batch metadata
    first_key = batch_keys.first()
    total_keys = batch_count
    used_keys = batch_keys.filter_by(uses_remaining=0).count()
    revoked_keys = batch_keys.filter_by(is_revoked=True).count()
    available_keys = total_keys - used_keys - revoked_keys

    # Filter by status
    query = batch_keys
    if status == 'available':
        query = query.filter(
            (RegistrationKey.uses_remaining > 0) &
            (RegistrationKey.is_revoked == False)
        )
    elif status == 'used':
        query = query.filter_by(uses_remaining=0)
    elif status == 'revoked':
        query = query.filter_by(is_revoked=True)

    # Paginate
    paginated = query.paginate(page=page, per_page=per_page, error_out=False)

    keys = []
    for key in paginated.items:
        keys.append({
            'id': key.id,
            'key_code': key.key_code,
            'uses_remaining': key.uses_remaining,
            'used_at': key.used_at.isoformat() if key.used_at else None,
            'expires_at': key.expires_at.isoformat() if key.expires_at else None,
            'is_revoked': key.is_revoked,
            'used_by_id': key.used_by_id,
            'used_by_username': key.used_by.username if key.used_by else None,
        })

    return jsonify({
        'batch_id': batch_id,
        'batch_name': first_key.key_name,
        'tier': first_key.tier,
        'created_at': first_key.created_at.isoformat(),
        'total_keys': total_keys,
        'used_keys': used_keys,
        'revoked_keys': revoked_keys,
        'available_keys': available_keys,
        'usage_percent': round((used_keys / total_keys * 100) if total_keys > 0 else 0, 2),
        'keys': keys,
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': paginated.total,
            'pages': paginated.pages,
        }
    }), 200


@registration_keys_bp.route('/admin/keys/batch/<batch_id>/export', methods=['GET'])
@has_platform_role('admin', 'owner')
def export_batch_csv(batch_id):
    """
    Export batch keys as CSV for distribution.

    Returns:
        CSV file with key codes and metadata
    """
    keys = RegistrationKey.query.filter_by(key_batch_id=batch_id).all()

    if not keys:
        return jsonify({'error': 'Batch not found'}), 404

    batch = keys[0]
    csv_data = 'key_code,tier,created_at,expires_at,status\n'

    for key in keys:
        status = 'revoked' if key.is_revoked else ('used' if key.uses_remaining == 0 else 'available')
        expires = key.expires_at.isoformat() if key.expires_at else ''
        csv_data += f'{key.key_code},{key.tier},{key.created_at.isoformat()},{expires},{status}\n'

    return csv_data, 200, {
        'Content-Type': 'text/csv',
        'Content-Disposition': f'attachment; filename="keys_{batch_id}.csv"'
    }


# ============= M40: ADMIN DASHBOARD =============

@registration_keys_bp.route('/admin/keys/stats', methods=['GET'])
@has_platform_role('admin', 'owner')
def get_key_stats():
    """
    Get overall registration key statistics.

    Returns:
        JSON with key statistics by tier and status
    """
    total_keys = RegistrationKey.query.count()
    used_keys = RegistrationKey.query.filter_by(uses_remaining=0).count()
    revoked_keys = RegistrationKey.query.filter_by(is_revoked=True).count()
    available_keys = total_keys - used_keys - revoked_keys

    # Stats by tier
    tier_stats = {}
    for tier in ['free', 'player', 'dm', 'headmaster']:
        tier_total = RegistrationKey.query.filter_by(tier=tier).count()
        tier_used = RegistrationKey.query.filter_by(tier=tier, uses_remaining=0).count()
        tier_revoked = RegistrationKey.query.filter_by(tier=tier, is_revoked=True).count()
        tier_available = tier_total - tier_used - tier_revoked

        tier_stats[tier] = {
            'total': tier_total,
            'used': tier_used,
            'revoked': tier_revoked,
            'available': tier_available,
            'usage_percent': round((tier_used / tier_total * 100) if tier_total > 0 else 0, 2),
        }

    return jsonify({
        'total': total_keys,
        'used': used_keys,
        'revoked': revoked_keys,
        'available': available_keys,
        'usage_percent': round((used_keys / total_keys * 100) if total_keys > 0 else 0, 2),
        'by_tier': tier_stats,
    }), 200


@registration_keys_bp.route('/admin/keys', methods=['GET'])
@has_platform_role('admin', 'owner')
def list_keys():
    """
    Paginated list of registration keys with filters.

    Query params:
    - batch_id: filter by batch (optional)
    - tier: filter by tier (optional)
    - status: filter by 'available', 'used', 'revoked' (optional)
    - page: pagination page (default 1)
    - per_page: items per page (default 20)

    Returns:
        JSON with key list and pagination info
    """
    batch_id = request.args.get('batch_id')
    tier = request.args.get('tier')
    status = request.args.get('status')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    if per_page < 1 or per_page > 100:
        per_page = 20

    query = RegistrationKey.query

    if batch_id:
        query = query.filter_by(key_batch_id=batch_id)

    if tier:
        query = query.filter_by(tier=tier)

    if status == 'available':
        query = query.filter(
            (RegistrationKey.uses_remaining > 0) &
            (RegistrationKey.is_revoked == False)
        )
    elif status == 'used':
        query = query.filter_by(uses_remaining=0)
    elif status == 'revoked':
        query = query.filter_by(is_revoked=True)

    paginated = query.order_by(desc(RegistrationKey.created_at)).paginate(
        page=page, per_page=per_page, error_out=False
    )

    keys = []
    for key in paginated.items:
        keys.append({
            'id': key.id,
            'key_code': key.key_code,
            'key_batch_id': key.key_batch_id,
            'tier': key.tier,
            'uses_remaining': key.uses_remaining,
            'max_uses': key.max_uses,
            'created_at': key.created_at.isoformat(),
            'used_at': key.used_at.isoformat() if key.used_at else None,
            'expires_at': key.expires_at.isoformat() if key.expires_at else None,
            'is_revoked': key.is_revoked,
            'used_by_id': key.used_by_id,
            'used_by_username': key.used_by.username if key.used_by else None,
        })

    return jsonify({
        'keys': keys,
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': paginated.total,
            'pages': paginated.pages,
        }
    }), 200


@registration_keys_bp.route('/admin/keys/<int:key_id>/revoke', methods=['POST'])
@has_platform_role('admin', 'owner')
def revoke_key(key_id):
    """
    Revoke a specific registration key.

    Expected JSON:
    {
        "reason": "Unauthorized distribution"  # optional
    }

    Returns:
        JSON with revoked key details
    """
    data = request.get_json() or {}
    reason = data.get('reason', 'Admin revocation')

    key = RegistrationKey.query.get(key_id)
    if not key:
        return jsonify({'error': 'Key not found'}), 404

    if key.is_revoked:
        return jsonify({'error': 'Key is already revoked'}), 400

    key.revoke()

    # Audit log
    log_audit(
        action='key_revoked',
        resource_type='registration_key',
        resource_id=key.id,
        details={
            'key_code': key.key_code,
            'reason': reason,
        },
        performed_by=current_user,
    )

    return jsonify({'key': key.serialize()}), 200


@registration_keys_bp.route('/admin/keys/<int:key_id>/unrestrict', methods=['POST'])
@has_platform_role('admin', 'owner')
def unrestrict_key(key_id):
    """
    Add one more use to a registration key.

    Returns:
        JSON with updated key details
    """
    key = RegistrationKey.query.get(key_id)
    if not key:
        return jsonify({'error': 'Key not found'}), 404

    if key.is_revoked:
        return jsonify({'error': 'Cannot unrestrict a revoked key'}), 400

    key.uses_remaining += 1
    db.session.commit()

    # Audit log
    log_audit(
        action='key_unrestricted',
        resource_type='registration_key',
        resource_id=key.id,
        details={
            'key_code': key.key_code,
            'uses_remaining': key.uses_remaining,
        },
        performed_by=current_user,
    )

    return jsonify({'key': key.serialize()}), 200


# ============= M46: PDF KEY DISTRIBUTION =============


@registration_keys_bp.route('/admin/keys/batch/<batch_id>/pdf', methods=['GET'])
@has_platform_role('admin', 'owner')
def export_batch_pdf(batch_id):
    """
    Export batch keys as a formatted PDF document for printing/distribution.

    Returns:
        PDF file with spellbook-themed key presentation
    """
    from vtt_app.pdf_templates.key_batch import generate_key_batch_pdf
    from vtt_app.models import AppThemeSettings
    from flask import send_file
    from io import BytesIO

    # Get batch keys
    keys = RegistrationKey.query.filter_by(key_batch_id=batch_id).all()

    if not keys:
        return jsonify({'error': 'Batch not found'}), 404

    # Get batch metadata from first key
    first_key = keys[0]

    # Prepare key data for PDF
    keys_data = []
    for key in keys:
        keys_data.append({
            'key_code': key.key_code,
            'name': first_key.key_name,
            'tier': key.tier,
        })

    # Get active theme for colors
    theme = AppThemeSettings.get_active_theme()
    theme_colors = {
        'primary': theme.primary_color,
        'accent': theme.accent_color,
        'text': theme.text_color,
        'bg': theme.background_color,
    } if theme else None

    # Generate PDF
    pdf_content = generate_key_batch_pdf(batch_id, keys_data, theme_colors)

    if pdf_content is None:
        return jsonify({'error': 'PDF generation failed'}), 500

    # Return PDF file
    return send_file(
        BytesIO(pdf_content) if isinstance(pdf_content, bytes) else pdf_content,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'spellbook-keys-{batch_id}.pdf'
    )
