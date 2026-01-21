"""
OpportunityAccount Association Table

Many-to-many relationship between Opportunities and Accounts.
An Opportunity can have multiple Accounts, and an Account can be associated with multiple Opportunities.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.database import Base


class OpportunityAccount(Base):
    """Junction table for Opportunity-Account many-to-many relationship."""

    __tablename__ = "opportunity_accounts"

    id = Column(Integer, primary_key=True)
    opportunity_id = Column(
        Integer,
        ForeignKey("opportunities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    account_id = Column(
        Integer,
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    opportunity = relationship("Opportunity", back_populates="account_links")
    account = relationship("Account", back_populates="opportunity_links")

    def __repr__(self):
        return f"<OpportunityAccount opp={self.opportunity_id} acc={self.account_id}>"
