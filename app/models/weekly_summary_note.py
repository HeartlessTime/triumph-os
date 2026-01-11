"""
Weekly Summary Notes Model

Stores user notes for specific sections of the weekly summary page.
Notes are keyed by week_start date, section name, and optionally user_id.

- user_id = NULL: Team-level notes (shared across all users)
- user_id = X: Personal notes for user X
"""

from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Text, DateTime, Date, Index, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class WeeklySummaryNote(Base):
    __tablename__ = 'weekly_summary_notes'

    id = Column(Integer, primary_key=True)
    week_start = Column(Date, nullable=False, index=True)
    section = Column(String(50), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True, index=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    user = relationship("User")

    # Composite index for efficient lookups by week + section + user
    __table_args__ = (
        Index('ix_weekly_summary_notes_week_section_user', 'week_start', 'section', 'user_id'),
    )

    # Valid section names
    SECTIONS = ['outreach', 'pipeline', 'tasks', 'new_records', 'other']

    def __repr__(self):
        return f"<WeeklySummaryNote {self.week_start} - {self.section} - user:{self.user_id}>"
