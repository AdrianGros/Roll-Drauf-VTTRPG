# Frozen evidence inputs

These snapshots make the reconciliation reproducible. They are not another live authority register.

`approved-*` files retain the exact approved contract used for reconciliation. The approval record and implementation/context snapshots establish decisions and the state observed at the start. The live repository entry point is `docs/creation-engine/README.md`.

Files beginning `withdrawn-v1.2` are explicitly non-authoritative evidence of the erroneous rewrite. They are used only to preserve research and translate old IDs. Do not implement their wire schema or treat their T47–T64 meanings as approved. The archived original ZIP hash is recorded in the source manifest.
