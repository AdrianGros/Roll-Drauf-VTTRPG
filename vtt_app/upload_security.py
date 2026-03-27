"""M20: Upload security validation (MIME types, sizes, safety)."""

import hashlib
import re
from flask import current_app

# M20: Allowed MIME types (whitelist)
ALLOWED_MIME_TYPES = {
    'image/jpeg', 'image/png', 'image/webp', 'image/gif',
    'application/json',  # Token/map configs
    'application/pdf',  # Handouts
    'text/plain',
}

MAX_FILE_SIZE_MB = 50
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

# Dangerous filename patterns
DANGEROUS_PATTERNS = [
    r'\.\./',  # Path traversal
    r'[<>:"|?*]',  # Invalid chars
    r'^\.+$',  # Hidden files
]


class UploadError(Exception):
    """Upload validation error."""
    pass


def is_filename_safe(filename):
    """Check if filename is safe (no path traversal, etc)."""
    if not filename:
        return False

    # Check length
    if len(filename) > 255:
        return False

    # Check for dangerous patterns
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, filename):
            return False

    return True


def validate_mime_type(mime_type):
    """Check if MIME type is whitelisted."""
    if mime_type not in ALLOWED_MIME_TYPES:
        raise UploadError(f'Forbidden MIME type: {mime_type}. Allowed: {ALLOWED_MIME_TYPES}')
    return True


def validate_file_size(file_content):
    """Check if file size is within limits."""
    if len(file_content) > MAX_FILE_SIZE_BYTES:
        raise UploadError(f'File too large. Max {MAX_FILE_SIZE_MB}MB, got {len(file_content) / 1024 / 1024:.1f}MB')
    return True


def compute_checksum_md5(file_content):
    """Compute MD5 checksum for integrity checks."""
    return hashlib.md5(file_content).hexdigest()


def validate_upload(file_obj, user):
    """
    Validate file upload.

    Args:
        file_obj: Werkzeug FileStorage object
        user: Current user

    Returns:
        dict with validation result and metadata

    Raises:
        UploadError: If validation fails
    """
    # 1. Check filename safety
    if not is_filename_safe(file_obj.filename):
        raise UploadError(f'Invalid filename: {file_obj.filename}')

    # 2. Check MIME type
    validate_mime_type(file_obj.content_type)

    # 3. Read file content and check size
    file_content = file_obj.read()
    validate_file_size(file_content)

    # 4. Check storage quota (M17 integration)
    from vtt_app.permissions import can_upload_asset
    size_mb = len(file_content) / 1024 / 1024
    allowed, msg = can_upload_asset(user, size_mb)
    if not allowed:
        raise UploadError(f'Storage quota exceeded: {msg}')

    # 5. Compute checksum
    checksum = compute_checksum_md5(file_content)

    return {
        'filename': file_obj.filename,
        'mime_type': file_obj.content_type,
        'size_bytes': len(file_content),
        'checksum_md5': checksum,
        'content': file_content,
    }
