# backend/app/routers/feedback.py
"""User feedback API endpoints."""

from typing import List, Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_

from app.database import get_db
from app.models.feedback import UserFeedback, FeedbackSummary
from app.models.chat import ChatMessage
from app.dependencies import get_current_user
from app.models.user import User
from pydantic import BaseModel, Field


# Pydantic models for request/response
class FeedbackCreate(BaseModel):
    """Create feedback for a message."""
    message_id: int
    rating: int = Field(..., ge=-1, le=5)  # -1 for thumbs down, 1 for thumbs up, or 1-5 scale
    helpful: Optional[bool] = None
    comments: Optional[str] = None
    accuracy_rating: Optional[int] = Field(None, ge=1, le=5)
    clarity_rating: Optional[int] = Field(None, ge=1, le=5)
    completeness_rating: Optional[int] = Field(None, ge=1, le=5)


class FeedbackResponse(BaseModel):
    """Feedback response model."""
    id: int
    message_id: int
    rating: int
    helpful: Optional[bool]
    comments: Optional[str]
    accuracy_rating: Optional[int]
    clarity_rating: Optional[int]
    completeness_rating: Optional[int]
    created_at: datetime
    
    class Config:
        from_attributes = True


class FeedbackStats(BaseModel):
    """Aggregated feedback statistics."""
    total_count: int
    average_rating: Optional[float]
    helpful_percentage: Optional[float]
    accuracy_avg: Optional[float]
    clarity_avg: Optional[float]
    completeness_avg: Optional[float]
    rag_success_rate: Optional[float]


router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.post("/", response_model=FeedbackResponse)
async def create_feedback(
    feedback_data: FeedbackCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Submit feedback for an assistant response."""
    
    # Verify the message exists and belongs to the user
    message_query = select(ChatMessage).where(
        ChatMessage.id == feedback_data.message_id,
        ChatMessage.role == "assistant"  # Only allow feedback on assistant messages
    )
    message = db.execute(message_query).scalar_one_or_none()
    
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found or not an assistant message"
        )
    
    # Check if user has access to this message (through session ownership)
    # This would typically involve checking session/project permissions
    # For now, we'll allow any authenticated user to provide feedback
    
    # Check if feedback already exists for this message from this user
    existing_feedback = db.execute(
        select(UserFeedback).where(
            UserFeedback.message_id == feedback_data.message_id,
            UserFeedback.user_id == current_user.id
        )
    ).scalar_one_or_none()
    
    if existing_feedback:
        # Update existing feedback
        for field, value in feedback_data.model_dump(exclude_unset=True).items():
            if field != "message_id":  # Don't update message_id
                setattr(existing_feedback, field, value)
        existing_feedback.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(existing_feedback)
        return existing_feedback
    
    # Create new feedback
    feedback = UserFeedback(
        message_id=feedback_data.message_id,
        user_id=current_user.id,
        session_id=message.session_id,
        rating=feedback_data.rating,
        helpful=feedback_data.helpful,
        comments=feedback_data.comments,
        accuracy_rating=feedback_data.accuracy_rating,
        clarity_rating=feedback_data.clarity_rating,
        completeness_rating=feedback_data.completeness_rating,
        
        # Extract context from the message
        response_length=len(message.content),
        had_code_examples=bool(message.code_snippets),
        had_citations=bool(message.referenced_chunks),
        rag_was_used=message.rag_used,
        rag_confidence=float(message.rag_confidence) if message.rag_confidence else None
    )
    
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    
    return feedback


@router.get("/message/{message_id}", response_model=List[FeedbackResponse])
async def get_message_feedback(
    message_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get feedback for a specific message."""
    
    feedback_query = select(UserFeedback).where(
        UserFeedback.message_id == message_id
    )
    
    # If user is admin or the message owner, show all feedback
    # Otherwise, show only their own feedback
    if not current_user.is_admin:  # Assuming there's an is_admin field
        feedback_query = feedback_query.where(UserFeedback.user_id == current_user.id)
    
    feedback_list = db.execute(feedback_query).scalars().all()
    return feedback_list


@router.get("/stats", response_model=FeedbackStats)
async def get_feedback_stats(
    days: int = 30,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get aggregated feedback statistics."""
    
    # Calculate date range
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    # Base query for the time period
    base_query = select(UserFeedback).where(
        UserFeedback.created_at >= start_date,
        UserFeedback.created_at <= end_date
    )
    
    # If not admin, filter to user's own feedback
    if not getattr(current_user, 'is_admin', False):
        base_query = base_query.where(UserFeedback.user_id == current_user.id)
    
    feedback_list = db.execute(base_query).scalars().all()
    
    if not feedback_list:
        return FeedbackStats(
            total_count=0,
            average_rating=None,
            helpful_percentage=None,
            accuracy_avg=None,
            clarity_avg=None,
            completeness_avg=None,
            rag_success_rate=None
        )
    
    total_count = len(feedback_list)
    
    # Calculate averages
    ratings = [f.rating for f in feedback_list if f.rating is not None]
    average_rating = sum(ratings) / len(ratings) if ratings else None
    
    helpful_count = sum(1 for f in feedback_list if f.helpful is True)
    helpful_percentage = (helpful_count / total_count * 100) if total_count > 0 else None
    
    accuracy_ratings = [f.accuracy_rating for f in feedback_list if f.accuracy_rating is not None]
    accuracy_avg = sum(accuracy_ratings) / len(accuracy_ratings) if accuracy_ratings else None
    
    clarity_ratings = [f.clarity_rating for f in feedback_list if f.clarity_rating is not None]
    clarity_avg = sum(clarity_ratings) / len(clarity_ratings) if clarity_ratings else None
    
    completeness_ratings = [f.completeness_rating for f in feedback_list if f.completeness_rating is not None]
    completeness_avg = sum(completeness_ratings) / len(completeness_ratings) if completeness_ratings else None
    
    # RAG success rate (positive feedback on RAG responses)
    rag_responses = [f for f in feedback_list if f.rag_was_used]
    if rag_responses:
        rag_positive = sum(1 for f in rag_responses if f.helpful is True or f.rating > 0)
        rag_success_rate = (rag_positive / len(rag_responses) * 100)
    else:
        rag_success_rate = None
    
    return FeedbackStats(
        total_count=total_count,
        average_rating=average_rating,
        helpful_percentage=helpful_percentage,
        accuracy_avg=accuracy_avg,
        clarity_avg=clarity_avg,
        completeness_avg=completeness_avg,
        rag_success_rate=rag_success_rate
    )


@router.delete("/{feedback_id}")
async def delete_feedback(
    feedback_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete user's own feedback."""
    
    feedback = db.execute(
        select(UserFeedback).where(
            UserFeedback.id == feedback_id,
            UserFeedback.user_id == current_user.id
        )
    ).scalar_one_or_none()
    
    if not feedback:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feedback not found or not authorized to delete"
        )
    
    db.delete(feedback)
    db.commit()
    
    return {"detail": "Feedback deleted successfully"}