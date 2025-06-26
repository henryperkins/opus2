# Router for prompt template management
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.services.prompt_service import PromptService
from app.schemas.prompt import (
    PromptTemplateCreate, PromptTemplateUpdate, PromptTemplateResponse,
    PromptTemplateList, PromptDuplicateRequest, PromptExecuteRequest,
    PromptExecuteResponse, PromptStatsResponse
)
from app.auth.security import limiter
import logging

logger = logging.getLogger(__name__)

# Align with other API routers by using the "/api" prefix so that the
# frontend can reach the endpoints at `/api/prompts/*`.
router = APIRouter(prefix="/api/prompts", tags=["prompts"])


@router.post("/", response_model=PromptTemplateResponse)
@limiter.limit("10/minute")  # Rate limit template creation
async def create_template(
    request: Request,
    template_data: PromptTemplateCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new prompt template"""
    service = PromptService(db)
    template = await service.create_template(template_data, current_user.id)
    return PromptTemplateResponse.from_orm(template)


@router.get("/", response_model=PromptTemplateList)
async def get_templates(
    category: Optional[str] = Query(None, description="Filter by category"),
    is_public: Optional[bool] = Query(None, description="Filter by public/private"),
    search: Optional[str] = Query(None, description="Search templates by name or description"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get prompt templates with filtering and pagination"""
    service = PromptService(db)
    skip = (page - 1) * page_size
    
    templates, total = await service.get_templates(
        user_id=current_user.id,
        category=category,
        is_public=is_public,
        search=search,
        skip=skip,
        limit=page_size
    )
    
    template_responses = [PromptTemplateResponse.from_orm(t) for t in templates]
    
    return PromptTemplateList(
        templates=template_responses,
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/categories", response_model=List[str])
async def get_categories(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all available template categories"""
    service = PromptService(db)
    return await service.get_categories(current_user.id)


@router.get("/{template_id}", response_model=PromptTemplateResponse)
async def get_template(
    template_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific template by ID"""
    service = PromptService(db)
    template = await service.get_template(template_id, current_user.id)
    return PromptTemplateResponse.from_orm(template)


@router.put("/{template_id}", response_model=PromptTemplateResponse)
@limiter.limit("20/minute")  # Rate limit template updates
async def update_template(
    request: Request,
    template_id: int,
    template_data: PromptTemplateUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update an existing template"""
    service = PromptService(db)
    template = await service.update_template(template_id, template_data, current_user.id)
    return PromptTemplateResponse.from_orm(template)


@router.delete("/{template_id}")
async def delete_template(
    template_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a template"""
    service = PromptService(db)
    success = await service.delete_template(template_id, current_user.id)
    return {"success": success, "message": "Template deleted successfully"}


@router.post("/{template_id}/duplicate", response_model=PromptTemplateResponse)
@limiter.limit("5/minute")  # Rate limit duplications
async def duplicate_template(
    request: Request,
    template_id: int,
    duplicate_data: PromptDuplicateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Duplicate an existing template"""
    service = PromptService(db)
    template = await service.duplicate_template(template_id, duplicate_data, current_user.id)
    return PromptTemplateResponse.from_orm(template)


@router.post("/{template_id}/execute", response_model=PromptExecuteResponse)
@limiter.limit("30/minute")  # Rate limit executions
async def execute_template(
    request: Request,
    template_id: int,
    execute_data: PromptExecuteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Execute a template with provided variables"""
    service = PromptService(db)
    return await service.execute_template(template_id, execute_data, current_user.id)


@router.get("/{template_id}/stats", response_model=PromptStatsResponse)
async def get_template_stats(
    template_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get statistics for a template"""
    service = PromptService(db)
    stats = await service.get_template_stats(template_id, current_user.id)
    return PromptStatsResponse(**stats)


@router.post("/seed-defaults")
async def seed_default_templates(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Seed default templates (admin only)"""
    # Note: In a real application, you'd want to restrict this to admin users
    # For now, allowing any authenticated user for development purposes
    service = PromptService(db)
    await service.seed_default_templates()
    return {"success": True, "message": "Default templates seeded successfully"}