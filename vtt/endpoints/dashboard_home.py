"""Personal VTT overview endpoints."""

from __future__ import annotations

from flask import Blueprint, jsonify
from flask_jwt_extended import get_jwt_identity, jwt_required
from sqlalchemy import and_, func, or_

from vtt.extensions import db
from vtt.models import (
    Campaign,
    CampaignMember,
    Character,
    GameSession,
    SessionCharacterAssignment,
    SessionState,
    User,
)


dashboard_home_bp = Blueprint("dashboard_home", __name__, url_prefix="/api/dashboard")


def _get_current_user():
    user_id = get_jwt_identity()
    if not user_id:
        return None, (jsonify({"error": "authentication required"}), 401)

    user = db.session.get(User, int(user_id))
    if not user or not user.is_active:
        return None, (jsonify({"error": "user not found"}), 404)
    return user, None


def _visible_campaigns_for_user(user: User) -> list[Campaign]:
    return (
        Campaign.query.outerjoin(
            CampaignMember,
            and_(
                CampaignMember.campaign_id == Campaign.id,
                CampaignMember.user_id == user.id,
                CampaignMember.status == "active",
            ),
        )
        .filter(Campaign.deleted_at.is_(None))
        .filter(or_(Campaign.owner_id == user.id, CampaignMember.id.isnot(None)))
        .order_by(Campaign.updated_at.desc(), Campaign.created_at.desc())
        .distinct()
        .all()
    )


def _serialize_campaign_for_home(campaign: Campaign, user_id: int) -> dict:
    active_members = [member for member in campaign.members if member.status == "active"]
    is_owner = campaign.owner_id == user_id
    active_membership = next((member for member in active_members if member.user_id == user_id), None)
    your_role = "DM" if is_owner else (active_membership.campaign_role if active_membership else None)
    return {
        "id": campaign.id,
        "name": campaign.name,
        "description": campaign.description,
        "status": campaign.status,
        "member_count": len(active_members),
        "session_count": len(campaign.sessions),
        "is_owner": is_owner,
        "is_member": bool(is_owner or active_membership),
        "your_role": your_role,
        "created_at": campaign.created_at.isoformat() if campaign.created_at else None,
        "updated_at": campaign.updated_at.isoformat() if campaign.updated_at else None,
    }


def _serialize_character_for_home(character: Character) -> dict:
    payload = character.serialize(include_details=True)
    payload["has_identity"] = bool(character.avatar_storage_key or character.token_storage_key)
    return payload


def _build_session_summaries(campaigns: list[Campaign]) -> list[dict]:
    campaign_ids = [campaign.id for campaign in campaigns]
    if not campaign_ids:
        return []

    sessions = (
        GameSession.query.filter(GameSession.campaign_id.in_(campaign_ids))
        .filter(GameSession.is_archived.is_(False))
        .order_by(
            GameSession.started_at.desc().nullslast(),
            GameSession.scheduled_at.asc().nullsfirst(),
            GameSession.created_at.desc(),
        )
        .all()
    )

    state_by_session = {
        state.game_session_id: state
        for state in SessionState.query.filter(SessionState.game_session_id.in_([session.id for session in sessions])).all()
    } if sessions else {}
    assignment_counts = {
        session_id: count
        for session_id, count in db.session.query(
            SessionCharacterAssignment.game_session_id,
            func.count(SessionCharacterAssignment.id),
        ).filter(SessionCharacterAssignment.game_session_id.in_([session.id for session in sessions])).group_by(SessionCharacterAssignment.game_session_id).all()
    } if sessions else {}

    campaign_by_id = {campaign.id: campaign for campaign in campaigns}
    summaries = []
    for session in sessions:
        campaign = campaign_by_id.get(session.campaign_id)
        state = state_by_session.get(session.id)
        assignment_count = assignment_counts.get(session.id, 0)
        map_ready = bool(session.map_id or (state and state.active_map_id))
        maps_available = len(campaign.maps) if campaign else 0
        runtime_status = str(session.get_runtime_status() or "").strip().lower()
        prep_blockers = []
        if runtime_status in {"scheduled", "ready", "paused"} and not map_ready:
            prep_blockers.append("Session-Karte fehlt")
        if runtime_status in {"scheduled", "ready", "paused"} and assignment_count <= 0:
            prep_blockers.append("Session-Charaktere fehlen")

        summaries.append(
            {
                "id": session.id,
                "campaign_id": session.campaign_id,
                "campaign_name": campaign.name if campaign else "Kampagne",
                "name": session.name,
                "runtime_status": runtime_status or "scheduled",
                "scheduled_at": session.scheduled_at.isoformat() if session.scheduled_at else None,
                "started_at": session.started_at.isoformat() if session.started_at else None,
                "map_ready": map_ready,
                "maps_available": maps_available,
                "assignment_count": assignment_count,
                "prep_blockers": prep_blockers,
            }
        )

    return summaries


def _build_primary_and_secondary_actions(campaigns: list[dict], characters: list[dict], sessions: list[dict], user: User | None = None) -> tuple[dict, dict]:
    is_player = bool(user and str(getattr(user, "profile_tier", "")).lower() == "player")
    live_session = next((session for session in sessions if session["runtime_status"] in {"in_progress", "active", "live"}), None)
    prep_session = next((session for session in sessions if session["prep_blockers"]), None)

    if live_session:
        primary = {
            "label": "Zur Live-Session",
            "href": f"/campaigns?campaign_id={live_session['campaign_id']}&classic=1",
            "note": "Öffnet die aktive Runde und ihre nächsten Schritte.",
        }
    elif prep_session:
        primary = {
            "label": "Session-Prep fortsetzen",
            "href": f"/campaigns?campaign_id={prep_session['campaign_id']}&classic=1",
            "note": "Karte oder Charaktere fehlen noch für den nächsten Spielabend.",
        }
    elif campaigns:
        primary = {
            "label": "Meine Kampagne öffnen" if is_player else "Kampagnen-Hub öffnen",
            "href": f"/campaigns?campaign_id={campaigns[0]['id']}&classic=1",
            "note": "Öffnet deine nächste Runde und den aktuellen Vorbereitungsstand.",
        }
    else:
        primary = {
            "label": "Charakter anlegen" if is_player else "Erste Kampagne anlegen",
            "href": "/characters?classic=1&intent=create" if is_player else "/campaigns?classic=1&intent=create",
            "note": "Lege deinen ersten eigenen Einstieg an." if is_player else "Lege die erste Runde an und beginne die Vorbereitung.",
        }

    if characters:
        secondary = {
            "label": "Charakterarchiv öffnen",
            "href": "/characters?classic=1",
            "note": "Bögen, Identität und der Rückweg in die Vorbereitung bleiben hier gebündelt.",
        }
    elif campaigns:
        secondary = {
            "label": "Held anlegen",
            "href": "/characters?classic=1&intent=create",
            "note": "Lege den ersten Helden an und führe ihn danach in die Vorbereitung.",
        }
    else:
        secondary = {
            "label": "Kampagnen öffnen",
            "href": "/campaigns?classic=1",
            "note": "Sieh dir bestehende Runden an oder tritt einer Kampagne bei.",
        }

    return primary, secondary


def _build_feed_preview(campaigns: list[dict], characters: list[dict], sessions: list[dict]) -> list[dict]:
    feed = []

    prep_session = next((session for session in sessions if session["prep_blockers"]), None)
    live_session = next((session for session in sessions if session["runtime_status"] in {"in_progress", "active", "live"}), None)

    if prep_session:
        feed.append(
            {
                "id": f"prep-{prep_session['id']}",
                "section": "session-prep",
                "kicker": "Vorbereitung",
                "title": f"{prep_session['campaign_name']} braucht noch Vorbereitung",
                "meta": prep_session["name"],
                "copy": f"Offen vor dem Tisch: {', '.join(prep_session['prep_blockers'])}.",
                "action_label": "Session-Prep öffnen",
                "action_href": f"/campaigns?campaign_id={prep_session['campaign_id']}&classic=1",
            }
        )

    if campaigns:
        campaign = campaigns[0]
        feed.append(
            {
                "id": f"campaign-{campaign['id']}",
                "section": "campaigns",
                "kicker": "Kampagnen",
                "title": campaign["name"],
                "meta": f"{campaign['member_count']} Mitglieder · {campaign['session_count']} Sitzungen",
                "copy": campaign.get("description") or "Von der Übersicht direkt in Hub, Vorbereitung und die nächsten Schritte zum Spielabend.",
                "action_label": "Hub öffnen",
                "action_href": f"/campaigns?campaign_id={campaign['id']}&classic=1",
            }
        )

    if characters:
        character = characters[0]
        feed.append(
            {
                "id": f"character-{character['id']}",
                "section": "characters",
                "kicker": "Charaktere",
                "title": character["name"],
                "meta": f"Stufe {character['level']} · {character.get('class') or 'Abenteurer'}",
                "copy": "Bogen, Identität und der Rückweg in Kampagnen oder Vorbereitung bleiben von hier aus erreichbar.",
                "action_label": "Bogen öffnen",
                "action_href": f"/character-sheet?id={character['id']}",
            }
        )

    if live_session:
        feed.append(
            {
                "id": f"play-{live_session['id']}",
                "section": "play",
                "kicker": "Play",
                "title": f"Live-Pfad für {live_session['campaign_name']}",
                "meta": live_session["name"],
                "copy": "Öffne die laufende Runde und kehre direkt zum nächsten Spielschritt zurück.",
                "action_label": "Runde öffnen",
                "action_href": f"/campaigns?campaign_id={live_session['campaign_id']}&classic=1",
            }
        )
    else:
        feed.append(
            {
                "id": "play-path",
                "section": "play",
                "kicker": "Play",
                "title": "Spieltisch vorbereiten",
                "meta": "Nächster Schritt vor der Session",
                "copy": "Öffne die Vorbereitung, prüfe Karte und Charaktere und starte danach den Spielabend.",
                "action_label": "Vorbereitung öffnen",
                "action_href": "/campaigns?classic=1",
            }
        )

    return feed


def _build_home_snapshot(user: User):
    visible_campaigns = _visible_campaigns_for_user(user)
    campaigns = [_serialize_campaign_for_home(campaign, user.id) for campaign in visible_campaigns]
    characters = [_serialize_character_for_home(character) for character in Character.query.filter_by(user_id=user.id, deleted_at=None).order_by(Character.updated_at.desc(), Character.created_at.desc()).all()]
    session_summaries = _build_session_summaries(visible_campaigns)
    primary_action, secondary_action = _build_primary_and_secondary_actions(campaigns, characters, session_summaries, user)
    feed_preview = _build_feed_preview(campaigns, characters, session_summaries)

    prep_blocker_count = sum(1 for session in session_summaries if session["prep_blockers"])
    live_session_count = sum(1 for session in session_summaries if session["runtime_status"] in {"in_progress", "active", "live"})

    home_state = {
        "campaign_count": len(campaigns),
        "character_count": len(characters),
        "session_count": len(session_summaries),
        "live_session_count": live_session_count,
        "prep_blocker_count": prep_blocker_count,
        "summary": (
            f"{prep_blocker_count} Session{'s' if prep_blocker_count != 1 else ''} brauchen noch Vorbereitung."
            if prep_blocker_count
            else (
                f"{live_session_count} Live-Session{'s' if live_session_count != 1 else ''} sind sichtbar."
                if live_session_count
                else (
                    "Die Übersicht ist bereit für Kampagnen und die nächsten Vorbereitungsschritte."
                    if campaigns or characters
                    else "Noch kein Kapitel offen. Starte mit deiner ersten Kampagne oder deinem ersten Helden."
                )
            )
        ),
    }

    return {
        "user": user.serialize(include_email=True),
        "campaigns": campaigns,
        "characters": characters,
        "sessions": session_summaries,
        "home_state": home_state,
        "primary_action": primary_action,
        "secondary_action": secondary_action,
        "feed_preview": feed_preview,
        "overview_scope": {
            "kind": "personal_vtt_home",
            "read_only": True,
            "note": "Diese Übersicht zeigt deinen VTT-Stand: Kampagnen, Charaktere, Sitzungen und Vorbereitung.",
        },
    }


@dashboard_home_bp.route("/home", methods=["GET"])
@jwt_required()
def get_dashboard_home():
    """Return the richer dashboard home snapshot for BookScene."""
    user, error = _get_current_user()
    if error:
        return error

    return jsonify(_build_home_snapshot(user)), 200
