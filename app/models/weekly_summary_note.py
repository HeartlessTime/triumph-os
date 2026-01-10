"""
Weekly Summary Notes Model

Stores user notes for specific sections of the weekly summary page.
Notes are keyed by week_start date and section name.
"""

from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Text, DateTime, Date, Index
from app.database import Base


class WeeklySummaryNote(Base):
    __tablename__ = 'weekly_summary_notes'

    id = Column(Integer, primary_key=True)
    week_start = Column(Date, nullable=False, index=True)
    section = Column(String(50), nullable=False, index=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Composite index for efficient lookups by week + section
    __table_args__ = (
        Index('ix_weekly_summary_notes_week_section', 'week_start', 'section'),
    )

    # Valid section names
    SECTIONS = ['outreach', 'pipeline', 'tasks', 'new_records', 'other']

    def __repr__(self):
        return f"<WeeklySummaryNote {self.week_start} - {self.section}>"
