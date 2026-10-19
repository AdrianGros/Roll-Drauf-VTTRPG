# Creation Engine: Eagle Homebrew host

Runs Matt's **Eagle Homebrew** editor (https://github.com/MattTheEagle/EagleHomebrew) unmodified inside the VTT.
This folder contains only what replaces Foundry: `src/foundry-shim.ts` (window, form fields, pickers, i18n,
notifications, `CONFIG.DND5E`), `src/vtt-context.ts` (Matt's `HomebrewWindowContext` and the Eagle Flight
Control requests, answered by `vtt/creation_engine/routes.py`) and `src/entry.ts` (the page, the VTT
counterpart of Matt's `v13/module.ts`).

Changes to the editor itself belong in Matt's repo. To take a new version, update both lines in
`eagle-homebrew.pin`, rebuild, and run the tests below.

```
npm run vendor      # vendor/eagle-homebrew at the pinned commit (verifies the SHA, refuses local edits)
npm ci
npm run typecheck   # this folder plus Matt's v13 code against the shim
npm run build       # -> vtt/static/eagle-homebrew/ (git-ignored; the Docker image builds it too)
```

Tests: `tests/test_creation_engine_eagle.py` (server contract) and `tests/test_creation_engine_eagle_browser.py`
(Chromium against the real server; skipped while the bundle is not built). `npm run build:spike && npm run e2e:spike`
opens all 18 editors without a server.

`data/` is generated from dnd5e 5.3.3 (`DND5E_ROOT=<dnd5e checkout> npm run data:dnd5e`); see `data/LICENSE-dnd5e.txt`.
