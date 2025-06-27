# backend/app/routers/config.py
"""Runtime configuration & metadata endpoints (Responses-API ready).

This revision introduces **native support for the Azure *Responses API*.**

Changes
-------
• `use_responses_api` flag is respected end-to-end (DB → LLM client → /test).
• `/test` now sends a *Responses* request when the flag is enabled instead of a
  Chat Completions request.
• Model catalogue already contained the new *o-series* models – no change
  required beyond updating the *features* block.
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import (
    BaseModel,
    Field,
    NonNegativeInt,
    confloat,
    validator,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.services.config_service import ConfigService
from app.llm.client import LLMClient  # abstraction layer used throughout

router = APIRouter(prefix="/api/config", tags=["config"])
logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# Pydantic schema for updates                                                 #
# --------------------------------------------------------------------------- #


class ModelConfigPayload(BaseModel):
    provider: str | None = Field(None, examples=["openai", "azure"])
    chat_model: str | None = Field(None, examples=["o3", "gpt-4o-mini"])

    # Optional gen-params (validated; some not supported by reasoning models)
    temperature: confloat(ge=0.0, le=2.0) | None = None
    max_tokens: NonNegativeInt | None = Field(None, alias="maxTokens")
    top_p: confloat(ge=0.0, le=1.0) | None = Field(None, alias="topP")
    frequency_penalty: confloat(ge=0.0, le=2.0) | None = Field(
        None, alias="frequencyPenalty"
    )
    presence_penalty: confloat(ge=0.0, le=2.0) | None = Field(
        None, alias="presencePenalty"
    )
    system_prompt: str | None = Field(None, alias="systemPrompt")

    # Toggle Responses API (camelCase externally)
    use_responses_api: bool | None = Field(None, alias="useResponsesApi")
    
    # Reasoning effort level for o-series models
    reasoning_effort: str | None = Field(None, pattern=r"^(low|medium|high)$")

    class Config:
        populate_by_name = True

    @validator("provider")
    @classmethod
    def _normalise_provider(cls, v):  # noqa: N805
        if v is None:
            return v
        v = v.lower()
        if v not in {"openai", "azure"}:
            raise ValueError("Unsupported provider")
        return v


# --------------------------------------------------------------------------- #
# In-memory fallback (dev / CI)                                               #
# --------------------------------------------------------------------------- #
def _should_use_responses_api(model_name: str = None) -> bool:
    """Determine if Responses API should be used based on API version and model."""
    # Import here to avoid circular dependency
    from app.llm.client import _is_responses_api_enabled
    return _is_responses_api_enabled(model_name)

_DEFAULT_RESPONSES_FLAG = _should_use_responses_api(settings.llm_default_model or settings.llm_model)

_RUNTIME_CONFIG: dict[str, Any] = {
    "provider": settings.llm_provider,
    "chat_model": settings.llm_default_model or settings.llm_model,
    "use_responses_api": _DEFAULT_RESPONSES_FLAG,
}

# --------------------------------------------------------------------------- #
# Dependency helpers                                                          #
# --------------------------------------------------------------------------- #


def get_config_service(db: Session = Depends(get_db)) -> ConfigService:
    return ConfigService(db)


def _merged_config(cfg_svc: ConfigService) -> dict[str, Any]:
    """Return DB config merged with in-memory defaults."""
    try:
        db_cfg = cfg_svc.get_all_config()
        if not db_cfg:
            cfg_svc.initialize_default_config()
            db_cfg = cfg_svc.get_all_config()
        
        merged = {**_RUNTIME_CONFIG, **db_cfg}
        
        # Auto-detect Responses API requirement if not explicitly set
        if "use_responses_api" not in db_cfg:
            current_model = merged.get("chat_model")
            merged["use_responses_api"] = _should_use_responses_api(current_model)
            
        return merged
    except Exception as exc:  # pragma: no cover
        logger.warning("Falling back to in-memory config: %s", exc)
        return _RUNTIME_CONFIG


# --------------------------------------------------------------------------- #
# Static model catalogues                                                     #
# --------------------------------------------------------------------------- #
_OPENAI_CHAT_MODELS = [
    "gpt-4o-mini",
    "gpt-4o",
    "gpt-4-turbo",
    "gpt-4",
    "gpt-3.5-turbo-0125",
    "gpt-3.5-turbo-1106",
    "gpt-3.5-turbo-0613",
]
_OPENAI_EMBED_MODELS = [
    "text-embedding-3-small",
    "text-embedding-3-large",
    "text-embedding-ada-002",
]

_AZURE_CHAT_MODELS = [
    # Available deployment names
    "gpt-4.1",  # Primary deployment for general use
    "o3",       # Reasoning model deployment
    # o-series reasoning models
    "o4-mini",
    "o3-pro",
    "o3-mini",
    "o1",
    "o1-mini",
    "o1-preview",
    # traditional GPT models
    "gpt-4o",
    "gpt-4o-mini",
    "gpt-4-turbo",
    "gpt-4",
    "gpt-35-turbo",
    # codex
    "codex-mini",
    # image & misc
    "gpt-image-1",
    "computer-use-preview",
]
_AZURE_EMBED_MODELS = [
    "text-embedding-3-small",
    "text-embedding-3-large",
    "text-embedding-ada-002",
]
_AZURE_API_VERSIONS = ["2024-02-01", "2025-04-01-preview", "preview"]

# --------------------------------------------------------------------------- #
# GET /api/config                                                             #
# --------------------------------------------------------------------------- #


@router.get("", summary="Return supported LLM providers and models")  # noqa: D401
async def get_config(cfg_svc: ConfigService = Depends(get_config_service)):
    """Return static provider catalogue and current defaults."""
    current = _merged_config(cfg_svc)

    camel_current = {
        "provider": current.get("provider"),
        "chat_model": current.get("chat_model"),
        "useResponsesApi": current.get("use_responses_api", False),
        "temperature": current.get("temperature", 0.7),
        "maxTokens": current.get("max_tokens"),
        "topP": current.get("top_p"),
        "frequencyPenalty": current.get("frequency_penalty"),
        "presencePenalty": current.get("presence_penalty"),
        "systemPrompt": current.get("system_prompt"),
    }

    logger.info("/api/config requested – sending catalogue")
    return {
        "providers": {
            "openai": {
                "chat_models": _OPENAI_CHAT_MODELS,
                "embedding_models": _OPENAI_EMBED_MODELS,
            },
            "azure": {
                "chat_models": _AZURE_CHAT_MODELS,
                "embedding_models": _AZURE_EMBED_MODELS,
                "api_versions": _AZURE_API_VERSIONS,
                "features": {
                    "responses_api": True,  # always available now
                    "background_tasks": True,
                    "image_generation": True,
                    "computer_use": True,
                    "mcp_servers": True,
                },
            },
        },
        "current": camel_current,
    }


# --------------------------------------------------------------------------- #
# PUT /api/config/model                                                       #
# --------------------------------------------------------------------------- #


@router.put("/model", summary="Update runtime chat-model configuration")  # noqa: D401
async def update_model_config(
    payload: ModelConfigPayload,
    cfg_svc: ConfigService = Depends(get_config_service),
):
    """Persist partial configuration & propagate to subsystems."""
    data = payload.dict(exclude_unset=True, by_alias=False)
    if not data:
        raise HTTPException(400, "No configuration provided")

    try:
        # Validate configuration before committing
        ok, detail = await cfg_svc.validate_config(data)
        if not ok:
            logger.warning(f"Config validation failed: {detail}")
            raise HTTPException(422, f"Validation failed: {detail}")   # ➜ 422 not 500

        cfg_svc.set_multiple_config(data, updated_by="api_user")
        _RUNTIME_CONFIG.update(data)

        # Invalidate cache after config update
        from app.services.config_cache import _cached
        _cached.cache_clear()

        if {"provider", "chat_model", "use_responses_api"} & data.keys():
            # hot-reload global LLM client
            try:
                from app.llm.client import llm_client

                await llm_client.reconfigure(
                    provider=data.get("provider"),
                    model=data.get("chat_model"),
                    use_responses_api=data.get("use_responses_api"),
                )
            except Exception as exc:  # pragma: no cover
                logger.warning("LLM client reconfiguration failed: %s", exc)
        # ------------------------------------------------------------------ #
        # Broadcast change – send the *same* structure returned by GET
        # /api/config so the frontend hook ingests it without falling back
        # to defaults.                                                       #
        # ------------------------------------------------------------------ #
        try:
            from app.websocket.manager import connection_manager

            # Rebuild full configuration payload
            current = _merged_config(cfg_svc)
            camel_current = {
                "provider": current.get("provider"),
                "chat_model": current.get("chat_model"),
                "useResponsesApi": current.get("use_responses_api", False),
                "temperature": current.get("temperature", 0.7),
                "maxTokens": current.get("max_tokens"),
                "topP": current.get("top_p"),
                "frequencyPenalty": current.get("frequency_penalty"),
                "presencePenalty": current.get("presence_penalty"),
                "systemPrompt": current.get("system_prompt"),
            }

            full_config = {
                "providers": {
                    "openai": {
                        "chat_models": _OPENAI_CHAT_MODELS,
                        "embedding_models": _OPENAI_EMBED_MODELS,
                    },
                    "azure": {
                        "chat_models": _AZURE_CHAT_MODELS,
                        "embedding_models": _AZURE_EMBED_MODELS,
                        "api_versions": _AZURE_API_VERSIONS,
                        "features": {
                            "responses_api": True,
                            "background_tasks": True,
                            "image_generation": True,
                            "computer_use": True,
                            "mcp_servers": True,
                        },
                    },
                },
                "current": camel_current,
            }

            await connection_manager.broadcast_config_update(full_config)
        except Exception as exc:  # pragma: no cover
            logger.warning("WebSocket broadcast failed: %s", exc)

        return {
            "success": True,
            "message": "Model configuration updated",
            "current": _merged_config(cfg_svc),
        }

    except IntegrityError as exc:
        logger.warning("DB error: %s", exc)
        raise HTTPException(409, "Duplicate/constraint violation")     # specific 4xx
    except HTTPException:
        # Re-raise HTTP exceptions as-is to preserve status codes
        raise
    except UnboundLocalError as exc:
        logger.error(f"Variable scope error in validation: {exc}", exc_info=True)
        raise HTTPException(422, f"Validation failed: Configuration error - {exc}") from exc
    except ValueError as exc:
        logger.error(f"Invalid configuration value: {exc}", exc_info=True)
        raise HTTPException(422, f"Invalid configuration: {exc}") from exc
    except Exception as exc:  # pragma: no cover
        logger.error("Unexpected error during config update: %s", exc, exc_info=True)
        raise HTTPException(500, f"Internal server error during configuration update") from exc


# --------------------------------------------------------------------------- #
# POST /api/config/test                                                       #
# --------------------------------------------------------------------------- #


@router.post("/test", summary="Validate that the supplied configuration works")  # noqa: D401
async def test_model_config(payload: ModelConfigPayload):
    """Issue either a *Responses* or *Chat Completions* request as a smoke test."""
    start = time.time()
    provider = payload.provider or "openai"
    model = payload.chat_model or "gpt-3.5-turbo"
    temperature = payload.temperature or 0.7
    max_tokens = payload.max_tokens or 50
    use_responses = (
        payload.use_responses_api
        if payload.use_responses_api is not None
        else _should_use_responses_api(model)
    )

    try:
        client = LLMClient()
        await client.reconfigure(
            provider=provider,
            model=model,
            use_responses_api=use_responses,
        )

        # ------------------------------------------------------------------ #
        # 1) Determine which endpoint to call                                #
        # ------------------------------------------------------------------ #
        if provider == "azure" and use_responses:
            # Minimal Responses-API test call
            try:
                # Use simplified string input for reasoning models, message array for others
                from app.llm.client import _is_reasoning_model
                if _is_reasoning_model(model):
                    # Reasoning models - use string input with reasoning config for Responses API
                    reasoning_effort = payload.reasoning_effort or "high"
                    resp = await asyncio.wait_for(
                        client.complete(
                            input="Say 'test successful' briefly.",
                            reasoning={"effort": reasoning_effort, "summary": "auto"},
                            max_tokens=max_tokens,
                            stream=False,
                        ),
                        timeout=30,
                    )
                else:
                    # Regular models - use message array format
                    resp = await asyncio.wait_for(
                        client.complete(
                            input=[
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
                # Handle reasoning model responses with improved extraction
                if hasattr(resp, "output") and resp.output:
                    try:
                        last_output = resp.output[-1]
                        if hasattr(last_output, "type") and last_output.type == "reasoning":
                            # This is a reasoning output - skip it and look for message output
                            for output_item in resp.output:
                                if hasattr(output_item, "type") and output_item.type == "message":
                                    if hasattr(output_item, "content"):
                                        if isinstance(output_item.content, list) and len(output_item.content) > 0:
                                            resp_text = output_item.content[0].text.strip()
                                        else:
                                            resp_text = str(output_item.content)
                                        break
                            else:
                                # No message output found
                                resp_text = "No message output in response"
                        else:
                            # Try standard extraction
                            if hasattr(last_output, "content"):
                                if isinstance(last_output.content, list) and len(last_output.content) > 0:
                                    resp_text = last_output.content[0].text.strip()
                                else:
                                    resp_text = str(last_output.content)
                            elif hasattr(last_output, "text"):
                                resp_text = last_output.text.strip()
                            else:
                                resp_text = str(last_output)
                    except Exception as e:
                        logger.warning(f"Failed to extract response text: {e}")
                        resp_text = str(resp)
                else:
                    resp_text = str(resp)
            except asyncio.TimeoutError:
                return {
                    "success": False,
                    "message": "Responses-API test timed out after 30 s",
                    "latency": 30.0,
                    "error_type": "timeout",
                    "provider": provider,
                    "model": model,
                }
        else:
            # Chat Completions fallback
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
                return {
                    "success": False,
                    "message": "Chat test timed out after 30 s",
                    "latency": 30.0,
                    "error_type": "timeout",
                    "provider": provider,
                    "model": model,
                }

            resp_text = (
                resp.choices[0].message.content.strip()
                if hasattr(resp, "choices")
                else str(resp)
            )

        # ------------------------------------------------------------------ #
        latency = round(time.time() - start, 3)
        return {
            "success": "test" in resp_text.lower(),
            "message": "Model configuration test completed",
            "latency": latency,
            "response_preview": resp_text[:100]
            + ("…" if len(resp_text) > 100 else ""),
            "provider": provider,
            "model": model,
            "configuration": {
                "temperature": temperature,
                "max_tokens": max_tokens,
                "use_responses_api": use_responses,
            },
        }

    except Exception as exc:  # pragma: no cover
        latency = round(time.time() - start, 3)
        msg = str(exc).lower()
        if any(k in msg for k in ("api key", "unauthorized")):
            err_type = "authentication"
            friendly = "Authentication failed – check your API key"
        elif any(k in msg for k in ("not found", "invalid")):
            err_type = "invalid_model"
            friendly = f"Invalid model: {model}"
        elif any(k in msg for k in ("timeout", "connection")):
            err_type = "connection"
            friendly = "Connection failed – verify endpoint & network"
        else:
            err_type = "unknown"
            friendly = f"Test failed: {exc}"

        logger.warning("Configuration test failed: %s", exc)
        return {
            "success": False,
            "message": friendly,
            "latency": latency,
            "error_type": err_type,
            "error_details": str(exc),
            "provider": provider,
            "model": model,
        }
