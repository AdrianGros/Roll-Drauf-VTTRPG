"""M65: Page content endpoints - editable copy, separate from code.

GET is public (unauthenticated) since every page load needs the current
text to render. Writes are admin-only.
"""

from flask import Blueprint, jsonify, request
from vtt.extensions import db
from vtt.models import PageContent
from vtt.permissions import has_platform_role
from vtt.utils.time import utcnow
from vtt.security import current_user

page_content_bp = Blueprint('page_content', __name__, url_prefix='/api/content')

MAX_TEXT_LENGTH = 4000


@page_content_bp.route('/<page_key>', methods=['GET'])
def get_page_content(page_key):
    """Return {content_key: text} for one page - what the frontend renders from."""
    return jsonify(PageContent.get_content_map(page_key)), 200


@page_content_bp.route('/admin/pages', methods=['GET'])
@has_platform_role('admin', 'owner')
def list_content_pages():
    """Distinct page_key values, for the admin editor's page selector."""
    rows = db.session.query(PageContent.page_key).distinct().order_by(PageContent.page_key).all()
    return jsonify({'pages': [row[0] for row in rows]}), 200


@page_content_bp.route('/admin/<page_key>', methods=['GET'])
@has_platform_role('admin', 'owner')
def list_page_content_admin(page_key):
    """Full rows (with description/updated_at) for the admin editor."""
    rows = (
        PageContent.query
        .filter_by(page_key=page_key)
        .order_by(PageContent.content_key)
        .all()
    )
    return jsonify({'entries': [row.serialize() for row in rows]}), 200


@page_content_bp.route('/admin/<page_key>/<content_key>', methods=['PUT'])
@has_platform_role('admin', 'owner')
def update_page_content(page_key, content_key):
    """Update one string's text. Only `text` is editable here - page_key/
    content_key/description are structural and stay code-owned."""
    entry = PageContent.query.filter_by(page_key=page_key, content_key=content_key).first()
    if not entry:
        return jsonify({'error': 'content entry not found'}), 404

    data = request.get_json() or {}
    text = data.get('text')
    if not isinstance(text, str) or not text.strip():
        return jsonify({'error': 'text is required'}), 400
    if len(text) > MAX_TEXT_LENGTH:
        return jsonify({'error': f'text must be under {MAX_TEXT_LENGTH} characters'}), 400

    entry.text = text
    entry.updated_at = utcnow()
    entry.updated_by_id = current_user.id if current_user else None
    db.session.commit()

    return jsonify({'entry': entry.serialize()}), 200
