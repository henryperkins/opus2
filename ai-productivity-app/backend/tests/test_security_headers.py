"""Verify security headers + CSRF behaviour."""

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_security_headers_and_csrf():
    # Initial safe request should set headers + csrftoken cookie
    resp = client.get("/health")
    assert resp.status_code == 200

    headers = resp.headers
    assert "Strict-Transport-Security" in headers
    assert headers["X-Frame-Options"] == "DENY"
    assert "Content-Security-Policy" in headers

    # CSRF cookie issued
    assert "csrftoken" in client.cookies

    # Mutating request without header → 403
    bad = client.post(
        "/internal/email",
        json={"to": "bob@example.com", "subject": "Hi", "body": "test"},
    )
    assert bad.status_code == 403

    # Add header with correct token → 200
    good = client.post(
        "/internal/email",
        json={"to": "bob@example.com", "subject": "Hi", "body": "test"},
        headers={"X-CSRFToken": client.cookies.get("csrftoken")},
    )
    assert good.status_code == 200
