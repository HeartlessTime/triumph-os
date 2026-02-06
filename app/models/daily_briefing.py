"""
Daily Briefing Model

Stores the AI-generated briefing text for the Daily Summary page.
One row per date — content is shared across all devices.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, Text, DateTime, Date
from app.database import Base


class DailyBriefing(Base):
    __tablename__ = "daily_briefings"

    id = Column(Integer, primary_key=True)
    summary_date = Column(Date, nullable=False, index=True, unique=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self):
        return f"<DailyBriefing {self.summary_date}>"
