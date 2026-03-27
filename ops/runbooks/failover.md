# Failover Runbook

## Trigger Conditions

- Primary database unavailable
- Persistent `503` from `/health/ready`
- Sustained error-rate alert above threshold

## Immediate Actions

1. Declare incident and assign incident lead.
2. Freeze feature deploys.
3. Confirm app health and dependency failures.
4. Switch database endpoint to managed standby/failover target.
5. Restart app instances with updated connection endpoint.

## Verification

1. `GET /health/live` returns `200`.
2. `GET /health/ready` returns `200`.
3. Login and campaign/session smoke flow succeeds.
4. Socket connection and session join work.

## Rollback

- If failover target is unhealthy, rollback to last known good endpoint.
- If app deploy caused incident, redeploy previous image tag.

## Post-Incident

- Capture outage timeline.
- Measure achieved RTO and estimated RPO.
- Add action items to next hardening sprint.
