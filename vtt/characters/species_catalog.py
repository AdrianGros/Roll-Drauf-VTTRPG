"""Which published homebrew Species a player may choose, and the pin a finished character keeps.

Access is decided here and only here: a personal publication is for its author, a campaign publication for the
campaign's owner and active members, and a global publication for every authenticated VTT user. A client-supplied Species id is always re-checked (draft save, evaluation,
finalize, rebuild, import). After finalizing, the character evaluates from its own pin (`srd.speciesPin`), so
later edits, deletions or new revisions of the Eagle document never reach it.
"""

import copy

from flask import current_app
from sqlalchemy import and_, or_

from vtt.creation_engine.models import CeSpeciesRevision
from vtt.extensions import db
from vtt.models import Campaign, CampaignMember, User
from vtt.rules_content import species_profiles as profiles
from vtt.rules_content.creator_rules import load_creator_data

UNAVAILABLE = "Diese Spezies ist für dich nicht (mehr) freigegeben."


def enabled():
    return bool(current_app.config.get("CE_PLAYABLE_SPECIES"))


def _campaign_ids(user_id):
    owned = {c.id for c in Campaign.query.filter(Campaign.owner_id == user_id, Campaign.deleted_at.is_(None))}
    joined = {
        row.campaign_id for row in CampaignMember.query.join(Campaign, Campaign.id == CampaignMember.campaign_id)
        .filter(CampaignMember.user_id == user_id, CampaignMember.status == "active", Campaign.deleted_at.is_(None))
    }
    return owned | joined


def can_select(user_id, row):
    if row is None:
        return False
    if row.scope_kind == "personal":
        return row.scope_id == user_id
    if row.scope_kind == "campaign":
        return row.scope_id in _campaign_ids(user_id)
    if row.scope_kind == "global":
        return row.scope_id == 0
    return False


def _scope(row):
    if row.scope_kind == "global":
        return {"kind": "global", "id": 0, "label": "VTT-Compendium"}
    if row.scope_kind == "campaign":
        campaign = db.session.get(Campaign, row.scope_id)
        return {"kind": "campaign", "id": row.scope_id, "label": campaign.name if campaign else "Kampagne"}
    return {"kind": "personal", "id": row.scope_id, "label": "Persönlich"}


def pin_for(row):
    """The immutable record a character stores at finalize (profile copied, not referenced)."""
    author = db.session.get(User, row.published_by)
    return {
        "schema": profiles.PIN_SCHEMA,
        "revisionId": row.id,
        "revision": row.revision_number,
        "digest": row.profile_digest,
        "sourceUuid": row.source_uuid,
        "sourceDigest": row.source_digest,
        "scope": _scope(row),
        "author": author.username if author else None,
        "publishedAt": row.published_at.isoformat() + "Z" if row.published_at else None,
        "profile": copy.deepcopy(row.profile),
    }


def catalog(user_id):
    """Latest revision of each Species the user may choose, as creator-data entries with provenance."""
    if not enabled():
        return []
    campaigns = _campaign_ids(user_id)
    rows = (
        CeSpeciesRevision.query.filter(or_(
            and_(CeSpeciesRevision.scope_kind == "global", CeSpeciesRevision.scope_id == 0),
            and_(CeSpeciesRevision.scope_kind == "personal", CeSpeciesRevision.scope_id == user_id),
            and_(CeSpeciesRevision.scope_kind == "campaign", CeSpeciesRevision.scope_id.in_(campaigns or [-1])),
        ))
        .order_by(CeSpeciesRevision.revision_number.asc(), CeSpeciesRevision.id.asc())
        .all()
    )
    latest = {}
    for row in rows:
        latest[(row.scope_kind, row.scope_id, row.lineage)] = row
    entries = []
    for row in sorted(latest.values(), key=lambda r: (r.name.lower(), r.id)):
        entry = profiles.species_entry(row.profile, profiles.species_id(row.id))
        entry["origin"] = profiles.origin_view(pin_for(row))
        entries.append(entry)
    return entries


def resolve(user_id, state):
    """(rules data, revision row or None, problems) for a creator state chosen by `user_id`."""
    data = load_creator_data()
    species = state.get("species") if isinstance(state, dict) else None
    sid = species.get("id") if isinstance(species, dict) else None
    if not profiles.is_homebrew_species(sid):
        return data, None, []
    revision_id = profiles.revision_id_of(sid)
    row = db.session.get(CeSpeciesRevision, revision_id) if revision_id else None
    if row is None or not enabled() or not can_select(user_id, row):
        return data, None, [{"path": "species.id", "message": UNAVAILABLE}]
    return profiles.with_species(data, profiles.species_entry(row.profile, sid)), row, []


def campaign_problem(pin, campaign_id):
    """Why a character pinning `pin` cannot be in `campaign_id` (a message), else None."""
    scope = (pin or {}).get("scope") or {}
    if scope.get("kind") == "campaign" and campaign_id is not None and campaign_id != scope.get("id"):
        return f"Die Spezies „{pin['profile']['name']}“ ist nur in der Kampagne „{scope.get('label')}“ spielbar."
    return None


def revision(revision_id):
    return db.session.get(CeSpeciesRevision, revision_id) if type(revision_id) is int else None
