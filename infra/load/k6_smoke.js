import http from "k6/http";
import { check, sleep } from "k6";

export const options = {
  vus: 50,
  duration: "2m",
  thresholds: {
    http_req_failed: ["rate<0.01"],
    http_req_duration: ["p(95)<500"],
  },
};

const BASE_URL = __ENV.BASE_URL || "http://localhost:5000";
const PLAY_CAMPAIGN_ID = __ENV.PLAY_CAMPAIGN_ID || "1";
const PLAY_SESSION_ID = __ENV.PLAY_SESSION_ID || "1";
const PLAY_ACCESS_TOKEN = __ENV.PLAY_ACCESS_TOKEN || "";

export default function () {
  const live = http.get(`${BASE_URL}/health/live`);
  check(live, {
    "live status 200": (r) => r.status === 200,
  });

  const ready = http.get(`${BASE_URL}/health/ready`);
  check(ready, {
    "ready status 200 or 503": (r) => r.status === 200 || r.status === 503,
  });

  const authCheck = http.get(`${BASE_URL}/api/auth/check`);
  check(authCheck, {
    "auth check status 200": (r) => r.status === 200,
  });

  const playBootstrapUrl = `${BASE_URL}/api/play/campaigns/${PLAY_CAMPAIGN_ID}/sessions/${PLAY_SESSION_ID}/bootstrap`;
  const playReadyCheckUrl = `${BASE_URL}/api/play/campaigns/${PLAY_CAMPAIGN_ID}/sessions/${PLAY_SESSION_ID}/ready-check`;
  const playHeaders = PLAY_ACCESS_TOKEN
    ? {
        headers: {
          Cookie: `access_token_cookie=${PLAY_ACCESS_TOKEN}`,
        },
      }
    : {};

  const bootstrap = http.get(playBootstrapUrl, playHeaders);
  check(bootstrap, {
    "play bootstrap reachable": (r) => [200, 401, 403, 404].includes(r.status),
  });

  const readyCheck = http.get(playReadyCheckUrl, playHeaders);
  check(readyCheck, {
    "play ready-check reachable": (r) => [200, 401, 403, 404].includes(r.status),
  });

  sleep(1);
}
