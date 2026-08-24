"""Fixed guild metadata and user primary-guild membership."""

from vtt.extensions import db
from vtt.utils.time import utcnow


FIXED_GUILD_DEFINITIONS = (
    {
        "slug": "sternenwacht",
        "name": "Sternenwacht",
        "tagline": "Haltet den Blick auf das nächste Kapitel.",
        "description": "Die Sternenwacht sammelt Leserinnen und Leiter, die Kampagnen vorausschauen, Session-Pfade schliessen und den Weg zum nächsten Tischmoment offen halten.",
        "accent": "gold",
        "display_order": 10,
    },
    {
        "slug": "bernsteinkreis",
        "name": "Bernsteinkreis",
        "tagline": "Chroniken, Hinweise und lange Erinnerung.",
        "description": "Der Bernsteinkreis ordnet Geschichten, Figuren und Kampagnenspuren. Diese Gilde steht für Archiv, Orientierung und das ruhige Sammeln von Fortschritt im Buch.",
        "accent": "amber",
        "display_order": 20,
    },
    {
        "slug": "nebellaterne",
        "name": "Nebellaterne",
        "tagline": "Vorhut für unbekannte Wege.",
        "description": "Die Nebellaterne ist für Aufbruch, Entdeckung und neue Vorbereitungswege gedacht. Hier landen Spielerinnen und DMs, die gern als Erste neue Kapitel betreten.",
        "accent": "mist",
        "display_order": 30,
    },
    {
        "slug": "eichenbund",
        "name": "Eichenbund",
        "tagline": "Gemeinschaft, Ruhe und verlässliche Runden.",
        "description": "Der Eichenbund steht für stabile Heimathaeuser, eingespielte Runden und das gemeinsame Tragen von Vorbereitung, Session-Klarheit und wiederkehrenden Ritualen.",
        "accent": "forest",
        "display_order": 40,
    },
)


class Guild(db.Model):
    """Fixed meta-identity guild surface for the dashboard home."""

    __tablename__ = "guilds"

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(80), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    tagline = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    accent = db.Column(db.String(30), nullable=False, default="gold")
    display_order = db.Column(db.Integer, nullable=False, default=0, index=True)
    created_at = db.Column(db.DateTime, default=utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)

    def serialize(self, *, member_count: int = 0, is_primary: bool = False):
        return {
            "id": self.id,
            "slug": self.slug,
            "name": self.name,
            "tagline": self.tagline,
            "description": self.description,
            "accent": self.accent,
            "display_order": self.display_order,
            "member_count": int(member_count),
            "is_primary": bool(is_primary),
        }


class GuildMembership(db.Model):
    """Exactly one primary guild per user for the first dashboard guild layer."""

    __tablename__ = "guild_memberships"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True, index=True)
    guild_id = db.Column(db.Integer, db.ForeignKey("guilds.id"), nullable=False, index=True)
    joined_at = db.Column(db.DateTime, default=utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)

    user = db.relationship("User", backref=db.backref("guild_membership", uselist=False, cascade="all, delete-orphan"))
    guild = db.relationship("Guild", backref=db.backref("memberships", cascade="all, delete-orphan", lazy=True))

    def serialize(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "guild_id": self.guild_id,
            "joined_at": self.joined_at.isoformat() if self.joined_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


def ensure_fixed_guilds():
    """Create the four fixed guilds if they are missing."""
    existing = {guild.slug: guild for guild in Guild.query.all()}
    changed = False

    for definition in FIXED_GUILD_DEFINITIONS:
        guild = existing.get(definition["slug"])
        if guild is None:
            guild = Guild(**definition)
            db.session.add(guild)
            changed = True
            continue

        for field in ("name", "tagline", "description", "accent", "display_order"):
            value = definition[field]
            if getattr(guild, field) != value:
                setattr(guild, field, value)
                changed = True

    if changed:
        db.session.commit()

    return Guild.query.order_by(Guild.display_order.asc(), Guild.id.asc()).all()
