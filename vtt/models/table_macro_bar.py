"""Personal hotbar macros at the table: one row per person and character.

The slots name sheet rolls ({kind, key}) of vtt.characters.sheet_link; the
table rolls them through the existing sheet-roll route, so permissions and
the target table are checked there on every use.
"""

from vtt.extensions import db
from vtt.utils.time import utcnow

MAX_MACRO_SLOTS = 10


class TableMacroBar(db.Model):
    __tablename__ = "table_macro_bars"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    character_id = db.Column(db.Integer, db.ForeignKey("characters.id", ondelete="CASCADE"),
                             nullable=False, index=True)
    slots = db.Column(db.JSON, nullable=False, default=list)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)

    __table_args__ = (
        db.UniqueConstraint("user_id", "character_id", name="uq_table_macro_bar_user_character"),
    )
