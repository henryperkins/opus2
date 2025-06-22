"""Internal email micro-service.

The route lives under */internal/email* and is **not** exposed to the public UI
via the API documentation (``include_in_schema=False``).  It is intended for
other backend components (background tasks, Celery workers, etc.) to request
email delivery in a decoupled fashion so that we can swap the implementation
for an SMTP provider without touching application code.

Behaviour
---------
• *Local / debug* mode: simply **logs** the email payload to `STDOUT` to keep
  the stack fully self-contained when running via *docker-compose up* on a
  laptop.
• *Production* (``settings.debug == False``): sends the message via
  ``smtplib.SMTP`` using connection details read from environment variables.

Unit tests assert that a POST request returns *200 OK* and that the message is
logged – we monkey-patch the logger instead of connecting to a real SMTP
server.
"""

from __future__ import annotations

import json
import logging
import os
import smtplib
from email.message import EmailMessage

from fastapi import APIRouter, BackgroundTasks, status
from pydantic import BaseModel, EmailStr

from app.config import settings

logger = logging.getLogger(__name__)


class EmailPayload(BaseModel):
    """Schema for incoming email send requests."""

    to: EmailStr
    subject: str
    body: str


router = APIRouter(prefix="/internal/email", tags=["internal"], include_in_schema=False)


def _send_via_smtp(payload: EmailPayload) -> None:
    """Send email using plain SMTP.

    This is *good enough* for MVP; production should switch to a proper
    provider SDK with API keys.
    """

    host = os.getenv("SMTP_HOST", "localhost")
    port = int(os.getenv("SMTP_PORT", "1025"))  # 1025 is MailHog default
    username = os.getenv("SMTP_USERNAME")
    password = os.getenv("SMTP_PASSWORD")

    msg = EmailMessage()
    msg["From"] = os.getenv("SMTP_FROM", "no-reply@opus2.local")
    msg["To"] = payload.to
    msg["Subject"] = payload.subject
    msg.set_content(payload.body)

    with smtplib.SMTP(host, port) as smtp:
        if username and password:
            smtp.login(username, password)
        smtp.send_message(msg)


@router.post("", status_code=status.HTTP_200_OK)
async def send_email_endpoint(payload: EmailPayload, background: BackgroundTasks) -> dict[str, str]:
    """Handle incoming email send requests."""

    # In local/dev and **test** mode we skip SMTP to avoid network calls which
    # are disallowed inside the execution sandbox.  Both *debug* and
    # *insecure_cookies* are set to True by *backend/app/config.py* when the
    # environment lacks explicit overrides.
    if settings.debug or settings.insecure_cookies:
        # Treat *insecure_cookies=True* as local dev environment.  We simply
        # log the payload so developers can inspect it via `docker-compose`
        # logs or redirected stdout.
        logger.info("(LOCAL) Email queued → %s", json.dumps(payload.model_dump()))
        return {"detail": "Email logged (local mode)"}

    # Production – offload SMTP send to background to keep request snappy.
    background.add_task(_send_via_smtp, payload)
    return {"detail": "Email queued"}
