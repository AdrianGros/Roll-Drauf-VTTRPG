"""Editable page content strings.

Externalizes user-facing text (button labels, headings, copy) from code so
non-technical staff can edit wording via the admin content editor without a
redeploy, ahead of the end-of-year test phase. Code keeps the *structure* and
*logic*; this table holds the *words*.

Dynamic values (counts, names, etc.) that used to be woven directly into a
JS template literal are represented as `{placeholder}` tokens in the stored
text (e.g. "{count} Kampagnen") - the frontend substitutes them at render
time. Editors can move/reword around a placeholder but the token itself must
stay intact for the substitution to work.
"""

from vtt.extensions import db
from vtt.utils.time import utcnow


class PageContent(db.Model):
    """One editable text string, scoped to a page and a key within that page."""

    __tablename__ = 'page_content'

    id = db.Column(db.Integer, primary_key=True)

    # 'shared' for text reused across multiple pages (ribbon, Play Launch
    # modal, ...); otherwise the page it belongs to (e.g. 'dashboard').
    page_key = db.Column(db.String(50), nullable=False, index=True)
    content_key = db.Column(db.String(150), nullable=False)

    text = db.Column(db.Text, nullable=False)
    description = db.Column(db.String(255))  # editor-facing hint: where/what this is

    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)
    updated_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    updated_by = db.relationship('User', foreign_keys=[updated_by_id])

    __table_args__ = (
        db.UniqueConstraint('page_key', 'content_key', name='uq_page_content_page_key_content_key'),
    )

    def serialize(self):
        return {
            'id': self.id,
            'page_key': self.page_key,
            'content_key': self.content_key,
            'text': self.text,
            'description': self.description,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'updated_by': self.updated_by.username if self.updated_by else None,
        }

    def __repr__(self):
        return f'<PageContent {self.page_key}:{self.content_key}>'

    @classmethod
    def get_content_map(cls, page_key):
        """Return {content_key: text} for a page - what the frontend fetches."""
        rows = cls.query.filter_by(page_key=page_key).all()
        return {row.content_key: row.text for row in rows}

    @classmethod
    def ensure_defaults(cls, definitions):
        """Insert any (page_key, content_key) pairs in `definitions` that don't
        already exist. Never touches existing rows - editors' changes survive
        every deploy. `definitions` is an iterable of dicts with page_key,
        content_key, text, and optionally description."""
        existing = {(row.page_key, row.content_key) for row in cls.query.all()}
        added = False

        for definition in definitions:
            key = (definition['page_key'], definition['content_key'])
            if key in existing:
                continue
            db.session.add(cls(
                page_key=definition['page_key'],
                content_key=definition['content_key'],
                text=definition['text'],
                description=definition.get('description'),
            ))
            existing.add(key)
            added = True

        if added:
            db.session.commit()
