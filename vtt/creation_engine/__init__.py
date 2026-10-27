"""Roll Drauf Creation Engine: Matt's Eagle Homebrew editor hosted in the VTT.

The editor itself is vendor/eagle-homebrew (pinned, unmodified), bundled by frontend/eagle-homebrew-host.
This package serves it and answers the Eagle Flight Control requests it sends:
`routes.py` (HTTP), `documents.py` (pure rules), `models.py` (storage), `capability.py` (who may open it).
`species.py` (pure playability check of a Species plus the VTT supplement) and `species_routes.py` (check and
publish an immutable, playable 2024 revision; gated by CE_PLAYABLE_SPECIES) make an Eagle Species a character origin.
`canonical.py` and `errors.py` are shared RFC 8785 JSON helpers used by the Regelwerk.
The previous engine (G1) is archived under archive/creation-engine-g1/.
"""
