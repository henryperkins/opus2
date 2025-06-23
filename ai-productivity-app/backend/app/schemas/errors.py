# backend/app/schemas/errors.py
"""Standardized error schemas and codes for consistent API responses."""
from datetime import datetime
from enum import Enum
from typing import Any, List, Optional

from fastapi import HTTPException, status
from pydantic import BaseModel, Field


class AuthErrorCode(str, Enum):
    """Authentication-specific error codes."""
    BAD_CREDENTIALS = "BAD_CREDENTIALS"
    INACTIVE_ACCOUNT = "INACTIVE_ACCOUNT"
    INVITE_REQUIRED = "INVITE_REQUIRED"
    USERNAME_EXISTS = "USERNAME_EXISTS"
    EMAIL_EXISTS = "EMAIL_EXISTS"
    REGISTRATION_CONFLICT = "REGISTRATION_CONFLICT"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    TOKEN_INVALID = "TOKEN_INVALID"
    SESSION_INVALID = "SESSION_INVALID"
    RATE_LIMITED = "RATE_LIMITED"


class ValidationErrorCode(str, Enum):
    """Validation-specific error codes."""
    FIELD_REQUIRED = "FIELD_REQUIRED"
    FIELD_TOO_LONG = "FIELD_TOO_LONG"
    FIELD_TOO_SHORT = "FIELD_TOO_SHORT"
    INVALID_FORMAT = "INVALID_FORMAT"
    PATH_NOT_ALLOWED = "PATH_NOT_ALLOWED"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    UNSUPPORTED_FILE_TYPE = "UNSUPPORTED_FILE_TYPE"


class SystemErrorCode(str, Enum):
    """System-level error codes."""
    DATABASE_ERROR = "DATABASE_ERROR"
    EXTERNAL_SERVICE_ERROR = "EXTERNAL_SERVICE_ERROR"
    RATE_LIMIT_ERROR = "RATE_LIMIT_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"


class ErrorDetail(BaseModel):
    """Detailed error information."""
    field: Optional[str] = Field(
        None, description="Field that caused the error"
    )
    reason: str = Field(..., description="Human-readable error reason")
    value: Optional[Any] = Field(
        None, description="The invalid value (sanitized)"
    )


class ErrorResponse(BaseModel):
    """Standardized error response format."""
    error_code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[List[ErrorDetail]] = Field(
        None, description="Additional error details"
    )
    request_id: Optional[str] = Field(
        None, description="Request correlation ID"
    )
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "error_code": "BAD_CREDENTIALS",
                "message": "Invalid credentials",
                "request_id": "req_12345",
                "timestamp": "2024-06-22T10:30:00Z"
            }
        }


def create_error_response(
    error_code: str,
    message: str,
    details: Optional[List[ErrorDetail]] = None,
    request_id: Optional[str] = None
) -> dict:
    """Create a standardized error response dictionary."""
    response = ErrorResponse(
        error_code=error_code,
        message=message,
        details=details,
        request_id=request_id
    )
    return response.model_dump(exclude_none=True)


# Helper functions for common error scenarios
def auth_error_response(code: AuthErrorCode, message: str) -> HTTPException:
    """Create an authentication error with proper headers."""
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=message,
        headers={"X-Error-Code": code.value}
    )


def validation_error_response(
    code: ValidationErrorCode,
    message: str,
    field: Optional[str] = None,
    value: Optional[Any] = None
) -> HTTPException:
    """Create a validation error with details."""
    details = []
    if field:
        details.append(ErrorDetail(
            field=field,
            reason=message,
            value=str(value) if value is not None else None
        ))

    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=create_error_response(
            error_code=code.value,
            message=message,
            details=details if details else None
        )
    )
