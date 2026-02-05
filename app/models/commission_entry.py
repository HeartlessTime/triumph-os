from datetime import datetime
from sqlalchemy import Column, DateTime, Integer, Numeric, String, Text
from app.database import Base


class CommissionEntry(Base):
    __tablename__ = "commission_entries"

    id = Column(Integer, primary_key=True)
    month = Column(String(7), nullable=False)  # "YYYY-MM"
    account_name = Column(String(255), nullable=False)
    job_name = Column(String(255), nullable=False)
    job_number = Column(String(100), nullable=True)
    contact = Column(String(255), nullable=True)
    job_amount = Column(Numeric(12, 2), nullable=True)
    commission_amount = Column(Numeric(12, 2), nullable=True)
    notes = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, server_default="draft")  # draft | exported
    exported_month = Column(String(7), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<CommissionEntry {self.account_name} - {self.job_name} ({self.month})>"
