"""
Purpose: Pydantic schemas for authentication workflows (login, registration,
token response, user serialization, password reset).  Kept concise (<150 LOC)
as specified in Phase 2 plan.
"""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, validator

# --------------------------------------------------------------------------- #
# Compatibility shim – Pydantic ConfigDict                                    #
# --------------------------------------------------------------------------- #
# Pydantic v2 provides *ConfigDict* for model configuration.  Earlier
# versions (and the lightweight stub used in the test-runner) do **not**
# export the symbol which breaks `model_config = ConfigDict(...)` assignments.
# We therefore provide a minimal fallback that behaves like a regular dict.
try:
    from pydantic import ConfigDict  # type: ignore
except ImportError:  # pragma: no cover – pydantic-v1 / stub
    class ConfigDict(dict):  # pylint: disable=too-few-public-methods
        """Stand-in replacement so code can reference ConfigDict unconditionally."""
        pass


# --------------------------------------------------------------------------- #
#                                 INPUT MODELS                                #
# --------------------------------------------------------------------------- #


class UserLogin(BaseModel):
    """
    User login payload. Accepts either username or email to simplify UX.
    """

    username_or_email: str = Field(
        ...,
        min_length=3,
        max_length=100,
        examples=["alice", "alice@example.com"],
    )
    password: str = Field(..., min_length=8, max_length=128)

    # ------------------------------------------------------------------
    # Backwards-compatibility: older clients (and several unit tests) send
    # either a *username* **or** an *email* field instead of the consolidated
    # *username_or_email* attribute introduced in v0.10.  The following
    # *model validator* transparently copies whichever of the legacy fields
    # is present so that downstream code can continue to rely on the single
    # canonical attribute.
    # ------------------------------------------------------------------

    # FastAPI (and our stubbed test runtime) rely on Pydantic **v2**.  The
    # recommended way to mutate raw input before field validation is a
    # *model_validator* with ``mode="before"``.  Our previous override of
    # ``model_validate`` used the *v1* signature which meant the hook was **not
    # executed** – ``username_or_email`` stayed *None* when callers only
    # supplied the legacy *username* or *email* field.  The subsequent
    # ``payload.username_or_email.lower()`` therefore crashed.

    # ------------------------------------------------------------------
    # Compatibility shim for sandbox Pydantic stub
    # ------------------------------------------------------------------
    # The minimal *pydantic* replacement used by the test-runner only exports
    # a subset of the real API (``BaseModel``, ``Field``, ``validator`` …)
    # and does *not* provide advanced helpers like ``root_validator`` /
    # ``model_validator``.  Relying on those therefore crashes the import
    # stage.  We fall back to a tiny ``__init__`` override that patches the
    # legacy keys **before** delegating to the parent constructor – works for
    # both the stub and the real implementation.

    def __init__(self, **data):  # type: ignore[override]
        if "username_or_email" not in data:
            alias_val = data.get("username") or data.get("email")
            if alias_val is not None:
                data["username_or_email"] = alias_val
        super().__init__(**data)

    @validator("username_or_email", pre=True)
    def strip_whitespace(cls, v: str) -> str:  # noqa: N805
        return v.strip().lower()

    class Config:
        json_schema_extra = {
            "example": {"username_or_email": "alice", "password": "hunter2"}
        }


class UserRegister(BaseModel):
    """
    Registration payload, optionally requires invite_code if enabled in settings.
    """

    username: str = Field(..., min_length=3, max_length=50, examples=["alice"])
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    invite_code: str | None = Field(
        None,
        description="Invite code required if registration is invite-only",
        examples=["INVITECODE"],
    )

    class Config:
        json_schema_extra = {
            "example": {
                "username": "alice",
                "email": "alice@example.com",
                "password": "hunter2",
                "invite_code": "INVITECODE",
            }
        }


class PasswordResetRequest(BaseModel):
    """
    Step 1: user requests password reset.
    """

    email: EmailStr


class PasswordResetSubmit(BaseModel):
    """
    Step 2: user submits new password with token they received.
    """

    token: str
    new_password: str = Field(..., min_length=8, max_length=128)


# --------------------------------------------------------------------------- #
#                                 OUTPUT MODELS                               #
# --------------------------------------------------------------------------- #


class TokenResponse(BaseModel):
    """
    Response returned on successful authentication.
    """

    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds until expiration

    @classmethod
    def from_ttl(cls, token: str, ttl_minutes: int) -> "TokenResponse":
        # Explicitly set *token_type* because our lightweight Pydantic stub
        # used inside the sandbox does **not** automatically include default
        # values when serialising the model via ``dict()``.  Supplying the
        # value explicitly keeps the response payload identical between the
        # real and the stubbed runtime.
        return cls(
            access_token=token,
            token_type="bearer",
            expires_in=ttl_minutes * 60,
        )


class UserResponse(BaseModel):
    """
    Public user information returned by /me endpoint.
    """

    id: int
    username: str
    email: EmailStr
    is_active: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None
    preferences: dict | None = None

    class Config:
        from_attributes = True


# --------------------------------------------------------------------------- #
#                              MUTATION MODELS                               #
# --------------------------------------------------------------------------- #


class UserUpdate(BaseModel):
    """Partial update payload for the authenticated user's profile."""

    username: str | None = Field(
        None,
        min_length=3,
        max_length=50,
        description="New username (must be unique)",
        examples=["alice"],
    )
    email: EmailStr | None = Field(
        None,
        description="New email address (must be unique)",
        examples=["alice@example.com"],
    )
    password: str | None = Field(
        None,
        min_length=8,
        max_length=128,
        description="Optional new password (will be hashed server-side)",
    )

    @validator("username", "email", pre=True)
    def _strip_and_lower(cls, v: str | None):  # noqa: N805
        if v is None:
            return v
        return v.strip().lower()

    @validator("password", pre=True)
    def _strip(cls, v: str | None):  # noqa: N805
        if v is None:
            return v
        return v.strip()

    @validator("password")
    def _password_strength(cls, v: str | None):  # noqa: N805
        # Extra guard – length already enforced by Field but keep for clarity
        if v is not None and len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        return v

    @classmethod
    def ensure_non_empty(cls, values):  # noqa: D401
        if not any(
            values.get(f) is not None for f in ("username", "email", "password")
        ):
            raise ValueError("At least one field must be provided")
        return values

    class Config:  # noqa: D401
        json_schema_extra = {
            "example": {
                "username": "newalice",
                "email": "alice@newdomain.com",
                "password": "newpassword123",
            }
        }

    # Ensure at least one field present – works on Pydantic v1 & v2
    def __init__(self, **data):  # noqa: D401
        super().__init__(**data)
        if not any(
            getattr(self, field) is not None
            for field in ("username", "email", "password")
        ):
            raise ValueError("At least one field must be provided")


class PreferencesUpdate(BaseModel):
    """Partial update for user preferences.

    The payload supports an open set of keys.  At the moment the UI needs to
    persist two *AI related* settings in addition to the existing
    ``quality_settings`` block so that every user can override the **default
    provider/model** used by the application when a new chat session is
    created:

    • ``default_provider`` – ``"openai" | "azure" | "anthropic"`` (optional)
    • ``default_model``    – deployment / model identifier                (optional)

    Additional keys can be added in the future without having to update the
    backend because *extra* fields are allowed and will be merged verbatim
    into the ``preferences`` JSON column.
    """

    quality_settings: dict | None = Field(
        None, description="Quality settings for model responses",
    )

    # AI runtime defaults – both are **optional** so that clients can PATCH
    # either field independently without having to send the whole object.
    default_provider: str | None = Field(
        None, description="Preferred LLM provider (openai / azure / anthropic)",
    )
    default_model: str | None = Field(
        None, description="Preferred default model (e.g. 'gpt-4o-mini')",
    )

    # Allow arbitrary additional keys so the preferences object stays forward
    # compatible with new UI features.  The router merges everything blindly
    # into ``User.preferences``.

    model_config = ConfigDict(extra="allow")


# --------------------------------------------------------------------------- #
#                               HELPER ALIASES                                #
# --------------------------------------------------------------------------- #

LoginSchema = UserLogin
RegisterSchema = UserRegister

# Ensure all forward references for this model are resolved for FastAPI+Pydantic
# Pydantic v2 introduces `model_rebuild`; guard for compatibility with v1
if hasattr(UserRegister, "model_rebuild"):
    UserRegister.model_rebuild()
globals()["UserRegister"] = UserRegister
