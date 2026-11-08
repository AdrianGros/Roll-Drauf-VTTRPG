"""Small, account-bound survey for the three DAD-M research reports."""

from collections import Counter

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from vtt.extensions import db, limiter
from vtt.models import ResearchSurveyResponse, User
from vtt.permissions import has_platform_role


research_survey_bp = Blueprint("research_survey", __name__, url_prefix="/api/research-survey")

OPTIONS = {
    "topic": {"technical", "frontier", "dadm_niche", "none", "unsure"},
    "usefulness": {"very", "somewhat", "little", "none", "unsure"},
    "concern": {"security", "proof", "effort", "benefit", "other", "unsure"},
    "vtt_priority": {"stability", "features", "transparency", "privacy", "other", "unsure"},
}


def _current_usable_user():
    try:
        user_id = int(get_jwt_identity())
    except (TypeError, ValueError):
        return None
    user = db.session.get(User, user_id)
    return user if user and user.is_usable() else None


@research_survey_bp.get("")
@jwt_required()
def get_survey():
    user = _current_usable_user()
    if not user:
        return jsonify({"error": "authentication required"}), 401
    response = ResearchSurveyResponse.query.filter_by(user_id=user.id).first()
    return jsonify({"options": {key: sorted(values) for key, values in OPTIONS.items()}, "answer": response.serialize_own() if response else None}), 200


@research_survey_bp.put("")
@limiter.limit("5 per minute")
@jwt_required()
def save_survey():
    user = _current_usable_user()
    if not user:
        return jsonify({"error": "authentication required"}), 401
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Ungültige Antwort."}), 400

    answers = {}
    for field, allowed in OPTIONS.items():
        value = data.get(field)
        if not isinstance(value, str) or value not in allowed:
            return jsonify({"error": f"Bitte beantworte die Frage: {field}."}), 400
        answers[field] = value

    comment = data.get("comment", "")
    if not isinstance(comment, str) or len(comment.strip()) > 1000:
        return jsonify({"error": "Der Kommentar darf höchstens 1000 Zeichen haben."}), 400

    response = ResearchSurveyResponse.query.filter_by(user_id=user.id).first()
    if response is None:
        response = ResearchSurveyResponse(user_id=user.id)
        db.session.add(response)
    for field, value in answers.items():
        setattr(response, field, value)
    response.comment = comment.strip()
    db.session.commit()
    return jsonify({"answer": response.serialize_own()}), 200


@research_survey_bp.get("/results")
@has_platform_role("owner", "admin")
def get_survey_results():
    rows = ResearchSurveyResponse.query.order_by(ResearchSurveyResponse.created_at.asc()).all()
    counts = {field: dict(Counter(getattr(row, field) for row in rows)) for field in OPTIONS}
    comments = [row.comment for row in rows if row.comment]
    return jsonify({"total": len(rows), "counts": counts, "comments": comments}), 200
