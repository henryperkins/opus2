"""Backward compatibility shim for legacy import path.

Historically authentication-related FastAPI dependencies lived under
``app.auth.dependencies``.  They have since been *promoted* to the project
root at :pymod:`app.dependencies`.  A lingering handful of test cases – and
possibly third-party extensions – still refer to the **old** location.

The shim re-exports the public symbols so that the canonical implementation
remains single-sourced in *app.dependencies* while legacy imports continue to
work unchanged.
"""

# ruff: noqa: F401 (re-exported symbols appear unused in this stub)

from app.dependencies import (  # type: ignore  # pragma: no cover
    CurrentUserOptional,
    CurrentUserRequired,
    AdminRequired,
    DatabaseDep,
    AsyncDatabaseDep,
    _current_user_optional as get_current_user,  # legacy name
)
