"""One legacy authority guard for ORM writers, including model helper methods.

Install on the host database engine explicitly. Scope locks are acquired before
SQLAlchemy flushes legacy mutations and retained to commit. The same hook also
coordinates membership/account revocation; callers still enforce their normal
route authorization. Bulk mutation shortcuts cannot bypass the guard.
"""

from sqlalchemy import event, inspect, or_, select
from sqlalchemy.orm import Session

from vtt.creation_engine.kernel.records import refuse
from vtt.creation_engine.store.migration_models import CeLegacyScopeLink, CeMigrationLedger, CeRepresentation
from vtt.creation_engine.store.runtime import RuntimeTransaction
from vtt.creation_engine.store.runtime_models import CeRuntimeScope
from vtt.models.campaign import Campaign
from vtt.models.campaign_member import CampaignMember
from vtt.models.character import Character
from vtt.models.equipment import Equipment
from vtt.models.inventory_item import InventoryItem
from vtt.models.spell import Spell
from vtt.models.token_state import TokenState
from vtt.models.user import User

LEGACY_MODELS = (Character, Equipment, InventoryItem, Spell, TokenState)
POLICY_FIELDS = {User: {"is_active", "is_suspended", "account_state", "deleted_at"},
                 CampaignMember: {"campaign_id", "user_id", "campaign_role", "status"},
                 Campaign: {"owner_id", "status", "deleted_at"}}
TOKEN_PRESENTATION = {"x", "y", "size", "rotation", "visibility", "name", "token_type", "initiative",
                      "metadata_json", "sight_range", "is_loot_source", "version", "updated_by", "updated_at", "deleted_at"}


def changed_fields(row):
    return {attribute.key for attribute in inspect(row).attrs if attribute.history.has_changes()}


def _links(session, character=None, campaign_ids=(), owners=()):
    filters = []
    if character is not None:
        if character.campaign_id:
            campaign_ids = {*campaign_ids, character.campaign_id}
        elif character.user_id:
            owners = {*owners, character.user_id}
    if campaign_ids:
        filters.append((CeLegacyScopeLink.source_type == "campaign") & CeLegacyScopeLink.source_id.in_(campaign_ids))
    if owners:
        filters.append((CeLegacyScopeLink.source_type == "sandbox") & CeLegacyScopeLink.source_id.in_(owners))
    return set(session.scalars(select(CeLegacyScopeLink.scope_id).where(or_(*filters)))) if filters else set()


def legacy_scopes(session, row):
    if isinstance(row, Character):
        character = row
    else:
        character = session.get(Character, row.character_id) if row.character_id else None
    scopes = _links(session, character, campaign_ids=(row.campaign_id,) if isinstance(row, TokenState) else ())
    if character and character.id:
        scopes.update(session.scalars(select(CeMigrationLedger.scope_id).where(
            CeMigrationLedger.source_type == "vtt.character", CeMigrationLedger.source_id == character.id)))
    # An attempted reassignment must also fence the previous occurrence.
    if not isinstance(row, Character):
        for old_id in inspect(row).attrs.character_id.history.deleted:
            old = session.get(Character, old_id) if old_id else None
            scopes.update(_links(session, old))
    return scopes


def legacy_write_guard(session, row, scope):
    """All ORM legacy writers enter here before their SQL is emitted."""
    state = scope.migration_state
    if state in {"LEGACY", "SHADOW"}:
        return
    if state != "ENGINE":
        refuse("MIGRATION_STATE_CONFLICT")
    fields = changed_fields(row)
    if isinstance(row, Character) and fields & {"campaign_id", "user_id"}:
        refuse("SCOPE_TRANSFER_UNSUPPORTED")
    if isinstance(row, TokenState):
        if row in session.new:
            # New tokens are presentations; client HP never seeds another ledger.
            if row.character_id is None:
                refuse("LEGACY_FIELD_READ_ONLY")
            representation = session.get(CeRepresentation, ("vtt.character", row.character_id))
            if representation is None or representation.scope_id != scope.id:
                refuse("SCOPE_TRANSFER_UNSUPPORTED")
            row.hp_current = row.hp_max = None
            session.info.setdefault("ce_new_tokens", []).append(row)
            return
        if row not in session.deleted and fields <= TOKEN_PRESENTATION:
            return
    refuse("LEGACY_FIELD_READ_ONLY")


def _actor(session):
    actor = session.info.get("ce_authenticated_actor")
    if actor is None:
        from flask import has_request_context
        from flask_jwt_extended import get_jwt_identity
        if has_request_context():
            try:
                actor = int(get_jwt_identity())
            except (RuntimeError, TypeError, ValueError):
                pass
    if type(actor) is not int or actor <= 0:
        refuse("OPERATION_FORBIDDEN", "policy writers require an authenticated audit actor")
    return actor


def install_guards(engine, gateway):
    """One registration per SQLAlchemy engine; return an uninstall function for tests."""
    existing = getattr(engine, "_ce_legacy_guards", None)
    if existing:
        return existing

    def before_flush(session, context, instances):
        if session.get_bind() is not engine:
            return
        with session.no_autoflush:
            legacy, policy_scopes, all_scopes = [], set(), set()
            for row in set(session.new) | set(session.dirty) | set(session.deleted):
                if type(row) in LEGACY_MODELS:
                    scopes = legacy_scopes(session, row)
                    legacy.append((row, scopes)); all_scopes.update(scopes)
                elif type(row) in POLICY_FIELDS and (row in session.new or row in session.deleted or changed_fields(row) & POLICY_FIELDS[type(row)]):
                    if isinstance(row, User):
                        campaigns = set(session.scalars(select(CampaignMember.campaign_id).where(CampaignMember.user_id == row.id)))
                        campaigns.update(session.scalars(select(Campaign.id).where(Campaign.owner_id == row.id)))
                        scopes = _links(session, campaign_ids=campaigns, owners=(row.id,))
                    else:
                        scopes = _links(session, campaign_ids=(row.campaign_id if isinstance(row, CampaignMember) else row.id,))
                    policy_scopes.update(scopes); all_scopes.update(scopes)
            locked = {row.id: row for row in session.scalars(select(CeRuntimeScope).where(
                CeRuntimeScope.id.in_(all_scopes)).order_by(CeRuntimeScope.id).with_for_update())} if all_scopes else {}
            for row, scopes in legacy:
                for scope_id in sorted(scopes):
                    legacy_write_guard(session, row, locked[scope_id])
            if policy_scopes:
                actor = _actor(session)
                session.info.setdefault("ce_policy_writes", {}).update({key: actor for key in policy_scopes})

    def before_commit(session):
        if session.get_bind() is not engine or session.get_nested_transaction() is not None:
            return
        session.flush()
        for token in session.info.pop("ce_new_tokens", []):
            if token not in session.deleted:
                original = session.get(CeRepresentation, ("vtt.character", token.character_id))
                if session.get(CeRepresentation, ("vtt.token", token.id)) is None:
                    session.add(CeRepresentation(source_type="vtt.token", source_id=token.id,
                        instance_id=original.instance_id, scope_id=original.scope_id))
        for scope_id, actor in sorted(session.info.pop("ce_policy_writes", {}).items()):
            scope = session.get(CeRuntimeScope, scope_id)
            tx = RuntimeTransaction(gateway.store, session, scope)
            gateway.policy.changed(tx, gateway.kernel, actor, reason="legacy membership/account policy change")
        session.flush()

    def transaction_end(session, transaction):
        if transaction.parent is None:
            session.info.pop("ce_new_tokens", None)
            session.info.pop("ce_policy_writes", None)

    def bulk_guard(state):
        if state.session.get_bind() is not engine or not (state.is_update or state.is_delete):
            return
        table = getattr(state.statement, "table", None)
        models = {m.__tablename__: m for m in LEGACY_MODELS + tuple(POLICY_FIELDS)}
        if table is None or table.name not in models:
            return
        with state.session.no_autoflush:
            model = models[table.name]
            query = select(model)
            if state.statement.whereclause is not None:
                query = query.where(state.statement.whereclause)
            rows = list(state.session.scalars(query))
            scopes = set()
            for row in rows:
                if model in LEGACY_MODELS:
                    scopes.update(legacy_scopes(state.session, row))
                elif model is User:
                    campaigns = set(state.session.scalars(select(CampaignMember.campaign_id).where(CampaignMember.user_id == row.id)))
                    campaigns.update(state.session.scalars(select(Campaign.id).where(Campaign.owner_id == row.id)))
                    scopes.update(_links(state.session, campaign_ids=campaigns, owners=(row.id,)))
                else:
                    scopes.update(_links(state.session, campaign_ids=(row.campaign_id if model is CampaignMember else row.id,)))
            locked = list(state.session.scalars(select(CeRuntimeScope).where(CeRuntimeScope.id.in_(scopes))
                                                .order_by(CeRuntimeScope.id).with_for_update())) if scopes else []
            if model in LEGACY_MODELS:
                if any(scope.migration_state not in {"LEGACY", "SHADOW"} for scope in locked):
                    refuse("LEGACY_FIELD_READ_ONLY", "bulk mechanical edits require engine commands")
            elif scopes:
                actor = _actor(state.session)
                state.session.info.setdefault("ce_policy_writes", {}).update({key: actor for key in scopes})

    callbacks = (("before_flush", before_flush), ("before_commit", before_commit),
                 ("after_transaction_end", transaction_end), ("do_orm_execute", bulk_guard))
    for name, callback in callbacks:
        event.listen(Session, name, callback)

    def uninstall():
        for name, callback in callbacks:
            event.remove(Session, name, callback)
        delattr(engine, "_ce_legacy_guards")
    engine._ce_legacy_guards = uninstall
    return uninstall
