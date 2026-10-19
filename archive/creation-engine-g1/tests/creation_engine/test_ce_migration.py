"""WP7: real legacy rows, exact parity reports and atomic scope authority."""

from pathlib import Path
import multiprocessing
import threading

import pytest
from sqlalchemy import func, inspect, select, text
from sqlalchemy.orm import Session

from vtt.creation_engine.transports.legacy_host import build_gateway
from vtt.creation_engine.adapter.mapping import VERSION
from vtt.creation_engine.canonical import canonical_bytes, parse_strict_json
from vtt.creation_engine.content import new_id
from vtt.creation_engine.kernel.records import KernelError
from vtt.creation_engine.store.migration_models import (MIGRATION_TABLES, CeMigrationLedger, CeMigrationState,
    CeParityApproval, CeRepresentation)
from vtt.creation_engine.store.runtime_models import CeInstance, CeResourceLedger, CeRuntimeScope
from vtt.models.campaign import Campaign
from vtt.models.campaign_member import CampaignMember
from vtt.models.character import Character
from vtt.models.equipment import Equipment
from vtt.models.user import User
from vtt.models.game_session import GameSession
from vtt.models.campaign_map import CampaignMap
from vtt.models.session_state import SessionState
from vtt.models.token_state import TokenState

from test_ce_content_store import postgres_engine

pytestmark = pytest.mark.postgres
MIGRATIONS = Path(__file__).resolve().parents[2] / "migrations"


@pytest.fixture(scope="module")
def migration_engine(postgres_engine):
    with postgres_engine.begin() as connection:
        with connection.connection.cursor() as cursor:
            for filename in ("migration_m74_creation_engine_kernel.sql", "migration_m75_creation_engine_decisions.sql",
                             "migration_m76_creation_engine_policy.sql", "migration_m77_creation_engine_legacy.sql"):
                cursor.execute((MIGRATIONS / filename).read_text())
        connection.execute(text("UPDATE users SET is_active=true, is_suspended=false, account_state='active' WHERE id=1"))
        connection.execute(text("SELECT setval(pg_get_serial_sequence('users','id'), (SELECT max(id) FROM users))"))
    return postgres_engine


def world(engine, *, fixture=True, count=2, invalid_hp=False):
    with Session(engine) as session, session.begin():
        account = User(username=new_id("player"), email=new_id("mail") + "@example.test", password_hash="x",
                       role_id=1, is_active=True, is_suspended=False, account_state="active")
        campaign = Campaign(name="Migration fixture", owner_id=1)
        session.add_all([account, campaign]); session.flush()
        session.add(CampaignMember(campaign_id=campaign.id, user_id=account.id, campaign_role="Player", status="active"))
        ids = []
        for ac in (12, 13)[:count]:
            c = Character(user_id=account.id, campaign_id=campaign.id, name="Kämpfer", class_name="Kämpfer", level=3,
                ac=ac, hp_current=20 if invalid_hp else 8, hp_max=10, mana_current=2, mana_max=4,
                character_data={"roll_drauf_light": {"content": {"class_features": [{"slug": "defensiver_stil"}]}},
                                "secret": "kept private", "unknown": {"kind": "revision", "id": "not executable"}})
            session.add(c); session.flush(); ids.append(c.id)
            session.add(Equipment(character_id=c.id, name="Old armor", ac_bonus=2, is_equipped=True,
                                  special_properties={"script": "inert"}))
        campaign_id, user_id = campaign.id, account.id
    gateway = build_gateway(engine)
    scope_id = gateway.kernel.migration.provision(1, campaign_id=campaign_id, fixture=fixture)
    return {"gateway": gateway, "scope": scope_id, "campaign": campaign_id, "user": user_id, "characters": ids}


def command(w, operation, payload, *, principal=1, public=True, **changes):
    gateway = w["gateway"]
    with gateway.store.transaction(w["scope"]) as tx:
        wire = {"contractVersion": "1.1.3", "commandId": new_id("cmd"), "idempotencyKey": new_id("key"),
                "scopeId": w["scope"], "expectedScopeVersion": tx.scope.state_version,
                "authorityEpoch": tx.scope.authority_epoch, "operation": operation, "payload": payload}
        if operation in {"AdjustResource", "SetBaseValue", "SetValueOverride", "ClearValueOverride", "SetItemEquipped"}:
            wire["executionLockDigest"] = tx.lock.digest
    wire.update(changes)
    return (gateway if public else gateway.kernel).submit(principal, canonical_bytes(wire))


def shadow(w):
    for character in w["characters"]:
        command(w, "MapLegacyCharacter", {"source": {"sourceType": "vtt.character", "sourceId": character}, "migrationVersion": VERSION})
    command(w, "BeginScopeShadow", {"ruleset": w["gateway"].kernel.ruleset.artifact()})
    return w["gateway"].kernel.migration.preview(1, w["scope"])


def cutover(w):
    report = shadow(w)
    command(w, "FreezeScopeForCutover", {"reason": "test fixture"})
    command(w, "CommitScopeCutover", {"parityReportDigest": report["parityReportDigest"]})
    return report


def ref(w, instance):
    return {"kind": "instance", "id": instance, "scopeId": w["scope"]}


def add_tokens(engine, w, hp=8):
    with Session(engine) as session, session.begin():
        campaign_map = CampaignMap(campaign_id=w["campaign"], name="Fixture", width=100, height=100, created_by=1)
        session.add(campaign_map); session.flush()
        ids = []
        for _ in range(2):
            game = GameSession(campaign_id=w["campaign"], name="Session", map_id=campaign_map.id,
                               session_state="active", status="in_progress")
            session.add(game); session.flush()
            state = SessionState(game_session_id=game.id, campaign_id=w["campaign"], active_map_id=campaign_map.id)
            session.add(state); session.flush()
            token = TokenState(session_state_id=state.id, campaign_id=w["campaign"], game_session_id=game.id,
                map_id=campaign_map.id, character_id=w["characters"][0], owner_user_id=w["user"], name="Hero",
                x=0, y=0, hp_current=hp, hp_max=10)
            session.add(token); session.flush(); ids.append(token.id)
        return ids


def context(w, key=None):
    with w["gateway"].store.transaction(w["scope"]) as tx:
        return {"authorityEpoch": tx.scope.authority_epoch, "expectedScopeVersion": tx.scope.state_version,
                "idempotencyKey": key or new_id("key")}


def test_t01_unknown_totals_and_inert_metadata_survive(migration_engine):
    w = world(migration_engine)
    report = cutover(w)
    assert report["differences"] == []
    for entry, expected in zip(report["characters"], (12, 13)):
        owner = w["gateway"].read(w["user"], w["scope"], entry["instanceId"])["fields"]
        assert owner["ac"] == expected  # neither signature nor armor bonus is applied twice
        assert owner["character_data"]["unknown"]["kind"] == "revision"
        assert owner["provenance"]["bases"] == "imported_legacy_baseline"
        gm = w["gateway"].read(1, w["scope"], entry["instanceId"])["fields"]
        assert "character_data" not in gm and "legacyMetadata" not in gm


def test_shadow_does_not_mutate_any_legacy_table_or_resource(migration_engine):
    w = world(migration_engine)
    def legacy_dump():
        with migration_engine.connect() as connection:
            return {name: connection.execute(text('SELECT row_to_json(t)::text FROM "' + name + '" t ORDER BY row_to_json(t)::text')).scalars().all()
                    for name in inspect(migration_engine).get_table_names() if not name.startswith("ce_")}
    before = legacy_dump()
    report = shadow(w)
    assert w["gateway"].kernel.migration.preview(1, w["scope"])["parityReportDigest"] == report["parityReportDigest"]
    assert legacy_dump() == before
    with Session(migration_engine) as session:
        assert session.scalar(select(func.count()).select_from(CeInstance).where(CeInstance.scope_id == w["scope"])) == 0


def test_t48_partial_campaign_mapping_cannot_shadow(migration_engine):
    w = world(migration_engine)
    command(w, "MapLegacyCharacter", {"source": {"sourceType": "vtt.character", "sourceId": w["characters"][0]}, "migrationVersion": 1})
    with pytest.raises(KernelError, match="every active character") as caught:
        command(w, "BeginScopeShadow", {"ruleset": w["gateway"].kernel.ruleset.artifact()})
    assert caught.value.code == "PARITY_UNRESOLVED"


def test_nonfixture_cutover_is_never_authorized(migration_engine):
    w = world(migration_engine, fixture=False)
    shadow(w)
    with pytest.raises(KernelError) as caught:
        command(w, "FreezeScopeForCutover", {"reason": "try live"})
    assert caught.value.code == "CUTOVER_FIXTURE_ONLY"


def test_discrepancy_requires_both_current_capacities(migration_engine):
    w = world(migration_engine, count=1, invalid_hp=True)
    report = shadow(w)
    difference = report["differences"][0]
    payload = {"discrepancyId": difference["discrepancyId"], "resolution": "adopt_engine_value", "reason": "approve bound reconciliation"}
    command(w, "ApproveParityDifference", payload)
    command(w, "FreezeScopeForCutover", {"reason": "test"})
    with pytest.raises(KernelError) as caught:
        command(w, "CommitScopeCutover", {"parityReportDigest": report["parityReportDigest"]})
    assert caught.value.code == "PARITY_UNRESOLVED"
    command(w, "ApproveParityDifference", payload, principal=w["user"])
    command(w, "CommitScopeCutover", {"parityReportDigest": report["parityReportDigest"]})
    assert w["gateway"].read(w["user"], w["scope"], difference["instanceId"])["fields"]["hp_current"] == 10


def test_changed_source_invalidates_review_and_approvals(migration_engine):
    w = world(migration_engine, count=1, invalid_hp=True)
    report = shadow(w)
    payload = {"discrepancyId": report["differences"][0]["discrepancyId"], "resolution": "adopt_engine_value", "reason": "approved"}
    command(w, "ApproveParityDifference", payload)
    with Session(migration_engine) as session, session.begin():
        session.get(Character, w["characters"][0]).hp_current = 30
    command(w, "FreezeScopeForCutover", {"reason": "test"})
    with pytest.raises(KernelError) as caught:
        command(w, "CommitScopeCutover", {"parityReportDigest": report["parityReportDigest"]})
    assert caught.value.code == "PARITY_UNRESOLVED"


@pytest.mark.parametrize("stage", ["before_commit", "after_commit"])
def test_cutover_commit_boundary_is_atomic(migration_engine, stage):
    w = world(migration_engine)
    report = shadow(w)
    command(w, "FreezeScopeForCutover", {"reason": "test"})
    def fail(point):
        if point == stage:
            raise RuntimeError("lost worker")
    w["gateway"].kernel.fault = fail
    with pytest.raises(RuntimeError, match="lost worker"):
        command(w, "CommitScopeCutover", {"parityReportDigest": report["parityReportDigest"]})
    with Session(migration_engine) as session:
        scope = session.get(CeRuntimeScope, w["scope"])
        count = session.scalar(select(func.count()).select_from(CeInstance).where(CeInstance.scope_id == scope.id))
        assert (scope.migration_state, scope.authority_epoch, count) == (
            ("FROZEN_FOR_CUTOVER", 1, 0) if stage == "before_commit" else ("ENGINE", 2, 4))


def test_t02_inputs_and_resources_change_engine_only(migration_engine):
    w = world(migration_engine, count=1)
    actor = cutover(w)["characters"][0]["instanceId"]
    command(w, "AdjustResource", {"instance": ref(w, actor), "resourceId": "hp",
        "delta": {"value": {"numerator": -3, "denominator": 1}, "unit": "rdl:hp"}, "reason": "damage"}, principal=w["user"])
    command(w, "SetValueOverride", {"instance": ref(w, actor), "bindingId": "defense",
        "value": {"value": {"numerator": 17, "denominator": 1}, "unit": "rdl:point"}, "reason": "manual override"}, principal=w["user"])
    value = w["gateway"].read(w["user"], w["scope"], actor)["fields"]
    assert (value["hp_current"], value["ac"]) == (5, 17)
    with Session(migration_engine) as session:
        legacy = session.get(Character, w["characters"][0])
        assert (legacy.hp_current, legacy.ac) == (8, 12)


def test_m77_matches_models_and_reapplies(migration_engine):
    inspector = inspect(migration_engine)
    for table in MIGRATION_TABLES:
        assert set(table.columns.keys()) == {c["name"] for c in inspector.get_columns(table.name)}
    with migration_engine.begin() as connection:
        with connection.connection.cursor() as cursor:
            cursor.execute((MIGRATIONS / "migration_m77_creation_engine_legacy.sql").read_text())


def test_t03_two_sessions_share_hp_and_another_campaign_does_not(migration_engine):
    from vtt.creation_engine.store.legacy.compatibility import LegacyCompatibility
    w, other = world(migration_engine, count=1), world(migration_engine, count=1)
    tokens = add_tokens(migration_engine, w)
    cutover(w); cutover(other)
    compat = LegacyCompatibility(w["gateway"])
    request_context = context(w)
    receipt = compat.translate(w["user"], "vtt.token", tokens[0], {"hp_current": 5}, request_context)
    assert compat.translate(w["user"], "vtt.token", tokens[0], {"hp_current": 5}, request_context) == receipt
    assert [compat.read(w["user"], "vtt.token", token)["hp_current"] for token in tokens] == [5, 5]
    assert compat.read(w["user"], "vtt.character", w["characters"][0])["hp_current"] == 5
    assert LegacyCompatibility(other["gateway"]).read(other["user"], "vtt.character", other["characters"][0])["hp_current"] == 8
    with pytest.raises(KernelError) as caught:
        compat.translate(w["user"], "vtt.token", tokens[0], {"hp_current": 4}, request_context)
    assert caught.value.code == "IDEMPOTENCY_KEY_REUSE"


@pytest.mark.parametrize("writer", ["sheet", "token", "equipment", "new_character", "transfer", "bulk"])
def test_legacy_writers_cannot_bypass_engine_authority(migration_engine, writer):
    from vtt.creation_engine.store.legacy.guards import install_guards
    w = world(migration_engine, count=1)
    tokens = add_tokens(migration_engine, w)
    cutover(w)
    uninstall = install_guards(migration_engine, w["gateway"])
    try:
        with pytest.raises(KernelError) as caught, Session(migration_engine) as session, session.begin():
            if writer == "sheet":
                session.get(Character, w["characters"][0]).hp_current = 99
            elif writer == "token":
                session.get(TokenState, tokens[0]).hp_current = 99
            elif writer == "equipment":
                session.scalar(select(Equipment).where(Equipment.character_id == w["characters"][0])).is_equipped = False
            elif writer == "new_character":
                session.add(Character(user_id=w["user"], campaign_id=w["campaign"], name="Sneaked into scope"))
            elif writer == "transfer":
                session.get(Character, w["characters"][0]).campaign_id = None
            else:
                from sqlalchemy import update
                session.execute(update(Character).where(Character.id == w["characters"][0]).values(hp_current=99))
        assert caught.value.code == ("SCOPE_TRANSFER_UNSUPPORTED" if writer in {"transfer", "new_character"} else "LEGACY_FIELD_READ_ONLY")
    finally:
        uninstall()


def test_shadow_writers_keep_authority_but_freeze_fences_them(migration_engine):
    from vtt.creation_engine.store.legacy.guards import install_guards
    w = world(migration_engine, count=1)
    shadow(w)
    uninstall = install_guards(migration_engine, w["gateway"])
    try:
        with Session(migration_engine) as session, session.begin():
            session.get(Character, w["characters"][0]).hp_current = 7
        command(w, "FreezeScopeForCutover", {"reason": "freeze"})
        with pytest.raises(KernelError) as caught, Session(migration_engine) as session, session.begin():
            session.get(Character, w["characters"][0]).hp_current = 6
        assert caught.value.code == "MIGRATION_STATE_CONFLICT"
        command(w, "AbortScopeCutover", {"reason": "abort"})
        with Session(migration_engine) as session, session.begin():
            session.get(Character, w["characters"][0]).hp_current = 6
    finally:
        uninstall()


def test_new_representation_ignores_hp_and_movement_stays_presentation(migration_engine):
    from vtt.creation_engine.store.legacy.guards import install_guards
    from vtt.creation_engine.store.legacy.compatibility import LegacyCompatibility
    w = world(migration_engine, count=1)
    tokens = add_tokens(migration_engine, w)
    cutover(w)
    uninstall = install_guards(migration_engine, w["gateway"])
    try:
        with Session(migration_engine) as session, session.begin():
            old = session.get(TokenState, tokens[0])
            old.x = 20
            added = TokenState(session_state_id=old.session_state_id, campaign_id=old.campaign_id,
                game_session_id=old.game_session_id, map_id=old.map_id, character_id=old.character_id,
                owner_user_id=old.owner_user_id, name="New view", x=40, y=0, hp_current=999, hp_max=999)
            session.add(added); session.flush(); token_id = added.id
        assert LegacyCompatibility(w["gateway"]).read(w["user"], "vtt.token", token_id)["hp_current"] == 8
        with Session(migration_engine) as session:
            assert session.get(TokenState, token_id).hp_current is None
    finally:
        uninstall()


@pytest.mark.parametrize("change", ["membership", "account"])
def test_legacy_policy_writers_revoke_subscription_in_same_commit(migration_engine, change):
    from vtt.creation_engine.store.legacy.guards import install_guards
    from vtt.creation_engine.store.policy_models import CeSubscription
    w = world(migration_engine, count=1)
    cutover(w)
    g = w["gateway"]
    subscription = g.subscribe(w["user"], w["scope"], "connection:a", contract_version="1.1.3", authority_epoch=2)
    uninstall = install_guards(migration_engine, g)
    try:
        with Session(migration_engine) as session, session.begin():
            session.info["ce_authenticated_actor"] = 1
            if change == "membership":
                session.scalar(select(CampaignMember).where(CampaignMember.campaign_id == w["campaign"],
                    CampaignMember.user_id == w["user"])).status = "kicked"
            else:
                session.get(User, w["user"]).is_suspended = True
        with Session(migration_engine) as session:
            assert session.get(CeSubscription, subscription["subscriptionId"]).revoked_at is not None
        with pytest.raises(KernelError):
            g.poll(w["user"], w["scope"], subscription["subscriptionId"], subscription["cursor"], "connection:a")
    finally:
        uninstall()


def test_maximum_reduction_needs_explicit_resource_reconciliation(migration_engine):
    w = world(migration_engine, count=1)
    actor = cutover(w)["characters"][0]["instanceId"]
    with pytest.raises(KernelError) as caught:
        command(w, "SetValueOverride", {"instance": ref(w, actor), "bindingId": "hp_max",
            "value": {"value": {"numerator": 4, "denominator": 1}, "unit": "rdl:hp"}, "reason": "lower max"}, principal=w["user"])
    assert caught.value.code == "RESOURCE_BOUND_EXCEEDED"
    assert w["gateway"].read(w["user"], w["scope"], actor)["fields"]["hp_max"] == 10


def _legacy_writer(url, character_id, locked, release, output):
    from sqlalchemy import create_engine
    from vtt.creation_engine.store.legacy.guards import install_guards
    engine = create_engine(url)
    uninstall = install_guards(engine, build_gateway(engine))
    try:
        with Session(engine) as session, session.begin():
            session.get(Character, character_id).hp_current = 7
            session.flush()
            locked.set()
            if not release.wait(15):
                raise RuntimeError("writer barrier timed out")
        output.put("committed")
    except Exception as exc:
        output.put(getattr(exc, "code", type(exc).__name__))
    finally:
        uninstall()
        engine.dispose()


def test_real_process_legacy_write_and_freeze_share_one_fence(migration_engine):
    w = world(migration_engine, count=1)
    shadow(w)
    ctx = multiprocessing.get_context("spawn")
    locked, release, output = ctx.Event(), ctx.Event(), ctx.Queue()
    process = ctx.Process(target=_legacy_writer, args=(str(migration_engine.url.render_as_string(hide_password=False)),
        w["characters"][0], locked, release, output))
    result, done = [], threading.Event()
    def freeze():
        try:
            result.append(command(w, "FreezeScopeForCutover", {"reason": "competing writer"}))
        except Exception as exc:
            result.append(exc)
        finally:
            done.set()
    process.start()
    try:
        assert locked.wait(15)
        thread = threading.Thread(target=freeze)
        thread.start()
        assert not done.wait(.2)
        release.set()
        process.join(15); thread.join(15)
        assert process.exitcode == 0 and output.get(timeout=2) == "committed"
        assert result[0]["status"] == "committed"
        report = w["gateway"].kernel.migration.preview(1, w["scope"])
        assert next(f for f in report["characters"][0]["fields"] if f["sourceField"] == "hp_current")["engineValue"] == 7
        locked2, release2, output2 = ctx.Event(), ctx.Event(), ctx.Queue()
        release2.set()
        late = ctx.Process(target=_legacy_writer, args=(str(migration_engine.url.render_as_string(hide_password=False)),
            w["characters"][0], locked2, release2, output2))
        late.start(); late.join(15)
        assert late.exitcode == 0 and output2.get(timeout=2) == "MIGRATION_STATE_CONFLICT"
    finally:
        release.set()
        if process.is_alive():
            process.terminate(); process.join(5)


def test_engine_action_gate_blocks_legacy_calculated_edit(migration_engine):
    from vtt.creation_engine.store.legacy.compatibility import LegacyCompatibility
    from vtt.creation_engine.kernel.activity import Activity, Window
    from vtt.creation_engine.kernel.records import Action, ActionState
    w = world(migration_engine, count=1)
    cutover(w)
    g = w["gateway"]
    with g.store.transaction(w["scope"]) as tx:
        action_id = new_id("action")
        action = Action(action_id, tx.scope.id, w["user"], b"{}", Activity("fixture.wait", (Window("wait", (), (), 1),)).canonical(),
                        ActionState.SUSPENDED, tx.now, action_id)
        tx.save_action(action)
        tx.scope.active_action_id = action_id
    with pytest.raises(KernelError) as caught:
        LegacyCompatibility(g).translate(w["user"], "vtt.character", w["characters"][0], {"ac": 20}, context(w))
    assert caught.value.code == "SCOPE_BUSY"
    with Session(migration_engine) as session:
        assert session.get(Character, w["characters"][0]).ac == 12


def test_policy_writer_rollback_preserves_subscription_and_epoch(migration_engine):
    from vtt.creation_engine.store.legacy.guards import install_guards
    from vtt.creation_engine.store.policy_models import CeSubscription
    w = world(migration_engine, count=1)
    cutover(w)
    g = w["gateway"]
    subscription = g.subscribe(w["user"], w["scope"], "connection:a", contract_version="1.1.3", authority_epoch=2)
    uninstall = install_guards(migration_engine, g)
    try:
        with Session(migration_engine) as session:
            session.info["ce_authenticated_actor"] = 1
            session.scalar(select(CampaignMember).where(CampaignMember.campaign_id == w["campaign"],
                                                       CampaignMember.user_id == w["user"])).status = "kicked"
            session.flush(); session.rollback()
            # Reuse the session; a rolled-back queued invalidation must not return.
            session.commit()
        with Session(migration_engine) as session:
            assert session.get(CeSubscription, subscription["subscriptionId"]).revoked_at is None
        assert g.poll(w["user"], w["scope"], subscription["subscriptionId"], subscription["cursor"], "connection:a")
    finally:
        uninstall()


def test_unrelated_bulk_legacy_edits_still_work_with_engine_fixture(migration_engine):
    from sqlalchemy import update
    from vtt.creation_engine.store.legacy.guards import install_guards
    engine_world = world(migration_engine, count=1)
    other = world(migration_engine, count=1)
    cutover(engine_world)
    shadow(other)
    uninstall = install_guards(migration_engine, engine_world["gateway"])
    try:
        with Session(migration_engine) as session, session.begin():
            session.execute(update(Character).where(Character.id == other["characters"][0]).values(hp_current=6))
        with Session(migration_engine) as session:
            assert session.get(Character, other["characters"][0]).hp_current == 6
    finally:
        uninstall()


def test_wrong_migration_worker_cannot_freeze_or_replace_a_report(migration_engine):
    w = world(migration_engine, count=1)
    report = shadow(w)
    w["gateway"].kernel.configuration_digest = "sha256:" + "0" * 64
    with pytest.raises(KernelError) as caught:
        command(w, "FreezeScopeForCutover", {"reason": "wrong worker"})
    assert caught.value.code == "EXECUTION_LOCK_MISMATCH"
    with pytest.raises(KernelError):
        w["gateway"].kernel.migration.preview(1, w["scope"])
    with Session(migration_engine) as session:
        assert session.get(CeRuntimeScope, w["scope"]).migration_state == "SHADOW"
        assert session.get(CeMigrationState, w["scope"]).report_id == report["reportId"]
