# Pydantic schemas for prompt templates
from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Optional, Any
from datetime import datetime
import re


class PromptVariable(BaseModel):
    """Schema for prompt template variables"""

    name: str = Field(..., description="Variable name")
    description: Optional[str] = Field(None, description="Variable description")
    required: bool = Field(False, description="Whether variable is required")
    default_value: Optional[str] = Field(
        None, description="Default value for variable", alias="defaultValue"
    )

    model_config = {"populate_by_name": True}

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", v):
            raise ValueError("Variable name must be a valid identifier")
        return v


class PromptTemplateBase(BaseModel):
    """Base schema for prompt templates"""

    name: str = Field(..., min_length=1, max_length=255, description="Template name")
    description: Optional[str] = Field(None, description="Template description")
    category: str = Field("Custom", description="Template category")
    system_prompt: Optional[str] = Field(
        None, description="System prompt for AI", alias="systemPrompt"
    )
    user_prompt_template: str = Field(
        ...,
        min_length=1,
        description="User prompt template",
        alias="userPromptTemplate",
    )
    variables: List[PromptVariable] = Field(
        default_factory=list, description="Template variables"
    )
    llm_preferences: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Model preferences", alias="llmPreferences"
    )
    is_public: bool = Field(
        False, description="Whether template is public", alias="isPublic"
    )

    model_config = {"populate_by_name": True, "protected_namespaces": ()}

    @field_validator("category")
    @classmethod
    def validate_category(cls, v):
        valid_categories = [
            "Code Generation",
            "Code Review",
            "Documentation",
            "Testing",
            "Debugging",
            "Refactoring",
            "Architecture",
            "Custom",
        ]
        if v not in valid_categories:
            raise ValueError(f"Category must be one of: {', '.join(valid_categories)}")
        return v


class PromptTemplateCreate(PromptTemplateBase):
    """Schema for creating prompt templates"""

    pass


class PromptTemplateUpdate(BaseModel):
    """Schema for updating prompt templates"""

    name: Optional[str] = Field(
        None, min_length=1, max_length=255, description="Template name"
    )
    description: Optional[str] = Field(None, description="Template description")
    category: Optional[str] = Field(None, description="Template category")
    system_prompt: Optional[str] = Field(
        None, description="System prompt for AI", alias="systemPrompt"
    )
    user_prompt_template: Optional[str] = Field(
        None,
        min_length=1,
        description="User prompt template",
        alias="userPromptTemplate",
    )
    variables: Optional[List[PromptVariable]] = Field(
        None, description="Template variables"
    )
    llm_preferences: Optional[Dict[str, Any]] = Field(
        None, description="Model preferences", alias="llmPreferences"
    )
    is_public: Optional[bool] = Field(
        None, description="Whether template is public", alias="isPublic"
    )

    model_config = {"populate_by_name": True, "protected_namespaces": ()}

    @field_validator("category")
    @classmethod
    def validate_category(cls, v):
        if v is None:
            return v
        valid_categories = [
            "Code Generation",
            "Code Review",
            "Documentation",
            "Testing",
            "Debugging",
            "Refactoring",
            "Architecture",
            "Custom",
        ]
        if v not in valid_categories:
            raise ValueError(f"Category must be one of: {', '.join(valid_categories)}")
        return v


class PromptTemplateResponse(PromptTemplateBase):
    """Schema for prompt template responses"""

    id: int = Field(..., description="Template ID")
    user_id: int = Field(..., description="Owner user ID", alias="userId")
    is_default: bool = Field(
        False, description="Whether template is a default template", alias="isDefault"
    )
    usage_count: int = Field(
        0, description="Number of times template was used", alias="usageCount"
    )
    created_at: datetime = Field(
        ..., description="Creation timestamp", alias="createdAt"
    )
    updated_at: datetime = Field(
        ..., description="Last update timestamp", alias="updatedAt"
    )

    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
        "protected_namespaces": (),
    }


class PromptTemplateList(BaseModel):
    """Schema for listing prompt templates"""

    templates: List[PromptTemplateResponse] = Field(
        ..., description="List of templates"
    )
    total: int = Field(..., description="Total number of templates")
    page: int = Field(1, description="Current page")
    page_size: int = Field(50, description="Page size", alias="pageSize")

    model_config = {"populate_by_name": True}


class PromptExecuteRequest(BaseModel):
    """Schema for executing prompt templates"""

    template_id: int = Field(..., description="Template ID", alias="templateId")
    variables: Dict[str, str] = Field(
        default_factory=dict, description="Variable values"
    )
    llm_overrides: Optional[Dict[str, Any]] = Field(
        None, description="Model preference overrides", alias="llmOverrides"
    )

    model_config = {"populate_by_name": True, "protected_namespaces": ()}


class PromptExecuteResponse(BaseModel):
    """Schema for prompt execution response"""

    system_prompt: Optional[str] = Field(
        None, description="System prompt", alias="systemPrompt"
    )
    user_prompt: str = Field(
        ..., description="Rendered user prompt", alias="userPrompt"
    )
    llm_preferences: Dict[str, Any] = Field(
        ..., description="Final model preferences", alias="llmPreferences"
    )

    model_config = {"populate_by_name": True, "protected_namespaces": ()}


class PromptDuplicateRequest(BaseModel):
    """Schema for duplicating prompt templates"""

    name: Optional[str] = Field(None, description="New template name")
    category: Optional[str] = Field(None, description="New template category")
    is_public: Optional[bool] = Field(
        None,
        description="Whether duplicated template should be public",
        alias="isPublic",
    )

    model_config = {"populate_by_name": True}


class PromptShareRequest(BaseModel):
    """Schema for sharing prompt templates"""

    user_ids: List[int] = Field(
        ..., description="List of user IDs to share with", alias="userIds"
    )
    permissions: str = Field("read", description="Permission level (read/write)")

    model_config = {"populate_by_name": True}

    @field_validator("permissions")
    @classmethod
    def validate_permissions(cls, v):
        if v not in ["read", "write"]:
            raise ValueError("Permissions must be 'read' or 'write'")
        return v


class PromptStatsResponse(BaseModel):
    """Schema for prompt template statistics"""

    template_id: int = Field(..., description="Template ID", alias="templateId")
    usage_count: int = Field(..., description="Usage count", alias="usageCount")
    last_used: Optional[datetime] = Field(
        None, description="Last used timestamp", alias="lastUsed"
    )
    avg_rating: Optional[float] = Field(
        None, description="Average rating", alias="avgRating"
    )
    total_ratings: int = Field(
        0, description="Total number of ratings", alias="totalRatings"
    )

    model_config = {"populate_by_name": True}
