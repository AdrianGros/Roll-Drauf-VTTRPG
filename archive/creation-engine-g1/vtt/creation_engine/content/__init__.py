"""Content model (G1 work package WP3; spec v1.1.4 §4, §6, §12–13, §15).

Pure domain code: schema registry, ruleset packages, workspaces, definitions,
immutable revisions, versioned drafts and execution locks. Persistence lives
in ``vtt.creation_engine.store``.
"""

from vtt.creation_engine.content.locks import PROFILE_ID, ExecutionLock, resolve_lock
from vtt.creation_engine.content.records import (Definition, Draft, DraftAnswer, Revision, Workspace, create_revision,
                                                 new_id, require_draft_version)
from vtt.creation_engine.content.registry import SchemaRegistry, SchemaType, SchemaTypeRef
from vtt.creation_engine.content.ruleset import AdjustBoundPolicy, BindingTemplate, ChoiceTemplate, ResourceSpec, Ruleset

__all__ = [
    "AdjustBoundPolicy", "BindingTemplate", "ChoiceTemplate", "Definition", "Draft", "DraftAnswer", "ExecutionLock", "PROFILE_ID",
    "ResourceSpec", "Revision", "Ruleset", "SchemaRegistry", "SchemaType", "SchemaTypeRef", "Workspace",
    "create_revision", "new_id", "require_draft_version", "resolve_lock",
]
