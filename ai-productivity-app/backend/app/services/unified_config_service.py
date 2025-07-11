# app/services/unified_config_service.py
"""
Unified configuration service for AI model settings.
Acts as **single source of truth** (RuntimeConfig table) and is consumed by
both sync code and the async façade (`UnifiedConfigServiceAsync`).

This module is intentionally synchronous – the async façade pushes every call
into a thread-pool so that FastAPI endpoints never block the event-loop.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.models.config import ConfigHistory, ModelConfiguration, RuntimeConfig
from app.schemas.generation import (
    UnifiedModelConfig,
    ModelInfo,
    # ConfigUpdate only used for type-hints, not required at runtime
)
# The consistency validator now lives in app.schemas.generation to keep all
# configuration-related helpers co-located with their Pydantic models.
from app.schemas.generation import validate_config_consistency  # type: ignore
from app.services.config_validation_service import ConfigValidationService
from app.services.config_preset_manager import ConfigPresetManager

logger = logging.getLogger(__name__)


class UnifiedConfigService:
    """Centralised service that owns all AI runtime-configuration data."""

    # --------------------------------------------------------------------- #
    # Constants / settings
    # --------------------------------------------------------------------- #
    CACHE_TTL_SECONDS = 300  # 5 min

    # --------------------------------------------------------------------- #
    # Construction
    # --------------------------------------------------------------------- #
    def __init__(self, db: Session):
        self.db: Session = db
        self._config_cache: Dict[str, Any] = {}
        self._cache_ts: Optional[datetime] = None
        self._validation_service = ConfigValidationService(db)
        self._preset_manager = ConfigPresetManager(db)

    # --------------------------------------------------------------------- #
    # Public – READ
    # --------------------------------------------------------------------- #
    def get_current_config(self) -> UnifiedModelConfig:
        """Return the current, validated, unified configuration."""
        run_cfg = self._load_all_config()
        try:
            return UnifiedModelConfig.from_runtime_config(run_cfg)
        except Exception as e:  # pragma: no cover
            logger.warning("Falling back to built-in defaults: %s", e)
            return self._get_default_config()

    def get_configuration_snapshot(
        self,
    ) -> Tuple[UnifiedModelConfig, List[ModelInfo], Dict[str, Dict[str, Any]]]:
        """
        Convenience helper used by the router: returns the current config,
        the list of models and a provider→info catalogue.
        """
        current_cfg = self.get_current_config()
        available_models = self.get_available_models()

        # Build provider catalogue ------------------------------------------------
        providers: Dict[str, Dict[str, Any]] = {}

        for mdl in available_models:
            p_key = mdl.provider.lower()
            providers.setdefault(
                p_key,
                {"display_name": p_key.capitalize(), "models": [], "capabilities": {}},
            )
            providers[p_key]["models"].append(mdl.model_dump(by_alias=True))

            # Merge capability flags: TRUE if any model supports it
            caps = mdl.capabilities or {}
            cap_fields = (
                "supports_functions",
                "supports_streaming",
                "supports_vision",
                "supports_responses_api",
                "supports_reasoning",
                "supports_thinking",
            )
            for field in cap_fields:
                if getattr(caps, field, False):
                    providers[p_key]["capabilities"][field] = True

        if not providers:
            # No DB? – at least expose the default provider
            def_provider = current_cfg.provider.lower()
            providers[def_provider] = {
                "display_name": def_provider.capitalize(),
                "models": [
                    {
                        "model_id": current_cfg.model_id,
                        "display_name": current_cfg.model_id,
                        "provider": def_provider,
                        "capabilities": {},
                    }
                ],
                "capabilities": {},
            }

        return current_cfg, available_models, providers

    def get_model_info(self, model_id: str) -> Optional[ModelInfo]:
        """Return `ModelInfo` for a specific `model_id` (or `None`)."""
        cfg: ModelConfiguration | None = (
            self.db.query(ModelConfiguration).filter_by(model_id=model_id).first()
        )
        return self._model_config_to_info(cfg) if cfg else None

    def get_available_models(
        self, provider: Optional[str] = None, include_deprecated: bool = False
    ) -> List[ModelInfo]:
        """Return all models, optionally filtered."""
        try:
            q = self.db.query(ModelConfiguration)
            if provider:
                q = q.filter_by(provider=provider)
            if not include_deprecated:
                q = q.filter_by(is_deprecated=False)
            rows = q.all()
            return sorted(
                (self._model_config_to_info(r) for r in rows),
                key=lambda m: (m.provider, m.display_name),
            )
        except Exception as e:  # pragma: no cover
            logger.warning("Could not fetch ModelConfiguration: %s", e)
            return []

    # --------------------------------------------------------------------- #
    # Public – WRITE
    # --------------------------------------------------------------------- #
    def update_config(
        self, updates: Dict[str, Any], *, updated_by: str = "api"
    ) -> UnifiedModelConfig:
        """
        Apply a single update dict to the current configuration.

        This implementation ensures:
        - Field merging uses alias (camelCase) names for compatibility with the frontend.
        - Resolves potential snake_case/camelCase conflicts by always favoring the frontend alias.
        - All validation for required fields and provider-aware business rules is enforced after normalization.
        - Provides clear error messages mapping to specific fields.

        Args:
            updates (Dict[str, Any]): Dictionary of updates (camelCase, as sent by frontend).
            updated_by (str): Identifier for who/what triggered the update.

        Returns:
            UnifiedModelConfig: The updated and validated configuration.

        Raises:
            ValueError: If required fields are missing or validation fails.
        """
        current = self.get_current_config()

        # Always use by_alias=True for frontend compatibility
        merged = current.model_dump(by_alias=True)
        merged.update(updates or {})  # Frontend PATCH fields (camelCase) take priority

        # Defensive cleanup: if any snake_case fields exist redundantly, drop them
        # (e.g., both model_id and modelId present—use modelId).
        for snake_name, alias in [("model_id", "modelId"), ("provider", "provider")]:
            if alias in merged and snake_name in merged:
                merged.pop(snake_name)

        try:
            new_cfg = UnifiedModelConfig(**merged)
        except ValueError as e:
            # Try to extract clear field-level errors using the validation service
            details = self._validation_service.get_missing_fields_details(e)
            if details:
                field_msgs = [f"{d['field']}: {d['message']}" for d in details]
                raise ValueError(f"Invalid configuration: {'; '.join(field_msgs)}") from None
            raise ValueError(f"Invalid configuration: {e}") from None

        # Additional provider/model business validation
        ok, err = self.validate_config(new_cfg.model_dump(by_alias=True))
        if not ok:
            raise ValueError(err or "Invalid configuration")

        self._save_config(new_cfg.to_runtime_config(), updated_by)
        self._invalidate_cache()
        return new_cfg

    def batch_update(
        self, updates: List[Dict[str, Any]], *, updated_by: str
    ) -> UnifiedModelConfig:
        """
        Atomically apply a list of updates.  Rolls back if any update fails.
        """
        # Snapshot before we begin
        original = self.get_current_config()

        try:
            final_cfg = original
            for upd in updates:
                final_cfg = self.update_config(upd, updated_by=updated_by)
            return final_cfg
        except Exception:
            # Roll back to original if anything went wrong
            logger.warning("Batch update failed – rolling back")
            self._save_config(original.to_runtime_config(), f"rollback_{updated_by}")
            self._invalidate_cache()
            raise

    # --------------------------------------------------------------------- #
    # Public – VALIDATION / TEST
    # --------------------------------------------------------------------- #
    def validate_config(
        self, config_dict: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """
        Lightweight validation – used internally by `update_config`.
        """
        try:
            cfg = UnifiedModelConfig(**config_dict)
            ok, err = validate_config_consistency(cfg)
            if not ok:
                return False, err

            # Additional model-specific validation
            from app.services.model_service import ModelService

            msvc = ModelService(self.db)
            ok, err = msvc.validate_model_config(cfg.model_id, config_dict)
            return ok, err
        except ValueError as e:
            return False, str(e)
        except Exception as e:
            logger.error("Validation failed: %s", e)
            return False, "Validation internal error"

    # Verbose helper used by `/validate` route -----------------------------
    def validate_verbose(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        ok, err = self.validate_config(payload)
        capabilities: Dict[str, Any] = {}
        warnings: List[str] = []

        if "model_id" in payload:
            try:
                from app.services.model_service import ModelService

                ms = ModelService(self.db)
                mid = payload["model_id"]
                capabilities = {
                    "supports_streaming": ms.supports_streaming(mid),
                    "supports_functions": ms.supports_functions(mid),
                    "supports_vision": ms.supports_vision(mid),
                    "supports_reasoning": ms.is_reasoning_model(mid),
                    "max_tokens": ms.get_max_tokens(mid),
                    "context_window": ms.get_context_window(mid),
                }

                # some simple rule-based warnings
                if payload.get("stream") and not capabilities["supports_streaming"]:
                    warnings.append(f"Model {mid} does not support streaming")

                if payload.get("tools") and not capabilities["supports_functions"]:
                    warnings.append(f"Model {mid} does not support function calling")

                if (
                    payload.get("max_tokens")
                    and payload["max_tokens"] > capabilities["max_tokens"]
                ):
                    warnings.append(
                        f"Requested max_tokens exceeds limit ({capabilities['max_tokens']})"
                    )
            except Exception as e:  # pragma: no cover
                logger.warning("Capability extraction failed: %s", e)

        return {
            "valid": ok,
            "error": err,
            "capabilities": capabilities,
            "warnings": warnings,
            "validated_at": datetime.utcnow(),
        }

    async def test_config(
        self, config: UnifiedModelConfig, dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Live test against the LLM provider (or dry-run validation).
        """
        # dry-run ----------------------------------------------------------
        if dry_run:
            t0 = time.perf_counter()
            ok, err = self.validate_config(config.model_dump())
            model_info = self.get_model_info(config.model_id)

            elapsed = time.perf_counter() - t0
            return {
                "success": ok,
                "message": "Validation passed" if ok else "Validation failed",
                "error": err,
                "response_time": round(elapsed, 3),
                "dry_run": True,
                "model_info": model_info.model_dump(by_alias=True) if model_info else {},
            }

        # live invocation --------------------------------------------------
        import asyncio
        from app.llm.client import llm_client as client

        snapshot = client.snapshot()
        t0 = time.perf_counter()

        try:
            await client.reconfigure(**config.model_dump())
            test_messages = [
                {"role": "system", "content": "You are a test assistant."},
                {
                    "role": "user",
                    "content": "Reply with exactly: test successful",
                },
            ]
            await asyncio.wait_for(
                client.complete(
                    messages=test_messages,
                    model=config.model_id,
                    temperature=config.temperature,
                    max_tokens=10,
                    stream=False,
                ),
                timeout=30,
            )
            return {
                "success": True,
                "message": "Configuration test successful",
                "response_time": round(time.perf_counter() - t0, 2),
                "dry_run": False,
            }
        except asyncio.TimeoutError:
            return {"success": False, "message": "Timeout", "error": "timeout", "dry_run": False}
        except Exception as e:  # pragma: no cover
            logger.error("Live configuration test failed: %s", e)
            return {
                "success": False,
                "message": "Live test failed",
                "error": str(e),
                "dry_run": False,
            }
        finally:
            await client.restore(snapshot)

    # --------------------------------------------------------------------- #
    # Private helpers – persistence
    # --------------------------------------------------------------------- #
    def _load_all_config(self) -> Dict[str, Any]:
        if self._config_cache and self._cache_ts:
            if datetime.utcnow() - self._cache_ts < timedelta(seconds=self.CACHE_TTL_SECONDS):
                return self._config_cache

        try:
            rows = self.db.query(RuntimeConfig).all()
        except Exception as e:  # pragma: no cover
            logger.warning("RuntimeConfig query failed – using empty config: %s", e)
            rows = []

        cfg: Dict[str, Any] = {}
        for row in rows:
            try:
                if row.value_type == "boolean":
                    cfg[row.key] = row.value in (True, "true", "True", "1", 1)
                elif row.value_type == "number":
                    cfg[row.key] = row.value
                else:
                    cfg[row.key] = row.value
            except Exception as e:  # pragma: no cover
                logger.warning("Could not parse RuntimeConfig[%s]: %s", row.key, e)

        self._config_cache = cfg
        self._cache_ts = datetime.utcnow()
        return cfg

    def _save_config(self, config: Dict[str, Any], updated_by: str) -> None:
        """Persist the runtime configuration dictionary."""
        for key, val in config.items():
            if val is None:
                continue

            if isinstance(val, bool):
                vtype = "boolean"
            elif isinstance(val, (int, float)):
                vtype = "number"
            elif isinstance(val, dict):
                vtype = "object"
            elif isinstance(val, list):
                vtype = "array"
            else:
                vtype = "string"
                val = str(val)

            existing = self.db.query(RuntimeConfig).filter_by(key=key).first()
            if existing:
                if existing.value != val:
                    self.db.add(
                        ConfigHistory(
                            config_key=key,
                            old_value=existing.value,
                            new_value=val,
                            changed_by=updated_by,
                        )
                    )
                    existing.value = val
                    existing.value_type = vtype
                    existing.updated_by = updated_by
            else:
                self.db.add(
                    RuntimeConfig(
                        key=key,
                        value=val,
                        value_type=vtype,
                        updated_by=updated_by,
                    )
                )
        try:
            self.db.commit()
            self.db.expire_all()
        except IntegrityError as e:
            self.db.rollback()
            logger.error("Integrity error while saving config: %s", e)
            raise ValueError(f"Configuration update failed: {e}") from None
        except Exception as e:  # pragma: no cover
            self.db.rollback()
            logger.error("Unexpected DB error: %s", e)
            raise RuntimeError("Database error while saving configuration") from e

    def _invalidate_cache(self) -> None:
        self._config_cache.clear()
        self._cache_ts = None

    # --------------------------------------------------------------------- #
    # Private helpers – defaults / mapping
    # --------------------------------------------------------------------- #
    def _get_default_config(self) -> UnifiedModelConfig:
        """
        Build a robust fallback config when the DB is empty/unavailable.

        Ensures the config always satisfies UnifiedModelConfig/Pydantic requirements
        and prevents 422 errors due to missing provider/model_id/fields.
        """
        default_provider = settings.llm_provider
        default_model = settings.llm_default_model

        allowed_providers = {"openai", "azure", "anthropic"}
        fallback_provider = "openai"
        fallback_model = "gpt-3.5-turbo"

        try:
            mc = (
                self.db.query(ModelConfiguration)
                .filter_by(model_id=default_model, is_available=True, is_deprecated=False)
                .first()
            )
            if not mc:
                mc = (
                    self.db.query(ModelConfiguration)
                    .filter_by(provider=default_provider, is_available=True, is_deprecated=False)
                    .first()
                )
        except Exception as e:  # pragma: no cover
            logger.warning("ModelConfiguration lookup failed: %s", e)
            mc = None

        provider = None
        model_id = None

        if mc:
            provider = mc.provider
            model_id = mc.model_id
        else:
            # Defensive fallback logic
            provider = default_provider if default_provider in allowed_providers else fallback_provider
            model_id = default_model or fallback_model

        # If still missing or invalid, force valid fields and log a clear warning
        if provider not in allowed_providers:
            logger.error(f"Configured LLM provider '{provider}' is invalid/missing, using '{fallback_provider}' fallback.")
            provider = fallback_provider
        if not isinstance(model_id, str) or not model_id:
            logger.error("Configured default model_id is empty or missing, using '%s'.", fallback_model)
            model_id = fallback_model

        return UnifiedModelConfig(
            provider=provider,
            model_id=model_id,
            temperature=0.7,
            max_tokens=1024,
            top_p=1.0,
            frequency_penalty=0.0,
            presence_penalty=0.0,
            enable_reasoning=getattr(settings, "enable_reasoning", False),
            reasoning_effort=getattr(settings, "reasoning_effort", "medium"),
            claude_extended_thinking=getattr(settings, "claude_extended_thinking", True),
            claude_thinking_mode=getattr(settings, "claude_thinking_mode", "enabled"),
            claude_thinking_budget_tokens=getattr(settings, "claude_thinking_budget_tokens", 16384),
        )

    def _model_config_to_info(self, mc: ModelConfiguration) -> ModelInfo:
        from app.schemas.generation import ModelCapabilities

        caps = ModelCapabilities(**(mc.capabilities or {}))
        return ModelInfo(
            model_id=mc.model_id,
            display_name=mc.name,
            provider=mc.provider,
            model_family=mc.model_family,
            capabilities=caps,
            cost_per_1k_input_tokens=mc.cost_input_per_1k,
            cost_per_1k_output_tokens=mc.cost_output_per_1k,
            performance_tier="balanced",
            average_latency_ms=mc.avg_response_time_ms,
            is_available=mc.is_available,
            is_deprecated=mc.is_deprecated,
            deprecation_date=getattr(mc, "deprecated_at", None),
            recommended_use_cases=getattr(mc, "model_metadata", {}).get(
                "recommended_use_cases", []
            ),
        )

    # --------------------------------------------------------------------- #
    # Presets & defaults API
    # --------------------------------------------------------------------- #
    def get_presets(self) -> List[Dict[str, Any]]:
        """Return predefined configuration presets with provider awareness."""
        return self._preset_manager.get_presets()

    def apply_preset(self, preset_id: str, target_provider: Optional[str] = None) -> UnifiedModelConfig:
        """Apply a preset configuration, adapting it to the current or target provider."""
        current = self.get_current_config()

        # Get the preset configuration adapted for the provider
        preset_config = self._preset_manager.apply_preset(preset_id, current, target_provider)

        # Apply the preset configuration
        return self.update_config(preset_config, updated_by="preset")

    def get_defaults(self) -> Dict[str, Any]:
        """Expose built-in defaults (camel-case) for the API."""
        return self._get_default_config().model_dump(by_alias=True)

    def initialize_defaults(self):
        """Initialize default configurations. Called during app startup."""
        # This method is called synchronously during app startup
        # For now, we'll just log that initialization is happening
        logger.info("UnifiedConfigService initialized")

        # Any default configuration setup can be added here
        # For example, setting up default AI provider configs, etc.
        pass

    def cleanup(self):
        """Cleanup resources."""
        if hasattr(self, 'db') and self.db:
            self.db.close()
