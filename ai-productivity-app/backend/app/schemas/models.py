"""Shim module for legacy `app.schemas.models` import path.

The full model-configuration schemas were consolidated into
``app.schemas.generation`` during the *Unified Configuration* refactor.  The
test-suite, however, still imports ``ModelConfig`` from the old location.  We
provide a minimal alias that re-exports the new ``UnifiedModelConfig`` so the
API surface remains intact without duplicating code.
"""

from __future__ import annotations

from typing import Any

from pydantic import field_validator

# Import the canonical schema
from app.schemas.generation import UnifiedModelConfig as _UnifiedModelConfig


class ModelConfig(_UnifiedModelConfig):
    """Backward-compatibility alias around *UnifiedModelConfig*.

    It inherits from the new schema unchanged so that existing validation logic
    continues to work, while satisfying the import expectations of historical
    code.
    """

    @field_validator("provider")
    def _validate_provider(cls, v: str) -> str:  # noqa: D401,N805
        # Legacy tests sometimes expect a lowercase provider string
        return v.lower()


__all__: list[str] = ["ModelConfig"]
