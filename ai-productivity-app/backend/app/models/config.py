"""Configuration models for storing runtime application settings."""
# pylint: disable=not-callable

from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, Text, Index, CheckConstraint
from sqlalchemy.dialects.postgresql import JSONB, ENUM
from sqlalchemy.sql import func, text
from .base import Base


class RuntimeConfig(Base):
    """Store runtime configuration settings that can be modified via API.

    This table stores the dynamic configuration that users can modify through
    the frontend, such as model selection, temperature, and other parameters.
    This replaces the in-memory _RUNTIME_CONFIG dict for persistence across
    application restarts.
    """

    __tablename__ = "runtime_config"

    # Configuration key (e.g., "chat_model", "provider", "temperature")
    key = Column(String(100), primary_key=True, index=True)

    # Configuration value stored as JSONB for better performance in PostgreSQL
    value = Column(JSONB, nullable=True)

    # Value type for validation (string, number, boolean, object, array)
    value_type = Column(String(20), nullable=False, default="string")

    # Human-readable description
    description = Column(Text, nullable=True)

    # Whether this config requires application restart to take effect
    requires_restart = Column(Boolean, default=False)

    # When this configuration was last updated
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Who/what updated this configuration (for audit trail)
    updated_by = Column(String(100), nullable=True)

    # PostgreSQL-specific table configuration
    __table_args__ = (
        # GIN index for JSONB value queries
        Index('idx_runtime_config_value_gin', 'value', postgresql_using='gin'),

        # Partial index for specific config types
        Index('idx_runtime_config_model_configs', 'key', 'value',
              postgresql_where=text("key LIKE '%model%' OR key LIKE '%provider%'")),

        # Check constraints for data validation
        CheckConstraint(
            "value_type IN ('string', 'number', 'boolean', 'object', 'array')",
            name='valid_value_type'
        ),

        # Ensure model configuration keys follow naming convention
        CheckConstraint(
            "key ~ '^[a-z][a-z0-9_]*$'",
            name='valid_config_key_format'
        ),

        {"extend_existing": True},
    )

    def __repr__(self):
        return f"<RuntimeConfig(key='{self.key}', value={self.value})>"


class ConfigHistory(Base):
    """Track configuration changes for audit and rollback purposes."""

    __tablename__ = "config_history"

    id = Column(Integer, primary_key=True, index=True)

    # Configuration key that was changed
    config_key = Column(String(100), nullable=False, index=True)

    # Previous value (before change)
    old_value = Column(JSONB, nullable=True)

    # New value (after change)
    new_value = Column(JSONB, nullable=True)

    # When the change occurred
    changed_at = Column(DateTime(timezone=True), server_default=func.now())

    # Who/what made the change
    changed_by = Column(String(100), nullable=True)

    # Optional reason for the change
    reason = Column(Text, nullable=True)

    # PostgreSQL-specific optimizations
    __table_args__ = (
        # Composite index for config history queries
        Index('idx_config_history_key_time', 'config_key', 'changed_at'),

        # GIN indexes for JSONB value searches
        Index('idx_config_history_old_value_gin', 'old_value', postgresql_using='gin'),
        Index('idx_config_history_new_value_gin', 'new_value', postgresql_using='gin'),

        # Simple index for recent changes lookup
        Index('idx_config_history_key_date', 'config_key', 'changed_at'),

        {"extend_existing": True},
    )

    def __repr__(self):
        return f"<ConfigHistory(key='{self.config_key}', changed_at={self.changed_at})>"


# PostgreSQL Enum for model providers
model_provider_enum = ENUM(
    'openai', 'azure', 'anthropic', 'local', 'ollama',
    name='model_provider_enum',
    create_type=True
)

# PostgreSQL Enum for model capabilities
model_capability_enum = ENUM(
    'chat', 'completion', 'embedding', 'vision', 'function_calling',
    'code_generation', 'reasoning', 'multimodal',
    name='model_capability_enum',
    create_type=True
)


class ModelConfiguration(Base):
    """Enhanced model configuration storage with PostgreSQL optimization.

    This model stores detailed language model configurations, capabilities,
    and performance metrics optimized for PostgreSQL's advanced features.
    """

    __tablename__ = "model_configurations"

    # Unique model identifier
    model_id = Column(String(100), primary_key=True, index=True)

    # Display name for the model
    name = Column(String(200), nullable=False)

    # Provider using PostgreSQL enum
    provider = Column(model_provider_enum, nullable=False)

    # Model family/base (e.g., gpt-4, claude-3, llama-2)
    model_family = Column(String(50), nullable=False, index=True)

    # Specific version (e.g., gpt-4-turbo-preview, claude-3-opus-20240229)
    version = Column(String(100), nullable=True)

    # Model capabilities as JSON object
    capabilities = Column(JSONB, nullable=False, default=dict, comment="Model capabilities as key-value pairs")

    # Configuration parameters as JSONB
    default_params = Column(JSONB, nullable=False, default=dict, comment="Default parameters for the model")

    # Model limits and specifications
    max_tokens = Column(Integer, nullable=False, default=4096)
    context_window = Column(Integer, nullable=False, default=8192)

    # Cost information (per 1K tokens)
    cost_input_per_1k = Column(Float, nullable=True, comment="Cost per 1K input tokens")
    cost_output_per_1k = Column(Float, nullable=True, comment="Cost per 1K output tokens")

    # ------------------------------------------------------------------
    # Compatibility shim for legacy **tier** column
    # ------------------------------------------------------------------
    # Some historical database migrations added a *tier* column to the
    # ``model_configurations`` table while more recent revisions removed it
    # (the information is now part of the JSON metadata).  To remain
    # compatible with either state we expose a *computed* column property that
    # always yields the string "balanced".  SQLAlchemy will embed the literal
    # directly in SELECT statements, therefore it never references a physical
    # column and cannot trigger *UndefinedColumn* errors.
    # ------------------------------------------------------------------

    from sqlalchemy import literal  # local import to avoid polluting module
    from sqlalchemy.orm import column_property

    tier = column_property(literal("balanced"))  # type: ignore  # noqa: A001

    # Performance characteristics
    avg_response_time_ms = Column(Integer, nullable=True, comment="Average response time in milliseconds")
    throughput_tokens_per_sec = Column(Float, nullable=True, comment="Average tokens per second")

    # Availability and status
    is_available = Column(Boolean, default=True, nullable=False)
    is_deprecated = Column(Boolean, default=False, nullable=False)

    # Model metadata as JSONB
    model_metadata = Column(JSONB, nullable=False, default=dict, comment="Additional model metadata and specifications")

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deprecated_at = Column(DateTime(timezone=True), nullable=True)

    # PostgreSQL-specific optimizations
    __table_args__ = (
        # GIN index for capabilities array
        Index('idx_model_config_capabilities_gin', 'capabilities', postgresql_using='gin'),

        # GIN index for default parameters
        Index('idx_model_config_params_gin', 'default_params', postgresql_using='gin'),

        # GIN index for metadata
        Index('idx_model_config_metadata_gin', 'model_metadata', postgresql_using='gin'),

        # Composite index for provider and family
        Index('idx_model_config_provider_family', 'provider', 'model_family'),

        # Partial index for available models only
        Index('idx_model_config_available', 'provider', 'model_family', 'is_available',
              postgresql_where=text("is_available = true AND is_deprecated = false")),

        # Simple index for cost columns
        Index('idx_model_config_cost_efficiency', 'cost_input_per_1k', 'cost_output_per_1k', 'throughput_tokens_per_sec'),

        # Check constraints
        CheckConstraint('max_tokens > 0', name='positive_max_tokens'),
        CheckConstraint('context_window > 0', name='positive_context_window'),
        CheckConstraint('cost_input_per_1k >= 0', name='non_negative_input_cost'),
        CheckConstraint('cost_output_per_1k >= 0', name='non_negative_output_cost'),
        CheckConstraint('avg_response_time_ms > 0', name='positive_response_time'),
        CheckConstraint('throughput_tokens_per_sec > 0', name='positive_throughput'),

        {"extend_existing": True},
    )

    def merged_params(self, overrides: dict | None = None) -> dict:
        """Merge default parameters with optional overrides.

        Args:
            overrides: Optional dictionary of parameters to override defaults

        Returns:
            Merged parameter dictionary with overrides taking precedence
        """
        merged = (self.default_params or {}).copy()
        if overrides:
            merged.update(overrides)
        return merged

    def __repr__(self):
        return f"<ModelConfiguration(model_id='{self.model_id}', provider='{self.provider}')>"


class ModelUsageMetrics(Base):
    """Track model usage and performance metrics."""

    __tablename__ = "model_usage_metrics"

    id = Column(Integer, primary_key=True, index=True)

    # Reference to model configuration
    model_id = Column(String(100), nullable=False, index=True)

    # Usage statistics
    total_requests = Column(Integer, default=0, nullable=False)
    total_tokens_input = Column(Integer, default=0, nullable=False)
    total_tokens_output = Column(Integer, default=0, nullable=False)

    # Performance metrics
    avg_response_time_ms = Column(Float, nullable=True)
    success_rate = Column(Float, nullable=True, comment="Success rate as percentage")

    # Cost tracking
    total_cost = Column(Float, default=0.0, nullable=False)

    # User satisfaction (if available)
    avg_user_rating = Column(Float, nullable=True, comment="Average user rating 1-5")

    # Time period for these metrics
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)

    # Detailed metrics as JSONB
    detailed_metrics = Column(JSONB, nullable=False, default=dict, comment="Detailed performance and usage metrics")

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # PostgreSQL-specific optimizations
    __table_args__ = (
        # Composite index for model and time period
        Index('idx_model_usage_model_period', 'model_id', 'period_start', 'period_end'),

        # GIN index for detailed metrics
        Index('idx_model_usage_metrics_gin', 'detailed_metrics', postgresql_using='gin'),

        # Simple index for recent metrics lookup
        Index('idx_model_usage_recent', 'model_id', 'period_end'),

        # Simple index for efficiency metrics
        Index('idx_model_usage_efficiency', 'total_cost', 'total_requests'),

        # Check constraints
        CheckConstraint('total_requests >= 0', name='non_negative_requests'),
        CheckConstraint('total_tokens_input >= 0', name='non_negative_input_tokens'),
        CheckConstraint('total_tokens_output >= 0', name='non_negative_output_tokens'),
        CheckConstraint('success_rate >= 0 AND success_rate <= 100', name='valid_success_rate'),
        CheckConstraint('avg_user_rating >= 1 AND avg_user_rating <= 5', name='valid_user_rating'),
        CheckConstraint('period_start < period_end', name='valid_time_period'),
        CheckConstraint('total_cost >= 0', name='non_negative_cost'),

        {"extend_existing": True},
    )

    def __repr__(self):
        return f"<ModelUsageMetrics(model_id='{self.model_id}', period={self.period_start} to {self.period_end})>"
