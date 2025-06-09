"""Search history model stores executed search queries per user."""

from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey, Index
from sqlalchemy.orm import relationship
from datetime import datetime

from .base import Base, TimestampMixin


class SearchHistory(Base, TimestampMixin):
    """Stores a single executed search query for a user.

    The table is append-only – one row per search execution so that we can
    later build analytics around popular queries, etc.  For suggestions we
    mainly read the most recent *n* rows per user.
    """

    __tablename__ = "search_history"
    __table_args__ = (
        Index("idx_search_history_user_created", "user_id", "created_at"),
        Index("idx_search_history_query", "query_text"),
        {
            "extend_existing": True,
        },
    )

    id = Column(Integer, primary_key=True)

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Raw query string the user submitted (before any server-side expansion)
    query_text = Column(String(255), nullable=False)

    # Optional structured data – search filters, project ids, etc.
    filters = Column(JSON, nullable=True)
    project_ids = Column(JSON, nullable=True)

    # Relationship back to user (lazy=False to avoid additional SELECT when not needed)
    user = relationship("User", back_populates="search_history", lazy=False)

    def __repr__(self) -> str:  # noqa: D401
        return (
            "<SearchHistory(id={0}, user_id={1}, query='{2}', created_at={3})>".format(
                self.id,
                self.user_id,
                (self.query_text[:20] + "…") if len(self.query_text) > 20 else self.query_text,
                self.created_at,
            )
        )
