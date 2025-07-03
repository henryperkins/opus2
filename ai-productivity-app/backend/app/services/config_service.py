"""Service for managing persistent runtime configuration."""

import logging
import re
from typing import Any, Dict, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import text

from app.models.config import RuntimeConfig, ConfigHistory, ModelConfiguration, ModelUsageMetrics
from app.config import settings
from app.utils.crypto import encrypt_secret, decrypt_secret, is_secret_key, mask_secret_value, is_encryption_available

logger = logging.getLogger(__name__)


class ConfigService:
    """Service for managing persistent runtime configuration."""

    _CAMEL_SPLIT = re.compile(r'(?<!^)(?=[A-Z])')  # fooBar → foo_Bar

    # ---------- internal helpers ------------------------------------------------

    @classmethod
    def _to_snake(cls, key: str) -> str:
        """Convert camelCase / PascalCase to lower_snake_case."""
        return cls._CAMEL_SPLIT.sub('_', key).lower()

    def __init__(self, db: Session):
        self.db = db

    def get_config(self, key: str) -> Optional[Any]:
        """Get a configuration value by key."""
        config = self.db.query(RuntimeConfig).filter_by(key=key).first()
        return config.value if config else None

    def get_all_config(self, include_secrets: bool = True, mask_secrets: bool = False) -> Dict[str, Any]:
        """Get all configuration as a dictionary.

        Args:
            include_secrets: Whether to include secret values in the result
            mask_secrets: Whether to mask secret values for display
        """
        configs = self.db.query(RuntimeConfig).all()
        result = {}
        for config in configs:
            key = config.key
            value = config.value
            # Handle secret values
            if config.value_type == "secret" and value:
                if not include_secrets:
                    continue  # Skip secret values entirely
                try:
                    # Decrypt the secret value
                    decrypted_value = decrypt_secret(value)
                    if mask_secrets:
                        value = mask_secret_value(decrypted_value)
                    else:
                        value = decrypted_value
                except Exception as e:
                    logger.warning("Failed to decrypt secret for key %s: %s", key, e)
                    value = "***" if mask_secrets else None
            elif is_secret_key(key) and mask_secrets and value:
                # Mask unencrypted secrets for display
                value = mask_secret_value(str(value))
            result[key] = value
        return result

    def set_config(self, key: str, value: Any, description: str = None,
                   requires_restart: bool = False, updated_by: str = None) -> RuntimeConfig:
        """Set a configuration value, creating or updating as needed."""

        # Convert camelCase to snake_case
        key = self._to_snake(key)

        # Get existing config if it exists
        existing = self.db.query(RuntimeConfig).filter_by(key=key).first()
        old_value = existing.value if existing else None

        # Encrypt secret values if encryption is available
        stored_value = value
        value_type = self._get_value_type(value)
        if is_secret_key(key) and isinstance(value, str) and value and is_encryption_available():
            try:
                stored_value = encrypt_secret(value)
                value_type = "secret"
                logger.debug("Encrypted secret value for key: %s", key)
            except Exception as e:
                logger.warning("Failed to encrypt secret for key %s: %s", key, e)
                # Continue with unencrypted value but log the issue

        if existing:
            # Update existing configuration
            existing.value = stored_value
            if description is not None:
                existing.description = description
            existing.value_type = value_type
            existing.requires_restart = requires_restart
            existing.updated_by = updated_by
            config = existing
        else:
            # Create new configuration
            config = RuntimeConfig(
                key=key,
                value=stored_value,
                value_type=value_type,
                description=description,
                requires_restart=requires_restart,
                updated_by=updated_by
            )
            self.db.add(config)

        try:
            self.db.commit()

            # Record configuration change in history
            self._record_history(key, old_value, value, updated_by)

            logger.info("Configuration updated: %s = %s", key, value)
            return config

        except IntegrityError as e:
            self.db.rollback()
            logger.error("Failed to update configuration %s: %s", key, e)
            raise

    def set_multiple_config(self, config_dict: Dict[str, Any],
                            updated_by: str = None) -> Dict[str, RuntimeConfig]:
        """Set multiple configuration values in a single transaction."""
        results = {}

        try:
            for raw_key, value in config_dict.items():
                key = self._to_snake(raw_key)
                existing = self.db.query(RuntimeConfig).filter_by(key=key).first()
                old_value = existing.value if existing else None

                # Encrypt secret values if encryption is available
                stored_value = value
                value_type = self._get_value_type(value)
                if is_secret_key(key) and isinstance(value, str) and value and is_encryption_available():
                    try:
                        stored_value = encrypt_secret(value)
                        value_type = "secret"
                        logger.debug("Encrypted secret value for key: %s", key)
                    except Exception as e:
                        logger.warning("Failed to encrypt secret for key %s: %s", key, e)
                        # Continue with unencrypted value but log the issue

                if existing:
                    existing.value = stored_value
                    existing.value_type = value_type
                    existing.updated_by = updated_by
                    results[key] = existing
                else:
                    config = RuntimeConfig(
                        key=key,
                        value=stored_value,
                        value_type=value_type,
                        updated_by=updated_by
                    )
                    self.db.add(config)
                    results[key] = config

                # Record in history
                self._record_history(key, old_value, value, updated_by)

            self.db.commit()
            logger.info("Multiple configurations updated: %s", list(config_dict.keys()))
            return results

        except Exception as e:
            self.db.rollback()
            logger.error("Failed to update multiple configurations: %s", e)
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

            logger.info("Configuration deleted: %s", key)
            return True

        except Exception as e:
            self.db.rollback()
            logger.error("Failed to delete configuration %s: %s", key, e)
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
            "use_responses_api": False,
            "max_tokens": None,
            "top_p": None,
            "frequency_penalty": None,
            "presence_penalty": None,
            "system_prompt": None,
        }

        # Only set defaults for keys that don't already exist
        existing_keys = set(config.key for config in self.db.query(RuntimeConfig).all())

        new_configs = {}
        for key, value in defaults.items():
            if key not in existing_keys:
                new_configs[key] = value

        if new_configs:
            self.set_multiple_config(new_configs, updated_by="system_init")
            logger.info("Initialized default configurations: %s", list(new_configs.keys()))

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
            logger.warning("Failed to record config history for %s: %s", key, e)

    # Model Configuration Management

    def get_model_configuration(self, model_id: str) -> Optional[ModelConfiguration]:
        """Get detailed configuration for a specific model."""
        return self.db.query(ModelConfiguration).filter_by(model_id=model_id).first()

    def get_available_models(self, provider: Optional[str] = None,
                             capabilities: Optional[List[str]] = None) -> List[ModelConfiguration]:
        """Get list of available models with optional filtering."""
        query = self.db.query(ModelConfiguration).filter(
            ModelConfiguration.is_available.is_(True),
            ModelConfiguration.is_deprecated.is_(False)
        )

        if provider:
            query = query.filter(ModelConfiguration.provider == provider)

        if capabilities and self.db.bind.dialect.name == 'postgresql':
            # Use PostgreSQL JSONB operators for capability filtering
            for capability in capabilities:
                query = query.filter(
                    text("capabilities @> :capability").bindparam(capability=f'["{capability}"]')
                )

        return query.order_by(ModelConfiguration.model_family, ModelConfiguration.name).all()

    def create_model_configuration(self, model_data: Dict[str, Any]) -> ModelConfiguration:
        """Create a new model configuration."""
        model_config = ModelConfiguration(**model_data)
        self.db.add(model_config)

        try:
            self.db.commit()
            logger.info("Created model configuration: %s", model_config.model_id)
            return model_config
        except IntegrityError as e:
            self.db.rollback()
            logger.error("Failed to create model configuration: %s", e)
            raise

    def update_model_configuration(self, model_id: str, updates: Dict[str, Any]) -> Optional[ModelConfiguration]:
        """Update an existing model configuration."""
        model_config = self.get_model_configuration(model_id)
        if not model_config:
            return None

        for key, value in updates.items():
            if hasattr(model_config, key):
                setattr(model_config, key, value)

        try:
            self.db.commit()
            logger.info("Updated model configuration: %s", model_id)
            return model_config
        except IntegrityError as e:
            self.db.rollback()
            logger.error("Failed to update model configuration: %s", e)
            raise

    def get_model_by_capabilities(self, required_capabilities: List[str],
                                  provider: Optional[str] = None) -> List[ModelConfiguration]:
        """Find models that have all required capabilities."""
        if self.db.bind.dialect.name == 'postgresql':
            # Use PostgreSQL JSONB containment operator
            capability_filter = text("capabilities @> :capabilities").bindparam(
                capabilities=str(required_capabilities).replace("'", '"')
            )
        else:
            # Fallback for SQLite - less efficient
            capability_filter = text("1=1")  # TODO: Implement SQLite fallback

        query = self.db.query(ModelConfiguration).filter(
            ModelConfiguration.is_available.is_(True),
            ModelConfiguration.is_deprecated.is_(False),
            capability_filter
        )

        if provider:
            query = query.filter(ModelConfiguration.provider == provider)

        return query.order_by(ModelConfiguration.avg_response_time_ms).all()

    def get_cost_efficient_models(self, limit: int = 5) -> List[ModelConfiguration]:
        """Get most cost-efficient models based on cost per token and throughput."""
        if self.db.bind.dialect.name == 'postgresql':
            # Use PostgreSQL expression for cost efficiency calculation
            query = self.db.query(ModelConfiguration).filter(
                ModelConfiguration.is_available.is_(True),
                ModelConfiguration.is_deprecated.is_(False),
                ModelConfiguration.cost_input_per_1k.isnot(None),
                ModelConfiguration.cost_output_per_1k.isnot(None),
                ModelConfiguration.throughput_tokens_per_sec.isnot(None)
            ).order_by(
                text("(cost_input_per_1k + cost_output_per_1k) / throughput_tokens_per_sec")
            ).limit(limit)
        else:
            # Fallback for SQLite
            query = self.db.query(ModelConfiguration).filter(
                ModelConfiguration.is_available.is_(True),
                ModelConfiguration.is_deprecated.is_(False)
            ).order_by(ModelConfiguration.cost_input_per_1k).limit(limit)

        return query.all()

    # Model Usage Metrics

    def record_model_usage(self, model_id: str, metrics_data: Dict[str, Any]) -> ModelUsageMetrics:
        """Record usage metrics for a model."""
        usage_metrics = ModelUsageMetrics(
            model_id=model_id,
            **metrics_data
        )
        self.db.add(usage_metrics)

        try:
            self.db.commit()
            logger.debug("Recorded usage metrics for model: %s", model_id)
            return usage_metrics
        except IntegrityError as e:
            self.db.rollback()
            logger.error("Failed to record model usage metrics: %s", e)
            raise

    def get_model_usage_metrics(self, model_id: str, days: int = 30) -> List[ModelUsageMetrics]:
        """Get usage metrics for a model over the specified time period."""
        if self.db.bind.dialect.name == 'postgresql':
            query = self.db.query(ModelUsageMetrics).filter(
                ModelUsageMetrics.model_id == model_id,
                text("period_end > CURRENT_TIMESTAMP - INTERVAL :days DAY").bindparam(days=days)
            ).order_by(ModelUsageMetrics.period_start.desc())
        else:
            # SQLite fallback
            query = self.db.query(ModelUsageMetrics).filter(
                ModelUsageMetrics.model_id == model_id
            ).order_by(ModelUsageMetrics.period_start.desc())

        return query.all()

    def get_model_performance_summary(self, model_id: str) -> Optional[Dict[str, Any]]:
        """Get aggregated performance summary for a model."""
        if self.db.bind.dialect.name == 'postgresql':
            # Use PostgreSQL aggregation functions
            result = self.db.execute(text("""
                SELECT
                    AVG(avg_response_time_ms) as avg_response_time,
                    AVG(success_rate) as avg_success_rate,
                    SUM(total_requests) as total_requests,
                    SUM(total_cost) as total_cost,
                    AVG(avg_user_rating) as avg_user_rating
                FROM model_usage_metrics
                WHERE model_id = :model_id
                AND period_end > CURRENT_TIMESTAMP - INTERVAL '30 days'
            """), {"model_id": model_id}).fetchone()

            if result:
                return {
                    "avg_response_time_ms": float(result.avg_response_time) if result.avg_response_time else None,
                    "avg_success_rate": float(result.avg_success_rate) if result.avg_success_rate else None,
                    "total_requests": int(result.total_requests) if result.total_requests else 0,
                    "total_cost": float(result.total_cost) if result.total_cost else 0.0,
                    "avg_user_rating": float(result.avg_user_rating) if result.avg_user_rating else None
                }

        return None

    # Configuration Validation

    async def validate_config(self, config_dict: Dict[str, Any]) -> tuple[bool, str]:
        """Validate a configuration by testing it with the LLM provider.

        Args:
            config_dict: Configuration dictionary to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        import asyncio
        from app.llm.client import LLMClient

        provider = config_dict.get("provider", "openai")
        model = config_dict.get("chat_model", "gpt-3.5-turbo")
        temperature = config_dict.get("temperature", 0.7)
        max_tokens = config_dict.get("max_tokens", 50)
        use_responses = config_dict.get("use_responses_api", False)

        try:
            client = LLMClient()
            await client.reconfigure(
                provider=provider,
                model=model,
                use_responses_api=use_responses,
            )

            # Determine which endpoint to test
            if provider == "azure" and use_responses:
                # Test Responses API
                try:
                    reasoning_effort = config_dict.get("reasoning_effort", "high")
                    resp = await asyncio.wait_for(
                        client.complete(
                            input="Say 'test successful' briefly.",
                            reasoning={"effort": reasoning_effort, "summary": "auto"},
                            max_tokens=max_tokens,
                            stream=False,
                        ),
                        timeout=30,
                    )
                    # Handle different response structures for reasoning models
                    if hasattr(resp, "output") and resp.output:
                        last_output = resp.output[-1]
                        if hasattr(last_output, 'content'):
                            # Standard response structure
                            if isinstance(last_output.content, list) and len(last_output.content) > 0:
                                resp_text = last_output.content[0].text.strip()
                            else:
                                resp_text = str(last_output.content)
                        elif hasattr(last_output, 'text'):
                            # Direct text attribute
                            resp_text = last_output.text.strip()
                        else:
                            # Fallback to string representation
                            resp_text = str(last_output)
                    else:
                        resp_text = str(resp)
                except asyncio.TimeoutError:
                    return False, "Responses-API test timed out after 30 seconds"
            else:
                # Test Chat Completions
                try:
                    resp = await asyncio.wait_for(
                        client.complete(
                            messages=[
                                {
                                    "role": "system",
                                    "content": "Respond with 'test successful' exactly.",
                                },
                                {"role": "user", "content": "Ping"},
                            ],
                            temperature=temperature,
                            max_tokens=max_tokens,
                            stream=False,
                        ),
                        timeout=30,
                    )
                except asyncio.TimeoutError:
                    return False, "Chat test timed out after 30 seconds"

                resp_text = (
                    resp.choices[0].message.content.strip()
                    if hasattr(resp, "choices")
                    else str(resp)
                )

            # Check if response contains expected text
            success = "test" in resp_text.lower()
            if success:
                return True, "Configuration validation successful"
            else:
                return False, f"Unexpected response from model: {resp_text[:100]}"

        except Exception as exc:
            msg = str(exc).lower()
            if any(k in msg for k in ("api key", "unauthorized")):
                return False, "Authentication failed - check your API key"
            elif any(k in msg for k in ("not found", "invalid")):
                return False, f"Invalid model: {model}"
            elif any(k in msg for k in ("timeout", "connection")):
                return False, "Connection failed - verify endpoint & network"
            else:
                return False, f"Test failed: {exc}"
