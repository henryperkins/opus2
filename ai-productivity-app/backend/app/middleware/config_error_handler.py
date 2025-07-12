"""
Enhanced error handling middleware for configuration-related errors.
Provides clear, actionable error messages.
"""

import logging
from typing import Callable
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import json

logger = logging.getLogger(__name__)


class ConfigurationErrorMiddleware(BaseHTTPMiddleware):
    """
    Middleware that intercepts configuration-related errors and provides
    clear, actionable error messages to the frontend.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            response = await call_next(request)

            if request.url.path.startswith("/api/v1/ai-config") and response.status_code >= 400:
                # Only read the body if we might want to enhance a dict error message
                content_type = response.headers.get("content-type", "")
                is_json = "application/json" in content_type

                if is_json:
                    # Peek at the body's opening char to determine type without exhausting the response.
                    import asyncio
                    import hashlib

                    # Create a buffer to intercept the stream
                    body = b""
                    async for chunk in response.body_iterator:
                        body += chunk

                    # Try basic JSON parse
                    error_data = None
                    try:
                        loaded = json.loads(body.decode())
                        if isinstance(loaded, dict):
                            error_data = loaded
                    except Exception:
                        error_data = None

                    if error_data is not None:
                        # Dict error body, enhance as before
                        if response.status_code == 422:
                            original_detail = error_data.get("detail", "")
                            enhanced_detail = self._enhance_validation_error(original_detail)
                            suggestions = self._get_error_suggestions(enhanced_detail)

                            if suggestions:
                                error_data["detail"] = enhanced_detail
                                error_data["error_type"] = "validation_error"
                                error_data["suggestions"] = suggestions
                            else:
                                error_data["detail"] = (
                                    "Configuration validation failed. Please check that all required fields are provided and valid."
                                )
                                error_data["error_type"] = "validation_error"
                                error_data["suggestions"] = [
                                    "Ensure the selected preset is compatible with your provider",
                                    "Check that all required environment variables are configured",
                                    "Try using a different preset or manually configuring settings"
                                ]
                            clean_headers = {
                                k: v
                                for k, v in response.headers.items()
                                if k.lower() != "content-length"
                            }
                            return JSONResponse(
                                status_code=422,
                                content=error_data,
                                headers=clean_headers,
                            )

                        elif response.status_code == 400:
                            error_data["error_type"] = "configuration_error"
                            error_data["suggestions"] = [
                                "Check that your environment variables match the selected provider",
                                "Ensure API keys are configured for the selected provider",
                                "Try using a different preset or model"
                            ]
                            clean_headers = {
                                k: v
                                for k, v in response.headers.items()
                                if k.lower() != "content-length"
                            }
                            return JSONResponse(
                                status_code=400,
                                content=error_data,
                                headers=clean_headers,
                            )
                        else:
                            # For other error codes, just pass through as before
                            clean_headers = {
                                k: v
                                for k, v in response.headers.items()
                                if k.lower() != "content-length"
                            }
                            return Response(
                                content=body,
                                status_code=response.status_code,
                                headers=clean_headers,
                                media_type=response.media_type,
                            )
                    else:
                        # If the error body is not a dict (e.g., Pydantic error list), yield the original response untouched
                        return Response(
                            content=body,
                            status_code=response.status_code,
                            headers=response.headers,
                            media_type=response.media_type,
                        )

                # For non-JSON or anything else, pass through untouched
                return response

            return response

        except Exception:
            logger.exception("Error in configuration error middleware")
            return JSONResponse(
                status_code=500,
                content={
                    "detail": "Internal server error",
                    "error_type": "internal_error"
                }
            )

    def _enhance_validation_error(self, detail: str) -> str:
        """
        Enhance validation error messages to be more user-friendly.
        """
        # Map common validation errors to clearer messages
        error_mappings = {
            "Field required; Field required": "Missing required configuration fields. The selected preset may not be compatible with your current provider.",
            "Field required": "Missing required configuration field.",
            "ensure this value is greater than or equal to": "Invalid parameter value - outside allowed range.",
            "ensure this value is less than or equal to": "Invalid parameter value - outside allowed range.",
            "Azure provider requires an explicit model_id": "Please select a model when using Azure OpenAI.",
            "Configuration validation failed": "The selected configuration is not valid for the current provider.",
        }

        for pattern, replacement in error_mappings.items():
            if pattern in detail:
                return replacement

        # Clean up Pydantic error messages
        if "value is not a valid" in detail:
            return "Invalid configuration value provided."

        return detail

    def _get_error_suggestions(self, error_message: str) -> list[str]:
        """
        Provide helpful suggestions based on the error message.
        """
        suggestions = []

        if "preset may not be compatible" in error_message:
            suggestions.extend([
                "Try selecting a different preset",
                "Ensure your environment is configured for the correct provider",
                "Use the 'balanced' preset which works across all providers"
            ])

        elif "Azure" in error_message:
            suggestions.extend([
                "Ensure AZURE_OPENAI_ENDPOINT is configured",
                "Ensure AZURE_OPENAI_API_KEY is configured",
                "Select an Azure-compatible model like 'gpt-4.1' or 'o3'"
            ])

        elif "OpenAI" in error_message:
            suggestions.extend([
                "Ensure OPENAI_API_KEY is configured",
                "Select an OpenAI model like 'gpt-4o' or 'gpt-4o-mini'"
            ])

        elif "Anthropic" in error_message or "Claude" in error_message:
            suggestions.extend([
                "Ensure ANTHROPIC_API_KEY is configured",
                "Select a Claude model like 'claude-3-5-sonnet-20241022'",
                "Use claude_extended_thinking instead of enable_reasoning for Claude models"
            ])

        elif "parameter value" in error_message:
            suggestions.extend([
                "Check that temperature is between 0.0 and 2.0",
                "Check that max_tokens is between 64 and 16000",
                "Check that top_p is between 0.0 and 1.0"
            ])

        return suggestions
