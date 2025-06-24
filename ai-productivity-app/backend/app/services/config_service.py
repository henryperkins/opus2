"""Service for managing persistent runtime configuration."""

from typing import Any, Dict, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import logging

from app.models.config import RuntimeConfig, ConfigHistory
from app.config import settings

logger = logging.getLogger(__name__)


class ConfigService:
    """Service for managing persistent runtime configuration."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_config(self, key: str) -> Optional[Any]:
        """Get a configuration value by key."""
        config = self.db.query(RuntimeConfig).filter_by(key=key).first()
        return config.value if config else None
    
    def get_all_config(self) -> Dict[str, Any]:
        """Get all configuration as a dictionary."""
        configs = self.db.query(RuntimeConfig).all()
        return {config.key: config.value for config in configs}
    
    def set_config(self, key: str, value: Any, description: str = None, 
                   requires_restart: bool = False, updated_by: str = None) -> RuntimeConfig:
        """Set a configuration value, creating or updating as needed."""
        
        # Get existing config if it exists
        existing = self.db.query(RuntimeConfig).filter_by(key=key).first()
        old_value = existing.value if existing else None
        
        if existing:
            # Update existing configuration
            existing.value = value
            if description is not None:
                existing.description = description
            existing.requires_restart = requires_restart
            existing.updated_by = updated_by
            config = existing
        else:
            # Create new configuration
            config = RuntimeConfig(
                key=key,
                value=value,
                value_type=self._get_value_type(value),
                description=description,
                requires_restart=requires_restart,
                updated_by=updated_by
            )
            self.db.add(config)
        
        try:
            self.db.commit()
            
            # Record configuration change in history
            self._record_history(key, old_value, value, updated_by)
            
            logger.info(f"Configuration updated: {key} = {value}")
            return config
            
        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Failed to update configuration {key}: {e}")
            raise
    
    def set_multiple_config(self, config_dict: Dict[str, Any], 
                           updated_by: str = None) -> Dict[str, RuntimeConfig]:
        """Set multiple configuration values in a single transaction."""
        results = {}
        
        try:
            for key, value in config_dict.items():
                existing = self.db.query(RuntimeConfig).filter_by(key=key).first()
                old_value = existing.value if existing else None
                
                if existing:
                    existing.value = value
                    existing.updated_by = updated_by
                    results[key] = existing
                else:
                    config = RuntimeConfig(
                        key=key,
                        value=value,
                        value_type=self._get_value_type(value),
                        updated_by=updated_by
                    )
                    self.db.add(config)
                    results[key] = config
                
                # Record in history
                self._record_history(key, old_value, value, updated_by)
            
            self.db.commit()
            logger.info(f"Multiple configurations updated: {list(config_dict.keys())}")
            return results
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to update multiple configurations: {e}")
            raise
    
    def delete_config(self, key: str, updated_by: str = None) -> bool:
        """Delete a configuration value."""
        config = self.db.query(RuntimeConfig).filter_by(key=key).first()
        if not config:
            return False
        
        old_value = config.value
        self.db.delete(config)
        
        try:
            self.db.commit()
            
            # Record deletion in history
            self._record_history(key, old_value, None, updated_by, "Configuration deleted")
            
            logger.info(f"Configuration deleted: {key}")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to delete configuration {key}: {e}")
            raise
    
    def get_config_history(self, key: str = None, limit: int = 100) -> List[ConfigHistory]:
        """Get configuration change history."""
        query = self.db.query(ConfigHistory)
        
        if key:
            query = query.filter_by(config_key=key)
        
        return query.order_by(ConfigHistory.changed_at.desc()).limit(limit).all()
    
    def initialize_default_config(self):
        """Initialize default configuration values from settings."""
        defaults = {
            "provider": settings.llm_provider,
            "chat_model": settings.llm_default_model or settings.llm_model or "gpt-3.5-turbo",
            "temperature": 0.7,
            "useResponsesApi": False,
            "maxTokens": None,
            "topP": None,
            "frequencyPenalty": None,
            "presencePenalty": None,
            "systemPrompt": None,
        }
        
        # Only set defaults for keys that don't already exist
        existing_keys = set(config.key for config in self.db.query(RuntimeConfig).all())
        
        new_configs = {}
        for key, value in defaults.items():
            if key not in existing_keys:
                new_configs[key] = value
        
        if new_configs:
            self.set_multiple_config(new_configs, updated_by="system_init")
            logger.info(f"Initialized default configurations: {list(new_configs.keys())}")
    
    def _get_value_type(self, value: Any) -> str:
        """Determine the type of a configuration value."""
        if isinstance(value, bool):
            return "boolean"
        elif isinstance(value, (int, float)):
            return "number"
        elif isinstance(value, str):
            return "string"
        elif isinstance(value, (dict, list)):
            return "object"
        else:
            return "string"  # Default fallback
    
    def _record_history(self, key: str, old_value: Any, new_value: Any, 
                       updated_by: str = None, reason: str = None):
        """Record a configuration change in the history table."""
        try:
            history = ConfigHistory(
                config_key=key,
                old_value=old_value,
                new_value=new_value,
                changed_by=updated_by,
                reason=reason
            )
            self.db.add(history)
            # Don't commit here - let the caller handle the transaction
            
        except Exception as e:
            logger.warning(f"Failed to record config history for {key}: {e}")