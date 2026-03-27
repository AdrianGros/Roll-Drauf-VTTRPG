"""Timezone-safe UTC helpers."""

from datetime import UTC, datetime


def utcnow() -> datetime:
    """Return a naive UTC datetime for DB compatibility."""
    return datetime.now(UTC).replace(tzinfo=None)

