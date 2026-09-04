"""M20: Upload security validation (MIME types, sizes, safety)."""

import hashlib
import io
import mimetypes
import re
from flask import current_app
from PIL import Image, UnidentifiedImageError

# M20: Allowed MIME types (whitelist)
ALLOWED_MIME_TYPES = {
    'image/jpeg', 'image/png', 'image/webp', 'image/gif',
    'application/json',  # Token/map configs
    'application/pdf',  # Handouts
    'text/plain',
}

# Fixed 2026-09-04 (adversarial audit): validate_mime_type only ever
# checked the CLIENT-SUPPLIED Content-Type header/filename extension --
# an attacker could label arbitrary bytes "image/png" and they'd sail
# straight through. Real-world impact was already reduced by this app's
# global X-Content-Type-Options: nosniff header and is_previewable()
# only allowing inline rendering for images/PDF (everything else forces
# as_attachment=True) -- but the check itself was still fake. Maps a
# claimed image/* MIME type to the actual format string Pillow's own
# decoder reports for the real bytes.
_IMAGE_MIME_TO_PIL_FORMAT = {
    'image/jpeg': 'JPEG',
    'image/png': 'PNG',
    'image/webp': 'WEBP',
    'image/gif': 'GIF',
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


def verify_content_matches_mime_type(file_content, mime_type):
    """Fixed 2026-09-04 (adversarial audit): the real content-vs-claim
    check, not just the header. Only enforced for the types that ever
    get INLINE rendering (images, PDF) -- text/plain and
    application/json are always served as_attachment=True regardless of
    content, so there's no rendering-context mismatch to exploit there,
    and "is this valid text" isn't a meaningful question anyway. Returns
    {'width': int, 'height': int} for a verified image (replaces the
    old separate, silently-swallowed-on-failure Image.open() call that
    used to run again later just for dimensions), or {} otherwise.
    Raises UploadError the same way every other validate_* function
    here does, so callers don't need a second exception type."""
    if mime_type in _IMAGE_MIME_TO_PIL_FORMAT:
        try:
            with Image.open(io.BytesIO(file_content)) as img:
                if img.format != _IMAGE_MIME_TO_PIL_FORMAT[mime_type]:
                    raise UploadError(
                        f'File content does not match claimed type {mime_type} '
                        f'(detected {img.format})'
                    )
                return {'width': img.size[0], 'height': img.size[1]}
        except UnidentifiedImageError:
            raise UploadError(f'File content is not a valid image (claimed {mime_type})')
    elif mime_type == 'application/pdf':
        if not file_content.startswith(b'%PDF-'):
            raise UploadError('File content is not a valid PDF (missing %PDF- header)')
    return {}


def compute_checksum_md5(file_content):
    """Compute MD5 checksum for integrity checks."""
    return hashlib.md5(file_content).hexdigest()


def validate_upload(file_obj, user, check_quota=True):
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
    mime_type = file_obj.content_type
    if not mime_type or mime_type == 'application/octet-stream':
        guessed_type, _ = mimetypes.guess_type(file_obj.filename or '')
        mime_type = guessed_type or mime_type
    validate_mime_type(mime_type)

    # 3. Read file content and check size
    file_content = file_obj.read()
    validate_file_size(file_content)

    # 4. Verify the actual bytes match the claimed MIME type (2026-09-04
    # fix) -- also extracts image dimensions in the same pass instead of
    # a separate, silently-swallowed-on-failure Image.open() call this
    # used to do later just for width/height.
    content_metadata = verify_content_matches_mime_type(file_content, mime_type)

    # 5. Check storage quota (M17 integration)
    if check_quota:
        from vtt.permissions import can_upload_asset
        size_mb = len(file_content) / 1024 / 1024
        allowed, msg = can_upload_asset(user, size_mb)
        if not allowed:
            raise UploadError(f'Storage quota exceeded: {msg}')

    # 6. Compute checksum
    checksum = compute_checksum_md5(file_content)

    result = {
        'filename': file_obj.filename,
        'mime_type': mime_type,
        'size_bytes': len(file_content),
        'checksum_md5': checksum,
        'content': file_content,
        **content_metadata,
    }

    return result
