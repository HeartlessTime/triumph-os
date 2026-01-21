from datetime import datetime, date
from sqlalchemy import Column, Integer, ForeignKey, Date, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base


class UserSummarySuppression(Base):
    """Track opportunities suppressed from a user's personal summary.

    When a user clicks "Remove from My Summary", this creates a suppression record.
    The opportunity will be hidden from their summary until new pipeline activity
    occurs (a new Activity with "Stage changed" in subject after suppressed_at).
    """
    __tablename__ = "user_summary_suppressions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    opportunity_id = Column(Integer, ForeignKey("opportunities.id", ondelete="CASCADE"), nullable=False, index=True)
    suppressed_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Unique constraint: one suppression per user/opportunity pair
    __table_args__ = (
        UniqueConstraint('user_id', 'opportunity_id', name='uq_user_opportunity_suppression'),
    )

    # Relationships
    user = relationship("User", back_populates="summary_suppressions")
    opportunity = relationship("Opportunity", back_populates="summary_suppressions")

    def __repr__(self):
        return f"<UserSummarySuppression user={self.user_id} opp={self.opportunity_id}>"
