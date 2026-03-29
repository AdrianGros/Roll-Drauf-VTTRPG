"""M46: Theme management endpoints for spellbook customization."""

from flask import Blueprint, request, jsonify
from vtt_app.extensions import db
from vtt_app.models import AppThemeSettings
from vtt_app.permissions import has_platform_role
from vtt_app.utils.time import utcnow

theme_bp = Blueprint('theme', __name__, url_prefix='/api/theme')


@theme_bp.route('/settings', methods=['GET'])
def get_theme_settings():
    """Get current active theme settings."""
    theme = AppThemeSettings.get_active_theme()
    if not theme:
        return jsonify({'error': 'No active theme found'}), 404

    return jsonify({
        'theme': theme.serialize(),
        'css_variables': theme.get_css_variables()
    }), 200


@theme_bp.route('/admin/update', methods=['POST'])
@has_platform_role('admin')
def update_theme():
    """Update theme settings (admin only)."""
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    theme = AppThemeSettings.get_active_theme()

    # Validate color format (simple hex validation)
    color_fields = ['primary_color', 'accent_color', 'text_color', 'background_color']
    for field in color_fields:
        if field in data:
            color = data[field]
            if not isinstance(color, str) or not color.startswith('#') or len(color) != 7:
                return jsonify({'error': f'Invalid color format for {field}'}), 400
            setattr(theme, field, color)

    # Update other fields
    if 'font_heading' in data:
        theme.font_heading = data['font_heading']
    if 'font_body' in data:
        theme.font_body = data['font_body']
    if 'book_animation_speed' in data:
        try:
            speed = float(data['book_animation_speed'])
            if speed <= 0 or speed > 10:
                return jsonify({'error': 'Animation speed must be between 0 and 10 seconds'}), 400
            theme.book_animation_speed = speed
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid animation speed'}), 400
    if 'key_code_prefix' in data:
        prefix = data['key_code_prefix'].upper()
        if not prefix.isalnum() or len(prefix) > 10:
            return jsonify({'error': 'Key prefix must be alphanumeric and max 10 characters'}), 400
        theme.key_code_prefix = prefix

    theme.updated_at = utcnow()
    db.session.commit()

    return jsonify({
        'message': 'Theme updated successfully',
        'theme': theme.serialize(),
        'css_variables': theme.get_css_variables()
    }), 200


@theme_bp.route('/admin/reset', methods=['POST'])
@has_platform_role('admin')
def reset_theme():
    """Reset theme to default settings (admin only)."""
    theme = AppThemeSettings.get_active_theme()

    # Reset to defaults
    theme.primary_color = '#4a235a'
    theme.accent_color = '#d4af37'
    theme.text_color = '#2a2a2a'
    theme.background_color = '#f5e6d3'
    theme.font_heading = "'Georgia', serif"
    theme.font_body = "'Segoe UI', sans-serif"
    theme.book_animation_speed = 2.5
    theme.key_code_prefix = 'SPELL'
    theme.updated_at = utcnow()

    db.session.commit()

    return jsonify({
        'message': 'Theme reset to default successfully',
        'theme': theme.serialize(),
        'css_variables': theme.get_css_variables()
    }), 200


@theme_bp.route('/admin/customize', methods=['POST'])
@has_platform_role('admin')
def customize_theme():
    """
    Customize theme with validation and return CSS variables for preview.

    Request body:
    {
        "primary_color": "#4a235a",
        "accent_color": "#d4af37",
        "text_color": "#2a2a2a",
        "background_color": "#f5e6d3",
        "font_heading": "'Georgia', serif",
        "font_body": "'Segoe UI', sans-serif",
        "book_animation_speed": 2.5,
        "key_code_prefix": "SPELL"
    }
    """
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    # Validate before applying
    color_fields = ['primary_color', 'accent_color', 'text_color', 'background_color']
    for field in color_fields:
        if field in data:
            color = data[field]
            if not isinstance(color, str) or not color.startswith('#') or len(color) != 7:
                return jsonify({'error': f'Invalid color format for {field}'}), 400

    # Build preview CSS variables
    theme = AppThemeSettings.get_active_theme()
    preview_vars = theme.get_css_variables()

    # Update with new values for preview
    if 'primary_color' in data:
        preview_vars['--vtt-primary'] = data['primary_color']
    if 'accent_color' in data:
        preview_vars['--vtt-accent'] = data['accent_color']
        preview_vars['--vtt-border'] = data['accent_color']
    if 'text_color' in data:
        preview_vars['--vtt-text'] = data['text_color']
    if 'background_color' in data:
        preview_vars['--vtt-bg'] = data['background_color']
    if 'font_heading' in data:
        preview_vars['--vtt-font-heading'] = data['font_heading']
    if 'font_body' in data:
        preview_vars['--vtt-font-body'] = data['font_body']
    if 'book_animation_speed' in data:
        try:
            speed = float(data['book_animation_speed'])
            if speed <= 0 or speed > 10:
                return jsonify({'error': 'Animation speed must be between 0 and 10 seconds'}), 400
            preview_vars['--vtt-book-animation-speed'] = f'{speed}s'
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid animation speed'}), 400

    return jsonify({
        'message': 'Theme preview generated',
        'css_variables': preview_vars,
        'ready_to_apply': True
    }), 200
