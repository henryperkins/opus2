"""Light-weight compatibility wrapper.

Older test-suites import :pymod:`app.utils.security` for helpers such as
``get_password_hash``.  The actual implementation was migrated to
``app.auth.security`` a while ago.  To avoid touching every historical test
file we provide a minimal pass-through module that re-exports the current
symbols.
"""

# ruff: noqa: F401

from app.auth.security import (  # type: ignore  # pragma: no cover
    create_access_token,
    get_password_hash,
    verify_password,
)
