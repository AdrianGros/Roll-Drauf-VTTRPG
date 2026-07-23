"""M4: Thumbnail generation for uploaded image assets."""

import io

from PIL import Image

# MIME types we know how to thumbnail. Non-image uploads (pdf/json/text) are
# skipped by the caller before this module is ever touched.
THUMBNAILABLE_MIME_TYPES = {
    'image/jpeg',
    'image/png',
    'image/webp',
    'image/gif',
}


def generate_thumbnail(content_bytes: bytes, max_dim: int = 320) -> bytes:
    """Generate a downscaled JPEG thumbnail for an in-memory image.

    Preserves aspect ratio (longest side capped at ``max_dim``). Images with
    an alpha/palette channel are flattened onto a white background so they
    can always be saved as JPEG.

    Raises whatever Pillow raises (e.g. ``UnidentifiedImageError``) on
    unreadable/corrupt input - callers are expected to catch and handle
    failures without aborting the wider upload.
    """
    with Image.open(io.BytesIO(content_bytes)) as image:
        image.load()
        image.thumbnail((max_dim, max_dim))

        if image.mode in ('RGBA', 'LA', 'P'):
            rgba = image.convert('RGBA')
            flattened = Image.new('RGB', rgba.size, (255, 255, 255))
            flattened.paste(rgba, mask=rgba.split()[-1])
            thumbnail = flattened
        elif image.mode != 'RGB':
            thumbnail = image.convert('RGB')
        else:
            thumbnail = image

        buffer = io.BytesIO()
        thumbnail.save(buffer, format='JPEG', quality=85)
        return buffer.getvalue()
