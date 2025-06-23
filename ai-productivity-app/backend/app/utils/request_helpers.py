"""Request utility helpers for extracting client information."""
from fastapi import Request


def real_ip(request: Request) -> str:
    """Return the client's public IP, honoring X-Forwarded-For."""
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
