artifact: deploy-output
date: 2026-04-01
status: deployed

## Deployment

The slice was rolled out live via:

```bash
./deploy_vtt_roll-drauf-de.sh
```

The production app container was rebuilt and restarted successfully.

## Live Evidence

- `https://vtt.roll-drauf.de/static/js/book-scene.js`
  - `last-modified: Wed, 01 Apr 2026 15:46:03 GMT`
- `https://vtt.roll-drauf.de/signup.html`
  - contains `signupSceneTemplate`
  - contains `BookScene.bootstrapRoute('signup')`
- `https://vtt.roll-drauf.de/register.html`
  - contains `registerSceneTemplate`
  - contains `BookScene.bootstrapRoute('register')`
