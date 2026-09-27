"""Explicitly installed RDL G1 host. No import or factory starts a worker."""

from vtt.creation_engine.store.legacy import inputs
from vtt.creation_engine.adapter.mapping import CONFIGURATION, registry
from vtt.creation_engine.store.legacy.migration import MigrationService, OPERATIONS as MIGRATION_OPERATIONS
from vtt.creation_engine.store.legacy.projections import RdlDocuments
from vtt.creation_engine.content.rdl_g1 import rdl_g1_ruleset
from vtt.creation_engine.content import new_id
from vtt.creation_engine.kernel.records import Command, refuse
from vtt.creation_engine.kernel.service import Kernel
from vtt.creation_engine.store.policy import PolicyStore
from vtt.creation_engine.store.public import PublicGateway
from vtt.creation_engine.store.runtime import RuntimeStore
from vtt.creation_engine.store.authoring import AuthoringService
from vtt.creation_engine.compiler.catalog import OPERATIONS as AUTHORING_OPERATIONS


class RdlPolicyStore(PolicyStore):
    def authorize(self, tx, principal, wire):
        if wire["operation"] in {"CreateSandboxScope", "InstantiateRevision"}:
            actor = self.require_scope(tx, principal)
            operator = self.authorize_operator(tx, principal, wire)
            if tx.scope.kind == "sandbox":
                return tx.scope.owner_user_id == principal and operator
            return (wire["operation"] == "InstantiateRevision" and tx.scope.fixture and operator and
                    self.policies(tx).allows(actor, tx.scope.id, "deploy"))
        if wire["operation"] == "OpenLegacyCampaignScope":
            from vtt.creation_engine.store.models import CeWorkspace
            workspace = tx.session.get(CeWorkspace, wire["workspaceId"])
            return bool(workspace and workspace.owner_user_id == principal and
                        wire["payload"]["legacyCampaignId"] == tx.scope.campaign_id and
                        self.authorize_operator(tx, principal, wire))
        if wire["operation"] in MIGRATION_OPERATIONS:
            return self.migration.authorized(tx, principal, wire)
        if wire["operation"] in inputs.OPERATIONS:
            actor = self.require_scope(tx, principal)
            target = tx.instance(wire["payload"].get("instance", wire["payload"].get("item")))
            policies = self.policies(tx)
            if not policies.allows(actor, target.id):
                refuse("NOT_FOUND")
            if wire["operation"] == "SetItemEquipped" and (target.holder_id is None or
                    not policies.allows(actor, target.holder_id, "controls")):
                return False
            return all(policies.allows(actor, target.id, op) for op in ("controls", "adjust"))
        return super().authorize(tx, principal, wire)


class RdlKernel(Kernel):
    def submit(self, principal, raw, *, defer=False, record_request=None):
        command = Command.parse(raw, max_bytes=self.max_request_bytes)
        if command.wire["operation"] in {"CreateSandboxScope", "InstantiateRevision"}:
            if defer or not hasattr(self, "native"):
                refuse("SEMANTIC_INVALID")
            if command.wire["operation"] == "CreateSandboxScope":
                return self.native.create_sandbox(principal, command)
            return self.native.instantiate(principal, command, record_request=record_request)
        if command.wire["operation"] == "OpenLegacyCampaignScope":
            return self.migration.open_campaign(principal, command, record_request=record_request)
        if command.wire["operation"] in MIGRATION_OPERATIONS:
            if defer:
                refuse("SEMANTIC_INVALID")
            return self.migration.submit(principal, command, record_request=record_request)
        if command.wire["operation"] in inputs.OPERATIONS:
            if defer:
                refuse("SEMANTIC_INVALID")
            return inputs.submit(self, principal, command, record_request=record_request)
        result = super().submit(principal, raw, defer=defer, record_request=record_request)
        if hasattr(self, "native") and not defer:
            self.native.drive(command.wire["scopeId"])
        return result


def manual_only(*args):
    refuse("SEMANTIC_INVALID", "imported legacy capabilities are manual until explicitly authored")


class RdlGateway(PublicGateway):
    def submit(self, principal, raw, *, view_id=None):
        command = Command.parse(raw, max_bytes=self.kernel.max_request_bytes)
        if command.wire["operation"] in AUTHORING_OPERATIONS:
            if view_id is not None:
                refuse("OPERATION_FORBIDDEN")
            return self.authoring.submit(principal, raw)
        if command.wire["operation"] not in {"OpenLegacyCampaignScope", "CreateSandboxScope"}:
            return super().submit(principal, raw, view_id=view_id)
        if view_id is not None:
            refuse("OPERATION_FORBIDDEN")
        internal = self.kernel.submit(principal, raw, record_request=self._record_request)
        with self._transaction(internal["scopeId"]) as tx:
            return self._receipt(tx, principal, command, internal)


def build_gateway(engine, *, worker_id=None, clock=None, native_authoring=False):
    from vtt.creation_engine.compiler import runtime as native
    from vtt.creation_engine.store.native import NativeService
    from vtt.creation_engine.store.native_documents import NativeDocuments
    policy = RdlPolicyStore()
    configuration = native.CONFIGURATION if native_authoring else CONFIGURATION
    kernel = RdlKernel(RuntimeStore(engine, clock=clock), ruleset=native.ruleset() if native_authoring else rdl_g1_ruleset(),
        schema_registry=native.registry() if native_authoring else registry(),
        configuration=configuration, authorize=policy.authorize, resolve_activity=native.resolve_activity if native_authoring else manual_only,
        prepare=manual_only, worker_id=worker_id or new_id("worker"))
    policy.migration = kernel.migration = MigrationService(kernel, policy, configuration=configuration)
    if native_authoring:
        kernel.native = NativeService(kernel, policy)
        kernel.prepare, kernel.responders = kernel.native.prepare, kernel.native.responders
        kernel.decision_facts = lambda tx, action, question: {"nativeRegistration": "g1.flames:1"}
    documents = NativeDocuments(kernel.ruleset) if native_authoring else RdlDocuments(kernel.ruleset)
    gateway = RdlGateway(kernel, policy, configuration=configuration, document=documents.document,
        snapshot_documents=documents.snapshot, event_document=documents.event, outcome_document=documents.outcome,
        representation_version="g1.native:1" if native_authoring else "rdl-g1-legacy:1")
    gateway.authoring = AuthoringService(kernel.store, fault=lambda point: kernel.fault(point), native_runtime=native_authoring)
    return gateway


def install(app, *, gateway=None):
    """Install after migrations, only when a CE surface is explicitly enabled."""
    from vtt.extensions import db
    from vtt.creation_engine.store.legacy.compatibility import LegacyCompatibility
    from vtt.creation_engine.store.legacy.guards import install_guards
    from .legacy_http import install_http
    if not any(app.config.get(flag) for flag in ("CE_RUNTIME", "CE_SHADOW", "CE_AUTHORING")):
        raise ValueError("enable an engine surface before installing the legacy host")
    with app.app_context():
        gateway = gateway or build_gateway(db.engine, native_authoring=app.config.get("CE_AUTHORING", False))
        compatibility = LegacyCompatibility(gateway)
        install_guards(db.engine, gateway)
    app.extensions["ce_gateway"], app.extensions["ce_legacy"] = gateway, compatibility
    install_http(app, compatibility)
    socketio = app.extensions.get("socketio")
    if socketio is not None:
        @socketio.on_error(namespace="/")
        def legacy_socket_error(exc):
            from flask_socketio import emit
            from vtt.creation_engine.errors import ContractViolation
            from vtt.creation_engine.policy.public_errors import public_error
            if not isinstance(exc, ContractViolation):
                raise exc
            db.session.rollback()
            body, status = public_error(exc)
            emit("ce:error", body)
            return body

    @app.cli.command("ce-maintain")
    def maintain():
        """Run the installed host's fenced 30-second heartbeat/expiry worker."""
        from threading import Event
        from vtt.creation_engine.store.maintenance import run
        stop = Event()
        try:
            run(gateway, stop)
        except KeyboardInterrupt:
            stop.set()
    return gateway
