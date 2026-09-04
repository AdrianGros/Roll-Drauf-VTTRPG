"""Adversarial audit fix (2026-09-04): validate_mime_type only ever
checked the client-supplied Content-Type header/filename extension --
an attacker could label arbitrary bytes as an allowed MIME type and
they'd sail straight through. verify_content_matches_mime_type is the
real check, against the actual bytes.
"""

import io

import pytest
from PIL import Image

from vtt.upload_security import UploadError, verify_content_matches_mime_type


def _real_png_bytes():
    buffer = io.BytesIO()
    Image.new("RGB", (16, 12), (200, 50, 50)).save(buffer, format="PNG")
    return buffer.getvalue()


def _real_jpeg_bytes():
    buffer = io.BytesIO()
    Image.new("RGB", (16, 12), (50, 200, 50)).save(buffer, format="JPEG")
    return buffer.getvalue()


class TestImageContentVerification:
    def test_a_real_png_claiming_png_passes_and_returns_dimensions(self):
        result = verify_content_matches_mime_type(_real_png_bytes(), "image/png")
        assert result == {"width": 16, "height": 12}

    def test_html_disguised_as_png_is_rejected(self):
        """The actual attack: upload a file with Content-Type: image/png
        whose real bytes are HTML/JS, hoping some downstream consumer
        that doesn't respect X-Content-Type-Options: nosniff renders it."""
        fake = b"<html><body><script>alert(document.cookie)</script></body></html>"
        with pytest.raises(UploadError):
            verify_content_matches_mime_type(fake, "image/png")

    def test_a_real_jpeg_claiming_png_is_rejected(self):
        """Real image data, but the wrong format claimed -- Pillow can
        open it, the detected format just doesn't match."""
        with pytest.raises(UploadError):
            verify_content_matches_mime_type(_real_jpeg_bytes(), "image/png")

    def test_a_real_jpeg_claiming_jpeg_passes(self):
        result = verify_content_matches_mime_type(_real_jpeg_bytes(), "image/jpeg")
        assert result["width"] == 16
        assert result["height"] == 12

    def test_empty_bytes_claiming_an_image_is_rejected(self):
        with pytest.raises(UploadError):
            verify_content_matches_mime_type(b"", "image/gif")


class TestPdfContentVerification:
    def test_a_real_pdf_header_passes(self):
        # A minimal but real PDF header is enough for this check --
        # full PDF structural validation is out of scope, this closes
        # the "arbitrary bytes labeled application/pdf" gap, not "is
        # this a well-formed PDF."
        result = verify_content_matches_mime_type(b"%PDF-1.4\n...", "application/pdf")
        assert result == {}

    def test_non_pdf_content_claiming_pdf_is_rejected(self):
        with pytest.raises(UploadError):
            verify_content_matches_mime_type(b"just some plain text notes", "application/pdf")


class TestNonRenderedTypesAreUnchecked:
    """text/plain and application/json are never rendered inline
    (is_previewable() excludes both -- download_asset always forces
    as_attachment=True for them), so there's no rendering-context
    mismatch to exploit and no content check is applied."""

    def test_text_plain_content_is_never_checked(self):
        assert verify_content_matches_mime_type(b"\x00\x01\x02 anything at all", "text/plain") == {}

    def test_application_json_content_is_never_checked(self):
        assert verify_content_matches_mime_type(b"not actually json", "application/json") == {}
