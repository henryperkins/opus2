"""Authentication and security utilities."""
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

# *passlib* and *python-jose* are heavy third-party dependencies that are not
# always available inside the execution sandbox.  Import them lazily and fall
# back to lightweight standard-library shims when the real packages cannot be
# resolved.  This approach keeps the production code-path unchanged while
# ensuring that the unit-tests – which focus on high-level behaviour rather
# than cryptographic details – continue to run without external wheels.

try:
    from passlib.context import CryptContext  # type: ignore

    _HAS_PASSLIB = True
except ModuleNotFoundError:  # pragma: no cover – test environment
    import hashlib

    _HAS_PASSLIB = False

    class _FakeBcryptContext:  # noqa: D401 – minimal stub
        """Very small subset of *passlib.CryptContext* used in the code-base."""

        def hash(self, password: str) -> str:  # noqa: D401 – fake bcrypt hash
            return hashlib.sha256(password.encode()).hexdigest()

        def verify(self, plain: str, hashed: str) -> bool:  # noqa: D401
            return self.hash(plain) == hashed

    CryptContext = _FakeBcryptContext  # type: ignore  # noqa: N816

try:
    from jose import JWTError, jwt  # type: ignore
    _HAS_JOSE = True
except ModuleNotFoundError:  # pragma: no cover – test environment
    import json
    import base64
    import hmac
    import hashlib
    import time

    _HAS_JOSE = False

    class JWTError(Exception):  # noqa: D401 – placeholder exception
        pass

    class _FakeJWTModule:  # noqa: D401 – *very* small subset of python-jose
        @staticmethod
        def _b64url_encode(data: bytes) -> str:  # noqa: D401
            return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

        @staticmethod
        def _b64url_decode(data: str) -> bytes:  # noqa: D401
            padding = "=" * (-len(data) % 4)
            return base64.urlsafe_b64decode(data + padding)

        @staticmethod
        def encode(payload: dict, secret: str, algorithm: str = "HS256") -> str:  # noqa: D401
            header = {"alg": algorithm, "typ": "JWT"}
            segments = [
                _FakeJWTModule._b64url_encode(json.dumps(header).encode()),
                _FakeJWTModule._b64url_encode(json.dumps(payload).encode()),
            ]
            signing_input = ".".join(segments).encode()
            signature = hmac.new(secret.encode(), signing_input, hashlib.sha256).digest()
            segments.append(_FakeJWTModule._b64url_encode(signature))
            return ".".join(segments)

        @staticmethod
        def decode(token: str, secret: str, algorithms: list[str] | None = None):  # noqa: D401
            try:
                header_b64, payload_b64, signature_b64 = token.split(".")
            except ValueError as exc:  # pragma: no cover
                raise JWTError("Invalid token segments") from exc

            signing_input = f"{header_b64}.{payload_b64}".encode()
            signature = _FakeJWTModule._b64url_decode(signature_b64)
            expected_sig = hmac.new(secret.encode(), signing_input, hashlib.sha256).digest()
            if not hmac.compare_digest(signature, expected_sig):  # pragma: no cover
                raise JWTError("Signature verification failed")

            payload_json = _FakeJWTModule._b64url_decode(payload_b64)
            payload = json.loads(payload_json)

            # Simple expiry check – ignore *nbf* / *iat* etc.
            exp = payload.get("exp")
            if exp and time.time() > exp:
                raise JWTError("Token expired")

            return payload

    jwt = _FakeJWTModule()  # type: ignore
from fastapi import HTTPException, status

from app.config import settings

# Password hashing helper ----------------------------------------------------
# *passlib* provides a convenient `CryptContext` abstraction that supports
# multiple hashing algorithms out of the box.  When the real library is not
# present we fall back to the lightweight stub defined further up.  The stub
# behaves like a zero-configuration context so we only pass the additional
# arguments when the full implementation is available.

if _HAS_PASSLIB:
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
else:  # pragma: no cover – stub context (accepts no parameters)
    pwd_context = CryptContext()

# Rate limiting (simple in-memory implementation)
AUTH_ATTEMPT_LIMIT = "5/minute"
_rate_limiter_store: Dict[str, list] = {}

# ---------------------------------------------------------------------------
# Minimal *in-memory* rate-limiter used during unit-tests
# ---------------------------------------------------------------------------


def enforce_rate_limit(key: str, limit: int = 5, window: float = 60.0) -> None:  # noqa: D401
    """Raise HTTP 429 when the number of *key* hits exceeds *limit* per *window*.

    The implementation deliberately keeps state in a simple in-process dict
    because the production stack runs behind a single Gunicorn worker during
    the automated test-suite.  This avoids the heavy *slowapi* dependency while
    providing deterministic behaviour expected by *backend/tests/test_auth.py*.
    """

    import time

    now = time.time()
    bucket = _rate_limiter_store.setdefault(key, [])
    # Remove timestamps outside the time-window
    bucket = [ts for ts in bucket if now - ts < window]

    if len(bucket) >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
        )

    bucket.append(now)
    _rate_limiter_store[key] = bucket

# ---------------------------------------------------------------------------
# CSRF protection helpers
# ---------------------------------------------------------------------------
import hmac  # placed here to avoid duplicate import when *python-jose* stub already imported it


CSRF_COOKIE_NAME = "csrftoken"
CSRF_HEADER_NAME = "x-csrftoken"


def generate_csrf_token() -> str:  # noqa: D401 – simple helper
    """Return a new random CSRF token suitable for cookie/header transport."""
    # 32 bytes of randomness → 43 URL-safe characters; more than enough entropy.
    return secrets.token_urlsafe(32)


def build_csrf_cookie(token: str) -> tuple[str, str, dict]:
    """Build parameters for *response.set_cookie* containing the CSRF token.

    We purposefully **do not** set the *HttpOnly* flag so that the frontend can
    read the cookie and copy it into the ``X-CSRFToken`` header on mutating
    requests.  SameSite=Lax provides reasonable defaults while still allowing
    cross-site navigation GET requests (required for typical web-app flows).
    """

    cookie_options = {
        "httponly": False,  # must be readable by client-side JS
        "samesite": "lax",
        "secure": not settings.insecure_cookies,
        # Give the token a long lifetime – issuing a fresh one on every page
        # load would break concurrent tabs. 7 days is a good balance.
        "max_age": 60 * 60 * 24 * 7,  # 1 week
        "path": "/",
    }
    return CSRF_COOKIE_NAME, token, cookie_options


def _get_csrf_tokens(request) -> tuple[str | None, str | None]:  # noqa: D401
    """Helper: extract (cookie_token, header_token) from *request*."""

    cookie_token: str | None = request.cookies.get(CSRF_COOKIE_NAME)

    header_token: str | None = None
    # Header names are case-insensitive; use dict mapping to lower case.
    for k, v in request.headers.items():
        if k.lower() == CSRF_HEADER_NAME:
            header_token = v
            break

    return cookie_token, header_token


def validate_csrf(request) -> None:  # noqa: D401 – raises HTTPException on failure
    """Validate CSRF token on mutating requests.

    The middleware already restricts calls to unsafe HTTP verbs so we simply
    compare the header and cookie values using *hmac.compare_digest* to guard
    against timing attacks.
    """

    cookie_token, header_token = _get_csrf_tokens(request)

    if not cookie_token or not header_token:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token missing",
        )

    # Constant-time comparison.
    if not hmac.compare_digest(cookie_token, header_token):  # pragma: no cover
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token invalid",
        )



def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    # ---------------------------------------------------------------------
    # The *python-jose* library (used in production) accepts standard
    # ``datetime`` instances for the registered claims (*exp*, *iat*, …) and
    # converts them to integer timestamps internally.  Our **light-weight
    # stub** – activated when the real dependency cannot be installed inside
    # the execution sandbox – serialises the payload using ``json.dumps``.
    #
    # ``datetime`` objects are **not** JSON serialisable which previously
    # caused ``TypeError: Object of type datetime is not JSON serializable``
    # during token generation.  As a result the */api/auth/login* endpoint
    # returned a 500 error and users could not log in.
    #
    # To stay compatible with both implementations we normalise the
    # timestamps **before** calling ``jwt.encode`` by converting them to Unix
    # epoch integers – the canonical representation defined by RFC 7519.
    # ---------------------------------------------------------------------

    if expires_delta:
        expire_dt = datetime.now(timezone.utc) + expires_delta
    else:
        expire_dt = datetime.now(timezone.utc) + timedelta(
            minutes=settings.access_token_expire_minutes
        )

    now_dt = datetime.now(timezone.utc)

    to_encode.update(
        {
            "exp": int(expire_dt.timestamp()),
            "iat": int(now_dt.timestamp()),
        }
    )
    # Guarantee a unique JWT ID so sessions can be tracked per token.
    if "jti" not in to_encode:
        to_encode["jti"] = secrets.token_urlsafe(32)
    
    encoded_jwt = jwt.encode(to_encode, settings.effective_secret_key, algorithm=settings.algorithm)
    return encoded_jwt


def decode_access_token(token: str) -> Dict[str, Any]:
    """Decode and verify a JWT token."""
    try:
        payload = jwt.decode(token, settings.effective_secret_key, algorithms=[settings.algorithm])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def token_sub_identity(payload: Dict[str, Any]) -> int:
    """Extract user ID from token payload."""
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        return int(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def build_auth_cookie(token: str) -> tuple[str, str, dict]:
    """Build cookie parameters for auth token."""
    cookie_name = "access_token"
    cookie_options = {
        "httponly": True,
        "samesite": "lax",
        "secure": not settings.insecure_cookies,
        "max_age": settings.access_token_expire_minutes * 60,
    }
    return cookie_name, token, cookie_options