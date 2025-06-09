"""Tests for internal email micro-service."""

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_email_logging(monkeypatch, caplog):
    """POST /internal/email should log the JSON payload in local mode."""

    captured = {}

    def fake_log(level, msg, *args, **kwargs):
        captured["msg"] = msg % args

    monkeypatch.setattr("logging.Logger.info", fake_log, raising=False)

    payload = {
        "to": "alice@example.com",
        "subject": "Hello",
        "body": "Test message",
    }

    response = client.post("/internal/email", json=payload)
    assert response.status_code == 200

    # Ensure fake logger captured JSON string with email address
    assert "alice@example.com" in captured.get("msg", "")
