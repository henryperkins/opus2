# Service layer for prompt template operations
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from typing import List, Optional, Dict, Any
from fastapi import HTTPException

from app.models.prompt import PromptTemplate
from app.models.user import User
from app.schemas.prompt import (
    PromptTemplateCreate,
    PromptTemplateUpdate,
    PromptTemplateResponse,
    PromptDuplicateRequest,
    PromptExecuteRequest,
    PromptExecuteResponse,
)
from app.schemas.generation import UnifiedModelConfig
import logging

logger = logging.getLogger(__name__)


class PromptService:
    """Service for managing prompt templates"""

    def __init__(self, db: Session):
        self.db = db

    async def create_template(
        self, template_data: PromptTemplateCreate, user_id: int
    ) -> PromptTemplate:
        """Create a new prompt template"""

        # Convert model preferences to dict
        llm_prefs = (
            template_data.llm_preferences.model_dump(exclude_unset=True, by_alias=True)
            if template_data.llm_preferences
            else {}
        )

        # Convert variables to dict format
        variables = [
            var.model_dump(exclude_unset=True, by_alias=True)
            for var in template_data.variables
        ]

        template = PromptTemplate(
            name=template_data.name,
            description=template_data.description,
            category=template_data.category,
            system_prompt=template_data.system_prompt,
            user_prompt_template=template_data.user_prompt_template,
            variables=variables,
            llm_preferences=llm_prefs,
            user_id=user_id,
            is_public=template_data.is_public,
            usage_count=0,
        )

        self.db.add(template)

        try:
            self.db.commit()
            self.db.refresh(template)
            logger.info(f"Created prompt template {template.id} for user {user_id}")
            return template
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create prompt template: {e}")
            raise HTTPException(status_code=500, detail="Failed to create template")

    async def get_template(
        self, template_id: int, user_id: int
    ) -> Optional[PromptTemplate]:
        """Get a specific template by ID"""
        template = (
            self.db.query(PromptTemplate)
            .filter(
                PromptTemplate.id == template_id,
                or_(
                    PromptTemplate.user_id == user_id,
                    PromptTemplate.is_public == True,
                    PromptTemplate.is_default == True,
                ),
            )
            .first()
        )

        if not template:
            raise HTTPException(status_code=404, detail="Template not found")

        return template

    async def get_templates(
        self,
        user_id: int,
        category: Optional[str] = None,
        is_public: Optional[bool] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[List[PromptTemplate], int]:
        """Get templates with filtering and pagination"""

        # Base query - user's templates plus public ones
        query = self.db.query(PromptTemplate).filter(
            or_(
                PromptTemplate.user_id == user_id,
                PromptTemplate.is_public == True,
                PromptTemplate.is_default == True,
            )
        )

        # Apply filters
        if category:
            query = query.filter(PromptTemplate.category == category)

        if is_public is not None:
            query = query.filter(PromptTemplate.is_public == is_public)

        if search:
            search_filter = or_(
                PromptTemplate.name.ilike(f"%{search}%"),
                PromptTemplate.description.ilike(f"%{search}%"),
            )
            query = query.filter(search_filter)

        # Get total count
        total = query.count()

        # Apply pagination and ordering
        templates = (
            query.order_by(
                PromptTemplate.is_default.desc(),  # Default templates first
                PromptTemplate.usage_count.desc(),  # Then by usage
                PromptTemplate.updated_at.desc(),  # Then by recency
            )
            .offset(skip)
            .limit(limit)
            .all()
        )

        return templates, total

    async def update_template(
        self, template_id: int, template_data: PromptTemplateUpdate, user_id: int
    ) -> PromptTemplate:
        """Update an existing template"""

        template = (
            self.db.query(PromptTemplate)
            .filter(
                PromptTemplate.id == template_id,
                PromptTemplate.user_id == user_id,
                PromptTemplate.is_default == False,  # Can't edit default templates
            )
            .first()
        )

        if not template:
            raise HTTPException(
                status_code=404, detail="Template not found or not editable"
            )

        # Update fields
        update_data = template_data.model_dump(exclude_unset=True, by_alias=True)

        for field, value in update_data.items():
            if field == "llmPreferences" and value:
                # Convert model preferences
                template.llm_preferences = value
            elif field == "variables" and value is not None:
                # Convert variables list
                template.variables = [
                    var.model_dump(exclude_unset=True, by_alias=True) for var in value
                ]
            elif hasattr(template, field):
                setattr(template, field, value)

        try:
            self.db.commit()
            self.db.refresh(template)
            logger.info(f"Updated prompt template {template_id}")
            return template
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to update prompt template {template_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to update template")

    async def delete_template(self, template_id: int, user_id: int) -> bool:
        """Delete a template"""

        template = (
            self.db.query(PromptTemplate)
            .filter(
                PromptTemplate.id == template_id,
                PromptTemplate.user_id == user_id,
                PromptTemplate.is_default == False,  # Can't delete default templates
            )
            .first()
        )

        if not template:
            raise HTTPException(
                status_code=404, detail="Template not found or not deletable"
            )

        try:
            self.db.delete(template)
            self.db.commit()
            logger.info(f"Deleted prompt template {template_id}")
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to delete prompt template {template_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to delete template")

    async def duplicate_template(
        self, template_id: int, duplicate_data: PromptDuplicateRequest, user_id: int
    ) -> PromptTemplate:
        """Duplicate an existing template"""

        # Get the original template
        original = await self.get_template(template_id, user_id)

        # Create new template with modified data
        new_name = duplicate_data.name or f"{original.name} (Copy)"
        new_category = duplicate_data.category or original.category
        new_is_public = (
            duplicate_data.is_public if duplicate_data.is_public is not None else False
        )

        new_template = PromptTemplate(
            name=new_name,
            description=original.description,
            category=new_category,
            system_prompt=original.system_prompt,
            user_prompt_template=original.user_prompt_template,
            variables=original.variables.copy() if original.variables else [],
            llm_preferences=(
                original.llm_preferences.copy() if original.llm_preferences else {}
            ),
            user_id=user_id,
            is_public=new_is_public,
            is_default=False,  # Duplicates are never default
            usage_count=0,
        )

        self.db.add(new_template)

        try:
            self.db.commit()
            self.db.refresh(new_template)
            logger.info(
                f"Duplicated prompt template {template_id} to {new_template.id}"
            )
            return new_template
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to duplicate prompt template {template_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to duplicate template")

    async def execute_template(
        self, template_id: int, execute_data: PromptExecuteRequest, user_id: int
    ) -> PromptExecuteResponse:
        """Execute a template with provided variables"""

        template = await self.get_template(template_id, user_id)

        try:
            # Render the template with variables
            rendered_prompt = template.render_prompt(execute_data.variables)

            # Merge model preferences with ModelConfiguration defaults
            final_model_prefs = (
                template.llm_preferences.copy() if template.llm_preferences else {}
            )
            if execute_data.llm_overrides:
                override_dict = execute_data.llm_overrides.model_dump(
                    exclude_unset=True, by_alias=True
                )
                final_model_prefs.update(override_dict)

            # Get runtime config using unified configuration service
            from app.services.unified_config_service import UnifiedConfigService

            unified_service = UnifiedConfigService(self.db)
            current_config = unified_service.get_current_config()

            # Get the model configuration for the specified model
            model_id = final_model_prefs.get("model_id") or current_config.model_id
            if model_id:
                model_info = unified_service.get_model_info(model_id)
                if model_info:
                    # Merge current config with template preferences and overrides
                    config_dict = current_config.model_dump(exclude_unset=True)
                    config_dict.update(final_model_prefs)
                    final_model_prefs = config_dict

            # Increment usage count
            template.increment_usage()
            self.db.commit()

            return PromptExecuteResponse(
                system_prompt=template.system_prompt,
                user_prompt=rendered_prompt,
                llm_preferences=UnifiedModelConfig(**final_model_prefs),
            )

        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Failed to execute prompt template {template_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to execute template")

    async def get_template_stats(
        self, template_id: int, user_id: int
    ) -> Dict[str, Any]:
        """Get statistics for a template"""

        template = await self.get_template(template_id, user_id)

        return {
            "template_id": template.id,
            "usage_count": template.usage_count,
            "last_used": template.updated_at if template.usage_count > 0 else None,
            "avg_rating": None,  # TODO: Implement rating system
            "total_ratings": 0,  # TODO: Implement rating system
        }

    async def get_categories(self, user_id: int) -> List[str]:
        """Get all categories used by user's templates"""

        categories = (
            self.db.query(PromptTemplate.category)
            .filter(
                or_(
                    PromptTemplate.user_id == user_id,
                    PromptTemplate.is_public == True,
                    PromptTemplate.is_default == True,
                )
            )
            .distinct()
            .all()
        )

        return [cat[0] for cat in categories if cat[0]]

    async def seed_default_templates(self) -> None:
        """Seed the database with default templates"""

        # Check if defaults already exist
        existing = (
            self.db.query(PromptTemplate)
            .filter(PromptTemplate.is_default == True)
            .first()
        )

        if existing:
            return  # Already seeded

        default_templates = [
            {
                "name": "Code Explainer",
                "description": "Explains code functionality in detail",
                "category": "Documentation",
                "system_prompt": "You are an expert programmer who excels at explaining code clearly and concisely.",
                "user_prompt_template": "Please explain the following {{language}} code:\n\n```{{language}}\n{{code}}\n```\n\nFocus on:\n1. Overall purpose\n2. Key logic flow\n3. Important details\n{{additionalContext}}",
                "variables": [
                    {
                        "name": "language",
                        "description": "Programming language",
                        "required": True,
                    },
                    {
                        "name": "code",
                        "description": "Code to explain",
                        "required": True,
                    },
                    {
                        "name": "additionalContext",
                        "description": "Additional context or specific questions",
                        "required": False,
                    },
                ],
                "is_default": True,
                "is_public": True,
                "user_id": 1,  # Assign to admin user
            },
            {
                "name": "Test Generator",
                "description": "Generates comprehensive unit tests",
                "category": "Testing",
                "system_prompt": "You are a testing expert who writes comprehensive, well-structured unit tests.",
                "user_prompt_template": "Generate {{testFramework}} unit tests for the following {{language}} code:\n\n```{{language}}\n{{code}}\n```\n\nRequirements:\n- Cover all functions/methods\n- Include edge cases\n- Add helpful test descriptions\n{{additionalRequirements}}",
                "variables": [
                    {
                        "name": "language",
                        "description": "Programming language",
                        "required": True,
                    },
                    {
                        "name": "testFramework",
                        "description": "Test framework (e.g., Jest, pytest)",
                        "required": True,
                    },
                    {"name": "code", "description": "Code to test", "required": True},
                    {
                        "name": "additionalRequirements",
                        "description": "Additional test requirements",
                        "required": False,
                    },
                ],
                "llm_preferences": {"temperature": 0.3, "maxTokens": 2048},
                "is_default": True,
                "is_public": True,
                "user_id": 1,
            },
        ]

        for template_data in default_templates:
            template = PromptTemplate(**template_data)
            self.db.add(template)

        try:
            self.db.commit()
            logger.info("Seeded default prompt templates")
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to seed default templates: {e}")
