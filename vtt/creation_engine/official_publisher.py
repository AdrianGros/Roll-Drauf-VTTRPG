"""Publish reviewed, playable Species under the non-login Roll Drauf Default identity.

Run on the app host with ``python -m vtt.creation_engine.official_publisher --bundle FILE --id ID``
to validate, then repeat with ``--publish`` to commit. Only server operators can run this module;
the ordinary Creation Engine HTTP path remains the path for human contributors.
"""

import argparse
import copy
import json
import secrets
from pathlib import Path

from vtt.creation_engine import documents, species
from vtt.creation_engine.canonical import content_digest
from vtt.creation_engine.models import CeEagleDocument, CeSpeciesRevision
from vtt.extensions import db
from vtt.models import Role, User
from vtt.rules_content.creator_rules import load_creator_data

OFFICIAL_USERNAME = "Roll Drauf Default"
OFFICIAL_EMAIL = "roll-drauf-default@example.invalid"


class OfficialPublishError(ValueError):
    """The bundle, publisher identity, or requested revision is unsuitable."""


def check_bundle(bundle, document_id):
    """Validate a Species bundle without changing the database; return the normalized publication material."""
    if not isinstance(bundle, dict) or set(bundle) != {"source", "supplement"}:
        raise OfficialPublishError("The bundle must contain exactly source and supplement.")
    documents.check_id(document_id)
    source = copy.deepcopy(bundle["source"])
    supplement = copy.deepcopy(bundle["supplement"])
    if not isinstance(source, dict) or source.get("_id", document_id) != document_id:
        raise OfficialPublishError("The source must be an object with no conflicting _id.")
    source["_id"] = document_id
    documents.check_json(source)
    documents.check_json(supplement)
    documents.check_document(source, "Item", "race")
    skills = {skill["id"]: skill["name"] for skill in load_creator_data()["skills"]}
    result = species.inspect(source, supplement, skills=skills)
    if not result["playable"]:
        blockers = "; ".join(f"{entry['path']}: {entry['message']}" for entry in result["entries"]
                             if entry["status"] == "blocked")
        raise OfficialPublishError(f"Species is not playable: {blockers[:1000]}")
    return {
        "source": source, "supplement": supplement, "profile": result["profile"],
        "report": result["entries"], "edition": result["edition"],
        "source_digest": content_digest(source), "profile_digest": content_digest(result["profile"]),
    }


def _publisher():
    by_name = User.query.filter_by(username=OFFICIAL_USERNAME).first()
    by_email = User.query.filter_by(email=OFFICIAL_EMAIL).first()
    if by_name is not None or by_email is not None:
        if by_name is None or by_email is None or by_name.id != by_email.id:
            raise OfficialPublishError("The reserved official username or email belongs to another account.")
        if (by_name.is_active or by_name.account_state != "deactivated" or by_name.platform_role is not None
                or by_name.role.name != "Player"):
            raise OfficialPublishError("The official publisher must remain a deactivated, unprivileged Player account.")
        return by_name
    player = Role.query.filter_by(name="Player").first()
    if player is None:
        raise OfficialPublishError("The Player role is missing.")
    user = User(username=OFFICIAL_USERNAME, email=OFFICIAL_EMAIL, role_id=player.id,
                is_active=False, account_state="deactivated", email_verified=False,
                platform_role=None, profile_tier="player")
    user.set_password(secrets.token_urlsafe(32))  # Discarded immediately; no login credential exists.
    db.session.add(user)
    db.session.flush()
    return user


def publish_bundle(bundle, document_id, *, revise=False):
    """Create/verify the official identity and atomically publish one global Species revision."""
    material = check_bundle(bundle, document_id)
    try:
        author = _publisher()
        source_row = CeEagleDocument.query.filter_by(
            scope_kind="personal", scope_id=author.id, pack="", document_name="Item", document_id=document_id,
        ).first()
        if source_row is None:
            source_row = CeEagleDocument(
                scope_kind="personal", scope_id=author.id, pack="", document_name="Item",
                document_id=document_id, doc_type="race", name=material["source"]["name"],
                source=material["source"], created_by=author.id, updated_by=author.id,
            )
            db.session.add(source_row)
            db.session.flush()
        elif source_row.source != material["source"]:
            if not revise:
                raise OfficialPublishError("The official source changed; pass --revise to publish a new revision.")
            source_row.source = material["source"]
            source_row.name = material["source"]["name"]
            source_row.revision += 1
            source_row.updated_by = author.id

        lineage = f"author:{author.id}:personal:{author.id}:{source_row.uuid}"
        latest = (CeSpeciesRevision.query.filter_by(scope_kind="global", scope_id=0, lineage=lineage)
                  .order_by(CeSpeciesRevision.revision_number.desc()).first())
        if (latest is not None and latest.source_digest == material["source_digest"]
                and latest.profile_digest == material["profile_digest"]
                and latest.supplement == material["supplement"]):
            db.session.commit()
            return {"created": False, "publisherId": author.id, "revision": latest.summary()}

        revision = CeSpeciesRevision(
            scope_kind="global", scope_id=0, lineage=lineage,
            revision_number=(latest.revision_number if latest else 0) + 1,
            name=material["profile"]["name"], edition=material["edition"],
            source_uuid=source_row.uuid, source_revision=source_row.revision,
            source_digest=material["source_digest"], source=material["source"],
            supplement=material["supplement"], profile=material["profile"],
            profile_digest=material["profile_digest"], report=material["report"],
            published_by=author.id,
        )
        db.session.add(revision)
        db.session.commit()
        return {"created": True, "publisherId": author.id, "revision": revision.summary()}
    except Exception:
        db.session.rollback()
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description="Check or publish official playable Species")
    parser.add_argument("--bundle", type=Path, required=True, help="JSON file containing source and supplement")
    parser.add_argument("--id", required=True, help="Stable alphanumeric Eagle document ID")
    parser.add_argument("--publish", action="store_true", help="Commit under Roll Drauf Default")
    parser.add_argument("--revise", action="store_true", help="Permit changing an existing official source")
    args = parser.parse_args(argv)
    from vtt import create_app

    app = create_app()
    try:
        bundle = json.loads(args.bundle.read_text(encoding="utf-8"))
        with app.app_context():
            if args.publish:
                outcome = publish_bundle(bundle, args.id, revise=args.revise)
            else:
                material = check_bundle(bundle, args.id)
                outcome = {"playable": True, "name": material["profile"]["name"],
                           "edition": material["edition"], "sourceDigest": material["source_digest"],
                           "profileDigest": material["profile_digest"]}
    except (OSError, json.JSONDecodeError, documents.RequestFailure, OfficialPublishError) as exc:
        parser.exit(1, f"Official Species publication refused: {exc}\n")
    print(json.dumps(outcome, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
