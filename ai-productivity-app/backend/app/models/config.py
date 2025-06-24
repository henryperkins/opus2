"""Configuration models for storing runtime application settings."""

from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, Text, JSON
from sqlalchemy.sql import func
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
    
    # Configuration value stored as JSON to support various data types
    value = Column(JSON, nullable=True)
    
    # Value type for validation (string, number, boolean, object)
    value_type = Column(String(20), nullable=False, default="string")
    
    # Human-readable description
    description = Column(Text, nullable=True)
    
    # Whether this config requires application restart to take effect
    requires_restart = Column(Boolean, default=False)
    
    # When this configuration was last updated
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Who/what updated this configuration (for audit trail)
    updated_by = Column(String(100), nullable=True)

    def __repr__(self):
        return f"<RuntimeConfig(key='{self.key}', value={self.value})>"


class ConfigHistory(Base):
    """Track configuration changes for audit and rollback purposes."""
    
    __tablename__ = "config_history"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Configuration key that was changed
    config_key = Column(String(100), nullable=False, index=True)
    
    # Previous value (before change)
    old_value = Column(JSON, nullable=True)
    
    # New value (after change)
    new_value = Column(JSON, nullable=True)
    
    # When the change occurred
    changed_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Who/what made the change
    changed_by = Column(String(100), nullable=True)
    
    # Optional reason for the change
    reason = Column(Text, nullable=True)

    def __repr__(self):
        return f"<ConfigHistory(key='{self.config_key}', changed_at={self.changed_at})>"