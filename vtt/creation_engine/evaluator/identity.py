"""The evaluator's identity as an ExecutionLock LockedArtifact (spec v1.1.4 §12).

The digest pins the observable profile and the shipped implementation bytes,
including arithmetic, types and validation dependencies inside this package.
Changing either requires a version bump and a new conformance fixture pin.
The deployment's Python and third-party dependency versions remain governed
by its environment/requirements; this is not an executable-code archive.
"""

import hashlib
from pathlib import Path

from vtt.creation_engine.canonical import content_digest
from vtt.creation_engine.evaluator.effects import Operator, StackPolicy
from vtt.creation_engine.evaluator.engine import Limits, Rounding
from vtt.creation_engine.evaluator.fuel import CHECKPOINT_OPERATIONS, ROOT_ACTION_OPERATIONS
from vtt.creation_engine.evaluator.functions import CORE_ARITIES
from vtt.creation_engine.evaluator.nodes import MAX_DEPTH, MAX_NODES, STAGES

EVALUATOR_ID = "ce.core-safe-1"
EVALUATOR_VERSION = "1.0.0"
_ROOT = Path(__file__).resolve().parents[1]
_SOURCE_FILES = (
    "canonical.py", "errors.py", "rational.py", "types.py", "units.py",
    "contracts/__init__.py", "contracts/core-contracts-1.1.3.schema.json", "contracts/registry-a1.schema.json",
    "evaluator/__init__.py", "evaluator/effects.py", "evaluator/engine.py", "evaluator/fuel.py",
    "evaluator/functions.py", "evaluator/identity.py", "evaluator/nodes.py",
)


def evaluator_descriptor() -> dict:
    limits = Limits()
    return {
        "profile": "core-safe-1",
        "stages": [stage.value for stage in STAGES],
        "operators": [operator.value for operator in Operator],
        "stackPolicies": [policy.value for policy in StackPolicy],
        "rounding": [rounding.value for rounding in Rounding],
        "coreFunctions": [[function_id, arity] for function_id, arity in sorted(CORE_ARITIES.items())],
        "limits": {"maxDepth": MAX_DEPTH, "maxNodes": MAX_NODES, "checkpointOperations": CHECKPOINT_OPERATIONS,
                   "rootActionOperations": ROOT_ACTION_OPERATIONS, "maxApplications": limits.max_applications,
                   "maxDerivedNodes": limits.max_derived_nodes},
    }


def evaluator_artifact() -> dict:
    implementation = {name: "sha256:" + hashlib.sha256((_ROOT / name).read_bytes()).hexdigest()
                      for name in _SOURCE_FILES}
    return {"kind": "evaluator", "id": EVALUATOR_ID, "version": EVALUATOR_VERSION,
            "digest": content_digest({"descriptor": evaluator_descriptor(), "implementation": implementation})}
