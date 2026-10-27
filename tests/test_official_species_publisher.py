"""Official publications keep durable provenance without a shared login account."""

import copy
import json
from pathlib import Path

import pytest

from tests.test_srd_creator_api import _client, app  # noqa: F401
from vtt.characters import species_catalog
from vtt.creation_engine.models import CeEagleDocument, CeSpeciesRevision
from vtt.creation_engine.official_publisher import (
    OFFICIAL_USERNAME, OfficialPublishError, check_bundle, publish_bundle,
)
from vtt.extensions import db
from vtt.models import User

STARTER = Path(__file__).resolve().parents[1] / "vtt/static/examples/duckfolk-2024.json"
DOCUMENT_ID = "RollDraufDuckfolk2024"


def _starter():
    return json.loads(STARTER.read_text(encoding="utf-8"))


def test_official_duckfolk_is_global_attributed_and_idempotent(app):
    app.config.update(CE_PLAYABLE_SPECIES=True)
    outsider = _client(app, "official_outsider")
    bundle = _starter()
    checked = check_bundle(bundle, DOCUMENT_ID)
    assert checked["profile"]["name"] == "Duckfolk"
    assert User.query.filter_by(username=OFFICIAL_USERNAME).first() is None, "check-only must not create an account"

    first = publish_bundle(bundle, DOCUMENT_ID)
    author = db.session.get(User, first["publisherId"])
    assert first["created"] is True and first["revision"]["revision"] == 1
    assert first["revision"]["scope"] == {"kind": "global", "id": 0}
    assert author.username == OFFICIAL_USERNAME and not author.is_usable()
    assert author.is_active is False and author.account_state == "deactivated"
    assert author.platform_role is None and author.role.name == "Player"
    assert CeEagleDocument.query.filter_by(scope_kind="personal", scope_id=author.id, document_id=DOCUMENT_ID).count() == 1
    entries = species_catalog.catalog(outsider.user_id)
    duck = next(entry for entry in entries if entry["name"] == "Duckfolk")
    assert duck["origin"]["author"] == OFFICIAL_USERNAME
    assert duck["origin"]["scope"]["kind"] == "global"

    again = publish_bundle(bundle, DOCUMENT_ID)
    assert again["created"] is False and again["revision"]["id"] == first["revision"]["id"]
    assert CeSpeciesRevision.query.count() == 1

    changed = copy.deepcopy(bundle)
    changed["source"]["name"] = "Duckfolk Revised"
    with pytest.raises(OfficialPublishError, match="--revise"):
        publish_bundle(changed, DOCUMENT_ID)
    assert CeSpeciesRevision.query.count() == 1
    assert CeEagleDocument.query.filter_by(document_id=DOCUMENT_ID).one().revision == 1

    second = publish_bundle(changed, DOCUMENT_ID, revise=True)
    assert second["created"] is True and second["revision"]["revision"] == 2
    assert second["revision"]["sourceRevision"] == 2
    assert CeSpeciesRevision.query.count() == 2
    assert db.session.get(CeSpeciesRevision, first["revision"]["id"]).name == "Duckfolk"
    assert author.is_active is False and author.account_state == "deactivated"


def test_unplayable_official_bundle_does_not_create_an_account_or_source(app):
    bundle = _starter()
    bundle["source"]["system"]["source"]["rules"] = "2014"
    with pytest.raises(OfficialPublishError, match="not playable"):
        publish_bundle(bundle, DOCUMENT_ID)
    assert User.query.filter_by(username=OFFICIAL_USERNAME).first() is None
    assert CeEagleDocument.query.count() == 0
    assert CeSpeciesRevision.query.count() == 0
