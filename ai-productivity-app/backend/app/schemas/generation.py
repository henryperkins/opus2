"""
app/schemas/generation.py
=========================

Pydantic models shared by the AI-configuration API, service layer and
frontend.

The module uses *camelCase* aliases in every public schema so the JSON
payloads match the naming style used in the React code-base.

Key points
----------
•  CamelModel  – base class with automatic snake→camel alias generator
•  GenerationParams / ReasoningParams  – main parameter groups
•  UnifiedModelConfig  – combines selection + generation + reasoning
•  ConfigUpdate        – strict PATCH contract (extra = forbid)
•  ModelInfo           – full catalogue entry incl. capabilities / cost
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    conint,
    confloat,
    field_validator,
)

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
def _to_camel(s: str) -> str:
    """snake_case → camelCase (simple, two-pass)."""
    parts = s.split("_")
    return parts[0] + "".join(p.title() for p in parts[1:])


class CamelModel(BaseModel):
    """Base model that exports camelCase keys by default."""
    model_config = ConfigDict(
        alias_generator=_to_camel,
        populate_by_name=True,
        protected_namespaces=(),
        extra="forbid",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Capabilities & catalogue
# ─────────────────────────────────────────────────────────────────────────────
class ModelCapabilities(CamelModel):
    supports_functions: bool = True
    supports_streaming: bool = True
    supports_vision: bool = False
    supports_responses_api: bool = False
    supports_reasoning: bool = False
    supports_thinking: bool = False
    supports_json_mode: bool = False
    max_context_window: int = 4096
    max_output_tokens: int = 4096
    supports_parallel_tools: bool = True


class ModelInfo(CamelModel):
    model_id: str = Field(..., description="Unique identifier used in API calls")
    display_name: str = Field(..., description="Human readable name")
    provider: Literal["openai", "azure", "anthropic"]
    model_family: Optional[str] = None
    capabilities: ModelCapabilities = Field(
        default_factory=ModelCapabilities, description="Capability flags & limits"
    )
    # Cost
    cost_per_1k_input_tokens: Optional[float] = Field(None, ge=0)
    cost_per_1k_output_tokens: Optional[float] = Field(None, ge=0)
    # Performance
    performance_tier: Optional[Literal["fast", "balanced", "powerful"]] = "balanced"
    average_latency_ms: Optional[int] = None
    # Life-cycle
    is_available: bool = True
    is_deprecated: bool = False
    deprecation_date: Optional[datetime] = None
    recommended_use_cases: List[str] = Field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# Parameter groups
# ─────────────────────────────────────────────────────────────────────────────
class GenerationParams(CamelModel):
    temperature: confloat(ge=0.0, le=2.0) = 1.0  # type: ignore[arg-type]
    max_tokens: conint(ge=64, le=16000) | None = 1024  # type: ignore[arg-type]
    top_p: confloat(ge=0.0, le=1.0) = 1.0  # type: ignore[arg-type]
    frequency_penalty: confloat(ge=-2.0, le=2.0) = 0.0  # type: ignore[arg-type]
    presence_penalty: confloat(ge=-2.0, le=2.0) = 0.0  # type: ignore[arg-type]
    # Streaming toggle (client side)
    stream: bool = False


class ReasoningParams(CamelModel):
    enable_reasoning: bool = False
    reasoning_effort: Literal["low", "medium", "high"] | None = "medium"

    # Claude
    claude_extended_thinking: Optional[bool] = True
    claude_thinking_mode: Optional[Literal["off", "enabled", "aggressive"]] = "enabled"
    claude_thinking_budget_tokens: Optional[int] = Field(16384, ge=1024, le=65536)
    claude_show_thinking_process: Optional[bool] = True
    claude_adaptive_thinking_budget: Optional[bool] = True

    default_thinking_mode: Optional[str] = "chain_of_thought"
    default_thinking_depth: Optional[
        Literal["surface", "detailed", "comprehensive", "exhaustive"]
    ] = "detailed"


# ─────────────────────────────────────────────────────────────────────────────
# Provider configuration (stored separately, but kept for completeness)
# ─────────────────────────────────────────────────────────────────────────────
class ProviderConfig(CamelModel):
    provider: Literal["openai", "azure", "anthropic"]
    api_key: Optional[str] = Field(default=None, description="Encrypted")
    endpoint: Optional[str] = None
    api_version: Optional[str] = None
    organization_id: Optional[str] = None
    use_responses_api: Optional[bool] = False


# ─────────────────────────────────────────────────────────────────────────────
# Unified model configuration
# ─────────────────────────────────────────────────────────────────────────────
class UnifiedModelConfig(GenerationParams, ReasoningParams):
    provider: Literal["openai", "azure", "anthropic"]
    model_id: str = Field(..., alias="modelId")

    # Optional overrides
    use_responses_api: bool = False
    system_prompt: Optional[str] = None
    # Accept either a structured dict **or** the legacy plain string
    # ("text", "markdown", "json") used by the current frontend.
    response_format: Optional[Union[str, Dict[str, Any]]] = None

    # Meta
    version: int = Field(0, description="Auto-incremented on every update")
    config_name: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # ------- validators -------------------------------------------------
    @field_validator("model_id", mode="before")
    @classmethod
    def _alias_accepts_legacy(cls, v, info):
        if v:
            return v
        # accept chat_model / modelId in payloads coming from old code
        return (info.data or {}).get("chat_model") or (info.data or {}).get("modelId") or v

    @field_validator("model_id")
    @classmethod
    def _basic_check(cls, v, info):
        provider = info.data.get("provider")
        if provider == "azure" and not v:
            raise ValueError("Azure provider requires an explicit model_id")
        return v

    # ------- conversions -----------------------------------------------
    def to_runtime_config(self) -> Dict[str, Any]:
        # Use snake_case for database storage by NOT using by_alias
        data = self.model_dump(exclude_none=True, by_alias=False)
        return data

    @classmethod
    def from_runtime_config(cls, cfg: Dict[str, Any]) -> "UnifiedModelConfig":
        mapped = cfg.copy()
        mapped["modelId"] = mapped.pop("model_id", mapped.pop("chat_model", None))
        return cls(**mapped)


# ─────────────────────────────────────────────────────────────────────────────
# API request / response wrappers
# ─────────────────────────────────────────────────────────────────────────────
class ConfigResponse(CamelModel):
    current: UnifiedModelConfig
    available_models: List[ModelInfo]
    providers: Dict[str, Dict[str, Any]]
    last_updated: datetime


# NOTE:
# Pydantic v2 treats any unannotated class-level attribute as a potential
# model field and therefore raises `PydanticUserError` if a plain attribute is
# added without a type annotation.  The `json_schema_extra` helper attribute
# is *not* meant to be a field – it should be passed to the model configuration
# instead.  Defining it directly on the class (as was common in Pydantic v1)
# breaks under v2.  We fix this by moving the value into `model_config`, the
# recommended way of customising schema generation in Pydantic v2.


class GenerationParamsResponse(CamelModel):
    temperature: float
    max_tokens: int
    top_p: float

    # Extra OpenAPI / JSON-schema metadata ------------------------------
    model_config = ConfigDict(
        json_schema_extra={
            "example": {"temperature": 0.7, "maxTokens": 1000, "topP": 0.9}
        },
        alias_generator=_to_camel,
        populate_by_name=True,
        protected_namespaces=(),
        extra="forbid",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Strict PATCH contract
# ─────────────────────────────────────────────────────────────────────────────
class ConfigUpdate(BaseModel):
    """
    Body schema for PATCH / PUT endpoints – every field optional,
    additional keys rejected (`extra="forbid"` defaults to BaseModel).
    """

    provider: Optional[str] = Field(None)
    model_id: Optional[str] = Field(None, alias="modelId")
    temperature: Optional[confloat(ge=0.0, le=2.0)] = None  # type: ignore[arg-type]
    max_tokens: Optional[conint(ge=64, le=16000)] = None  # type: ignore[arg-type]
    top_p: Optional[confloat(ge=0.0, le=1.0)] = None  # type: ignore[arg-type]
    frequency_penalty: Optional[confloat(ge=-2.0, le=2.0)] = None  # type: ignore[arg-type]
    presence_penalty: Optional[confloat(ge=-2.0, le=2.0)] = None  # type: ignore[arg-type]
    enable_reasoning: Optional[bool] = None
    # Accept both numeric and string representations to maintain backwards
    # compatibility with earlier frontend versions that used human-readable
    # strings ("low", "medium", "high").
    reasoning_effort: Optional[Union[int, Literal["low", "medium", "high"]]] = None
    use_responses_api: Optional[bool] = None
    stream: Optional[bool] = None

    # Claude extended thinking parameters (provider = "anthropic")
    claude_extended_thinking: Optional[bool] = None
    claude_thinking_mode: Optional[Literal["off", "enabled", "aggressive"]] = None
    claude_thinking_budget_tokens: Optional[int] = Field(
        None, ge=1024, le=65536
    )

    # Misc optional fields that can be part of a configuration patch
    system_prompt: Optional[str] = None
    # Accept either structured dict **or** the legacy plain string
    # ("text", "markdown", "json") used by the current frontend.
    response_format: Optional[Union[str, Dict[str, Any]]] = None

    model_config = ConfigDict(
        alias_generator=_to_camel,
        populate_by_name=True,
        extra="forbid",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Consistency validator used by service layer
# ─────────────────────────────────────────────────────────────────────────────
def validate_config_consistency(
    config: UnifiedModelConfig,
) -> tuple[bool, Optional[str]]:
    """
    Basic cross-field validation without hitting external services.
    Service layer adds model-specific checks afterwards.
    """
    # Claude quirk -------------------------------------------------------
    if config.provider == "anthropic" and config.enable_reasoning:
        return (
            False,
            "Claude models use extended thinking, not standard reasoning",
        )

    # Responses API only for Azure --------------------------------------
    if config.use_responses_api and config.provider != "azure":
        return False, "Responses API is only available for Azure provider"

    # All good -----------------------------------------------------------
    return True, None


# ─────────────────────────────────────────────────────────────────────────────
# Export list
# ─────────────────────────────────────────────────────────────────────────────
__all__ = [
    "CamelModel",
    "GenerationParams",
    "ReasoningParams",
    "ProviderConfig",
    "ModelCapabilities",
    "ModelInfo",
    "UnifiedModelConfig",
    "ConfigResponse",
    "GenerationParamsResponse",
    "ConfigUpdate",
    "validate_config_consistency",
]
