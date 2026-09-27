"""Stable public codes; internal details and unknown diagnostic identifiers stay private."""

STATUS = {"SCHEMA_INVALID": 400, "NOT_FOUND": 404, "OPERATION_FORBIDDEN": 403,
          "SEMANTIC_INVALID": 422, "BUDGET_EXCEEDED": 422, "PAYLOAD_TOO_LARGE": 413,
          "ADMISSION_LIMIT": 429, "WORKER_FENCED": 503, "LEASE_BUSY": 503, "ENGINE_UNAVAILABLE": 503,
          "CUTOVER_FIXTURE_ONLY": 403, "BINDING_NOT_OVERRIDEABLE": 422}
CONFLICTS = {"IDEMPOTENCY_KEY_REUSE", "SCOPE_BUSY", "DECISION_STALE", "AUTHORITY_EPOCH_MISMATCH",
             "SCOPE_VERSION_CONFLICT", "ACTION_VERSION_CONFLICT", "ACTION_STATE_CONFLICT", "ACTION_CANCELLED",
             "EXECUTION_LOCK_MISMATCH", "EFFECT_CONFLICT", "RESOURCE_BOUND_EXCEEDED", "REVISION_NOT_IN_LOCK",
             "MIGRATION_STATE_CONFLICT", "PARITY_UNRESOLVED", "SCOPE_NOT_QUIESCENT",
             "LEGACY_FIELD_READ_ONLY", "SCOPE_TRANSFER_UNSUPPORTED", "DRAFT_VERSION_CONFLICT",
             "AUTHORING_REGISTRY_MISMATCH", "GUIDE_DEAD_END", "QUESTION_REQUIRED", "QUESTION_NOT_READY",
             "PRESET_PREVIEW_STALE", "QUALITY_CLAIM_UNMET"}


def safe_code(code):
    return code if code is None or code in STATUS or code in CONFLICTS else "SEMANTIC_INVALID"


def public_error(exc):
    code = safe_code(exc.code)
    body = {"error": {"code": code}}
    if code == "QUALITY_CLAIM_UNMET" and hasattr(exc, "gates"):
        body["error"]["gates"] = exc.gates
    if code == "AUTHORITY_EPOCH_MISMATCH":
        body["refresh"] = "Reload the current authorized scope projection before retrying."
    return body, STATUS.get(code, 409)
