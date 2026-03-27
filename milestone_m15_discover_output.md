# M15 Discover Output: MVP Launch Handover and Operating Playbook

```
artifact: discover-output
milestone: M15
phase: DISCOVER
status: complete
date: 2026-03-27
```

---

## Discover Focus

- Launch-day execution friction after M14 release gate
- Repeatability of evidence runs for handover
- Minimal operator workflow for "can we launch now?"

---

## Findings

1. M14 delivered robust gate checks, but operators still needed multiple manual commands.
2. There was no single consolidated rehearsal run producing one status artifact.
3. Browser smoke and full regression are useful but should stay optional toggles for speed.

---

## Decisions

- D1: Add a single rehearsal runner that executes release evidence + targeted regression.
- D2: Keep browser smoke/full regression opt-in via env flags.
- D3: Store one consolidated JSON artifact under `ops/monitor/evidence/`.
- D4: Update milestone plan and quickstart to include rehearsal command.

