"""M8 tests: operational health and metrics endpoints."""

import pytest

from vtt_app import create_app
from vtt_app.extensions import db
from vtt_app.models import Role


@pytest.fixture
def app():
    app = create_app(config_name="testing")
    with app.app_context():
        db.create_all()
        for role_name in ["Player", "DM", "Admin"]:
            db.session.add(Role(name=role_name))
        db.session.commit()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


class TestOpsEndpoints:
    def test_request_id_header_propagation(self, client):
        response = client.get("/health/live", headers={"X-Request-ID": "m11-test-id"})
        assert response.status_code == 200
        assert response.headers.get("X-Request-ID") == "m11-test-id"

    def test_request_id_header_auto_generation(self, client):
        response = client.get("/health/live")
        assert response.status_code == 200
        assert response.headers.get("X-Request-ID")

    def test_health_live(self, client):
        response = client.get("/health/live")
        assert response.status_code == 200
        payload = response.get_json()
        assert payload["status"] == "ok"
        assert "started_at" in payload

    def test_health_ready(self, client):
        response = client.get("/health/ready")
        assert response.status_code == 200
        payload = response.get_json()
        assert payload["status"] in {"ready", "degraded"}
        assert "dependencies" in payload
        assert "database" in payload["dependencies"]

    def test_health_release(self, client):
        response = client.get("/health/release")
        assert response.status_code == 200
        payload = response.get_json()
        assert payload["status"] == "go"
        assert payload["release_ready"] is True
        assert "checks" in payload
        assert "error_budget" in payload["checks"]
        assert "rollback_runbooks" in payload["checks"]

    def test_health_release_fails_when_error_budget_exceeded(self, app, client):
        with app.app_context():
            store = app.extensions["ops_metrics"]
            store["requests_total"] = 200
            store["by_status"] = {"200": 190, "500": 10}
            app.config["RELEASE_GATE_MAX_5XX_RATE"] = 0.01
            app.config["RELEASE_GATE_MIN_REQUESTS"] = 0
            app.config["RELEASE_GATE_REQUIRE_RUNBOOKS"] = False

        response = client.get("/health/release")
        assert response.status_code == 503
        payload = response.get_json()
        assert payload["status"] == "no-go"
        assert payload["checks"]["error_budget"]["ok"] is False

    def test_health_release_fails_when_required_runbook_missing(self, app, client):
        with app.app_context():
            store = app.extensions["ops_metrics"]
            store["requests_total"] = 50
            store["by_status"] = {"200": 50}
            app.config["RELEASE_GATE_MAX_5XX_RATE"] = 1.0
            app.config["RELEASE_GATE_MAX_SLOW_REQUEST_RATE"] = 1.0
            app.config["RELEASE_GATE_MAX_SOCKET_RESYNC_RATE"] = 1.0
            app.config["RELEASE_GATE_MAX_SOCKET_CONFLICT_RATE"] = 1.0
            app.config["RELEASE_GATE_REQUIRE_RUNBOOKS"] = True
            app.config["RELEASE_GATE_REQUIRED_FILES"] = (
                "ops/runbooks/backup_restore.md",
                "ops/runbooks/this_file_does_not_exist.md",
            )

        response = client.get("/health/release")
        assert response.status_code == 503
        payload = response.get_json()
        assert payload["status"] == "no-go"
        assert payload["checks"]["rollback_runbooks"]["ok"] is False
        assert "ops/runbooks/this_file_does_not_exist.md" in payload["checks"]["rollback_runbooks"]["missing_files"]

    def test_metrics_plain_text(self, client):
        client.get("/health/live")
        client.get("/health/ready")
        client.get("/health/release")
        client.get("/api/auth/check")
        response = client.get("/metrics")
        assert response.status_code == 200
        text = response.get_data(as_text=True)
        assert "vtt_requests_total" in text
        assert "vtt_uptime_seconds" in text
        assert "vtt_requests_by_route_total" in text
        assert 'route="/health/live"' in text
        assert "vtt_request_latency_bucket_total" in text
        assert "vtt_socket_events_total" in text
        assert "vtt_socket_conflicts_total" in text
        assert "vtt_socket_resync_requests_total" in text
        assert "vtt_socket_reconnect_recoveries_total" in text
        assert "vtt_play_transitions_total" in text
