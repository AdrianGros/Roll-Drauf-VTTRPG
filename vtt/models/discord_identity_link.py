"""Discord identity link model."""

import re

from vtt.extensions import db
from vtt.utils.time import utcnow


class DiscordIdentityLink(db.Model):
    """Stable link between a VTT user and a Discord user identity."""

    __tablename__ = "discord_identity_links"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False, index=True)
    discord_user_id = db.Column(db.String(32), unique=True, nullable=False, index=True)
    discord_guild_id = db.Column(db.String(32), index=True)
    discord_username_snapshot = db.Column(db.String(100))
    avatar_hash = db.Column(db.String(64))
    bot_verified_role = db.Column(db.String(32))
    link_status = db.Column(db.String(20), default="linked", nullable=False, index=True)
    linked_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    last_verified_at = db.Column(db.DateTime)
    revoked_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)

    user = db.relationship(
        "User",
        backref=db.backref("discord_identity_link", uselist=False),
    )

    def is_active(self) -> bool:
        return self.link_status == "linked" and self.revoked_at is None

    def revoke(self) -> None:
        self.link_status = "revoked"
        self.revoked_at = utcnow()

    def set_avatar_snapshot(self, value) -> None:
        self.avatar_hash = value if isinstance(value, str) and re.fullmatch(r'(?:a_)?[0-9a-f]{32}', value) else None

    def avatar_url(self) -> str | None:
        if not self.is_active() or not re.fullmatch(r'[0-9]{1,20}', self.discord_user_id or ''):
            return None
        if not re.fullmatch(r'(?:a_)?[0-9a-f]{32}', self.avatar_hash or ''):
            return None
        return f'https://cdn.discordapp.com/avatars/{self.discord_user_id}/{self.avatar_hash}.png?size=64'
