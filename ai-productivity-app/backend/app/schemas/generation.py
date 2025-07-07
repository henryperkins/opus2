
# app/schemas/generation.py
"""
Unified schema definitions for AI model configuration.
Single source of truth for all generation parameters, reasoning settings, and provider options.
"""
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field, field_validator, ConfigDict
from datetime import datetime
from app.utils.naming import to_camel

class GenerationParams(BaseModel):
    """Core generation parameters supported by all providers."""
    
    temperature: Optional[float] = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Controls randomness in generation"
    )
    max_tokens: Optional[int] = Field(
        default=None,
        ge=1,
        le=128000,
        description="Maximum tokens to generate"
    )
    top_p: Optional[float] = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Nucleus sampling parameter"
    )
    frequency_penalty: Optional[float] = Field(
        default=0.0,
        ge=-2.0,
        le=2.0,
        description="Penalty for token frequency"
    )
    presence_penalty: Optional[float] = Field(
        default=0.0,
        ge=-2.0,
        le=2.0,
        description="Penalty for token presence"
    )
    stop_sequences: Optional[List[str]] = Field(
        default=None,
        description="Sequences where generation stops"
    )
    seed: Optional[int] = Field(
        default=None,
        description="Random seed for reproducibility"
    )
    
    model_config = ConfigDict(protected_namespaces=())


class ReasoningParams(BaseModel):
    """Reasoning and thinking parameters for advanced models."""
    
    # General reasoning settings
    enable_reasoning: bool = Field(
        default=False,
        description="Enable reasoning for supported models"
    )
    reasoning_effort: Literal["low", "medium", "high"] = Field(
        default="medium",
        description="Reasoning effort level (Azure/OpenAI)"
    )
    
    # Claude-specific thinking settings
    claude_extended_thinking: Optional[bool] = Field(
        default=True,
        description="Enable Claude's extended thinking"
    )
    claude_thinking_mode: Optional[Literal["off", "enabled", "aggressive"]] = Field(
        default="enabled",
        description="Claude thinking mode"
    )
    claude_thinking_budget_tokens: Optional[int] = Field(
        default=16384,
        ge=1024,
        le=65536,
        description="Token budget for Claude thinking"
    )
    claude_show_thinking_process: Optional[bool] = Field(
        default=True,
        description="Show Claude's thinking process"
    )
    claude_adaptive_thinking_budget: Optional[bool] = Field(
        default=True,
        description="Auto-adjust thinking budget based on complexity"
    )
    
    # Thinking mode selection
    default_thinking_mode: Optional[str] = Field(
        default="chain_of_thought",
        description="Default thinking approach"
    )
    default_thinking_depth: Optional[Literal["surface", "detailed", "comprehensive", "exhaustive"]] = Field(
        default="detailed",
        description="Default thinking depth"
    )
    
    model_config = ConfigDict(protected_namespaces=())


class ProviderConfig(BaseModel):
    """Provider-specific configuration."""
    
    provider: Literal["openai", "azure", "anthropic"] = Field(
        ...,
        description="AI provider"
    )
    api_key: Optional[str] = Field(
        default=None,
        description="API key (stored encrypted)"
    )
    endpoint: Optional[str] = Field(
        default=None,
        description="API endpoint URL"
    )
    api_version: Optional[str] = Field(
        default=None,
        description="API version (Azure)"
    )
    organization_id: Optional[str] = Field(
        default=None,
        description="Organization ID (OpenAI)"
    )
    use_responses_api: Optional[bool] = Field(
        default=False,
        description="Use Azure Responses API"
    )
    
    model_config = ConfigDict(protected_namespaces=())


class ModelCapabilities(BaseModel):
    """Model capabilities and limits."""
    
    supports_functions: bool = True
    supports_vision: bool = False
    supports_reasoning: bool = False
    supports_streaming: bool = True
    supports_json_mode: bool = True
    max_context_window: int = 4096
    max_output_tokens: int = 4096
    supports_parallel_tools: bool = True
    
    model_config = ConfigDict(protected_namespaces=())


class ModelInfo(BaseModel):
    """Complete model information."""
    
    model_id: str = Field(..., description="Unique model identifier")
    display_name: str = Field(..., description="User-friendly name")
    provider: Literal["openai", "azure", "anthropic"] = Field(..., description="Provider")
    model_family: Optional[str] = Field(None, description="Model family (gpt-4, claude-3, etc)")
    
    # Capabilities
    capabilities: ModelCapabilities = Field(
        default_factory=ModelCapabilities,
        description="Model capabilities"
    )
    
    # Cost information
    cost_per_1k_input_tokens: Optional[float] = Field(None, ge=0)
    cost_per_1k_output_tokens: Optional[float] = Field(None, ge=0)
    
    # Performance characteristics
    performance_tier: Optional[Literal["fast", "balanced", "powerful"]] = Field(
        default="balanced",
        description="Performance tier"
    )
    average_latency_ms: Optional[int] = Field(None, description="Average response time")
    
    # Metadata
    is_available: bool = True
    is_deprecated: bool = False
    deprecation_date: Optional[datetime] = None
    recommended_use_cases: List[str] = Field(default_factory=list)
    
    model_config = ConfigDict(protected_namespaces=())


class UnifiedModelConfig(GenerationParams, ReasoningParams):
    """Complete model configuration combining all parameters."""
    
    # Model selection
    provider: Literal["openai", "azure", "anthropic"] = Field(
        ...,
        description="AI provider"
    )
    model_id: str = Field(
        ...,
        description="Model identifier"
    )
    
    # Optional overrides
    system_prompt: Optional[str] = Field(
        default=None,
        description="System prompt override"
    )
    response_format: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Response format (e.g., JSON mode)"
    )
    
    # Provider-specific settings
    use_responses_api: bool = Field(
        default=False,
        description="Use Azure Responses API"
    )
    
    # Metadata
    config_name: Optional[str] = Field(
        default=None,
        description="Configuration preset name"
    )
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    @field_validator("model_id")
    @classmethod
    def validate_model_id(cls, v, info):
        """Validate model_id based on provider."""
        provider = info.data.get("provider")
        
        # Basic validation - could be extended with actual model lists
        if provider == "azure" and not v:
            raise ValueError("Model ID required for Azure provider")
        
        return v
    
    def to_runtime_config(self) -> Dict[str, Any]:
        """Convert to runtime configuration format."""
        config = self.model_dump(exclude_unset=True, exclude_none=True)
        
        # Flatten for storage
        flat_config = {
            "provider": config.pop("provider"),
            "chat_model": config.pop("model_id"),
            **config
        }
        
        return flat_config
    
    @classmethod
    def from_runtime_config(cls, config: Dict[str, Any]) -> "UnifiedModelConfig":
        """Create from runtime configuration."""
        # Map flat structure back to nested
        model_config = {
            "provider": config.get("provider", "openai"),
            "model_id": config.get("chat_model", "gpt-4o-mini"),
            **{k: v for k, v in config.items() if k not in ["provider", "chat_model"]}
        }
        
        return cls(**model_config)
    
    model_config = ConfigDict(protected_namespaces=())


# Request/Response schemas for API
class ConfigUpdateRequest(BaseModel):
    """Request schema for configuration updates."""
    
    config: Optional[UnifiedModelConfig] = None
    provider_config: Optional[ProviderConfig] = None
    update_type: Literal["full", "partial"] = "partial"
    
    model_config = ConfigDict(protected_namespaces=())


class ConfigResponse(BaseModel):
    """Response schema for configuration endpoints."""
    
    current: UnifiedModelConfig
    available_models: List[ModelInfo]
    providers: Dict[str, Dict[str, Any]]
    last_updated: datetime
    
    model_config = ConfigDict(protected_namespaces=())

class GenerationParamsResponse(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
        json_schema_extra={
            "example": {
                "temperature": 0.7,
                "maxTokens": 1000,
                "topP": 0.9
            }
        }
    )
    
    temperature: float
    max_tokens: int
    top_p: float
    # ... other fields

# Validation helpers
def validate_config_consistency(config: UnifiedModelConfig) -> tuple[bool, Optional[str]]:
    """Validate configuration consistency across parameters."""
    
    # Reasoning models don't support temperature
    reasoning_models = ["o1", "o1-mini", "o3", "o3-mini", "o4-mini"]
    if any(model in config.model_id for model in reasoning_models):
        if config.temperature is not None and config.temperature != 1.0:
            return False, f"Reasoning model {config.model_id} does not support temperature control"
    
    # Claude models require specific thinking parameters
    if config.provider == "anthropic":
        if config.enable_reasoning and not config.claude_extended_thinking:
            return False, "Claude models use extended thinking, not standard reasoning"
    
    # Azure Responses API requirements
    if config.use_responses_api and config.provider != "azure":
        return False, "Responses API is only available for Azure provider"
    
    return True, None


# Export all schemas
__all__ = [
    "GenerationParams",
    "ReasoningParams", 
    "ProviderConfig",
    "ModelCapabilities",
    "ModelInfo",
    "UnifiedModelConfig",
    "ConfigUpdateRequest",
    "ConfigResponse",
    "GenerationParamsResponse",
    "validate_config_consistency"
]
