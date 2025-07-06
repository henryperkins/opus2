# backend/app/models/feedback.py
"""User feedback model for RAG responses."""

from datetime import datetime
from typing import Optional

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship

from .base import Base


class UserFeedback(Base):
    """User feedback on AI assistant responses."""
    
    __tablename__ = "user_feedback"
    
    id = Column(Integer, primary_key=True)
    
    # Reference to the chat message being rated
    message_id = Column(Integer, ForeignKey("chat_messages.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"), nullable=False)
    
    # Feedback details
    rating = Column(Integer, nullable=False)  # 1-5 scale or thumbs up/down (-1, 1)
    helpful = Column(Boolean, nullable=True)  # Explicit helpful/not helpful flag
    comments = Column(Text, nullable=True)  # Optional user comments
    
    # Feedback categories (what was good/bad)
    accuracy_rating = Column(Integer, nullable=True)  # 1-5 for accuracy
    clarity_rating = Column(Integer, nullable=True)   # 1-5 for clarity
    completeness_rating = Column(Integer, nullable=True)  # 1-5 for completeness
    
    # Context about the response
    response_length = Column(Integer, nullable=True)  # Length of response
    had_code_examples = Column(Boolean, default=False)
    had_citations = Column(Boolean, default=False)
    rag_was_used = Column(Boolean, default=False)
    rag_confidence = Column(Float, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    message = relationship("ChatMessage", back_populates="feedback")
    user = relationship("User")
    session = relationship("ChatSession")
    
    def __repr__(self):
        return f"<UserFeedback(id={self.id}, message_id={self.message_id}, rating={self.rating})>"


class FeedbackSummary(Base):
    """Aggregated feedback statistics."""
    
    __tablename__ = "feedback_summaries"
    
    id = Column(Integer, primary_key=True)
    
    # Time period for this summary
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    period_type = Column(String(20), nullable=False)  # daily, weekly, monthly
    
    # Aggregate metrics
    total_feedback_count = Column(Integer, default=0)
    average_rating = Column(Float, nullable=True)
    helpful_percentage = Column(Float, nullable=True)
    
    # Breakdown by categories
    avg_accuracy = Column(Float, nullable=True)
    avg_clarity = Column(Float, nullable=True)
    avg_completeness = Column(Float, nullable=True)
    
    # RAG-specific metrics
    rag_responses_count = Column(Integer, default=0)
    rag_avg_confidence = Column(Float, nullable=True)
    rag_success_rate = Column(Float, nullable=True)  # % of RAG responses rated positively
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<FeedbackSummary(period={self.period_type}, avg_rating={self.average_rating})>"