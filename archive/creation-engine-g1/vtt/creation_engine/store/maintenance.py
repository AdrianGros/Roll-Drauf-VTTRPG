"""Host worker entry point; one tick every 30 seconds, using durable lease fences."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from vtt.creation_engine.errors import ContractViolation
from vtt.creation_engine.store.policy_models import CeSubscription, CeViewAsSession
from vtt.creation_engine.store.runtime_models import CePendingDecision, CeAction


def tick(gateway):
    with Session(gateway.store.engine) as session:
        decisions = set(session.scalars(select(CePendingDecision.scope_id).where(CePendingDecision.status == "open").distinct()))
        views = set(session.scalars(select(CeViewAsSession.scope_id).where(CeViewAsSession.closed_at.is_(None)).distinct()))
        subscriptions = set(session.scalars(select(CeSubscription.scope_id).distinct()))
        active = set(session.scalars(select(CeAction.scope_id).where(CeAction.state == "ACTIVE").distinct())) if hasattr(gateway.kernel, "native") else set()
    for scope_id in sorted(decisions | views | subscriptions | active):
        gateway.maintain(scope_id)
        if scope_id in decisions:
            with gateway.store.transaction(scope_id) as tx:
                if not gateway.supports_scope(tx):
                    continue  # a worker with this scope's pinned registrations must handle it
            try:
                fence = gateway.kernel.claim(scope_id)
                gateway.kernel.heartbeat(scope_id, fence=fence)
            except ContractViolation as exc:
                if exc.code not in {"LEASE_BUSY", "WORKER_FENCED"}:
                    raise
        if hasattr(gateway.kernel, "native"):
            try:
                gateway.kernel.native.drive(scope_id)
            except ContractViolation as exc:
                if exc.code not in {"LEASE_BUSY", "WORKER_FENCED", "ACTION_VERSION_CONFLICT", "ACTION_STATE_CONFLICT"}:
                    raise


def run(gateway, stop):
    """Run in the configured engine worker; stop is a threading.Event-compatible port."""
    while not stop.is_set():
        tick(gateway)
        stop.wait(30)
