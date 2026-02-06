from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Text, DateTime, Date, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, index=True)
    account_type = Column(String(20), nullable=False, default="end_user", index=True)
    industry = Column(String(100), nullable=True)
    website = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    zip_code = Column(String(20), nullable=True)
    notes = Column(Text, nullable=True)
    awaiting_response = Column(Boolean, nullable=False, default=False, index=True)
    is_hot = Column(Boolean, nullable=False, default=False, index=True)
    next_action = Column(Text, nullable=True)
    next_action_due_date = Column(Date, nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    created_by = relationship("User", back_populates="created_accounts")
    contacts = relationship(
        "Contact", back_populates="account", cascade="all, delete-orphan"
    )
    # Legacy relationship - kept for migration
    opportunities = relationship(
        "Opportunity",
        back_populates="account",
        foreign_keys="Opportunity.account_id",
    )
    end_user_opportunities = relationship(
        "Opportunity",
        back_populates="end_user_account",
        foreign_keys="Opportunity.end_user_account_id",
    )
    tasks = relationship("Task", back_populates="account", foreign_keys="Task.account_id")
    # Multi-account relationship via junction table
    opportunity_links = relationship(
        "OpportunityAccount",
        back_populates="account",
        cascade="all, delete-orphan",
    )

    # Simplified - removed GC type
    ACCOUNT_TYPES = [
        ("end_user", "End User"),
    ]

    INDUSTRIES = [
        "Construction",
        "Manufacturing",
        "Healthcare",
        "Education",
        "Government",
        "Retail",
        "Technology",
        "Finance",
        "Real Estate",
        "Hospitality",
        "Other",
    ]

    @property
    def account_type_display(self):
        """Get display name for account type."""
        type_map = dict(self.ACCOUNT_TYPES)
        return type_map.get(self.account_type, self.account_type)

    @property
    def full_address(self):
        parts = []
        if self.address:
            parts.append(self.address)
        city_state = []
        if self.city:
            city_state.append(self.city)
        if self.state:
            city_state.append(self.state)
        if city_state:
            parts.append(", ".join(city_state))
        if self.zip_code:
            parts.append(self.zip_code)
        return "\n".join(parts) if parts else None

    @property
    def primary_contact(self):
        for contact in self.contacts:
            if contact.is_primary:
                return contact
        return self.contacts[0] if self.contacts else None

    @property
    def total_pipeline_value(self):
        """Calculate total pipeline value from linked opportunities."""
        # Use opportunity_links to get all linked opportunities
        return sum(
            link.opportunity.value or 0
            for link in self.opportunity_links
            if link.opportunity.stage not in ["Won", "Lost"]
        )

    @property
    def open_opportunities_count(self):
        """Count open opportunities linked to this account."""
        return len(
            [link for link in self.opportunity_links
             if link.opportunity.stage not in ["Won", "Lost"]]
        )

    @property
    def linked_opportunities(self):
        """Get all opportunities linked to this account."""
        return [link.opportunity for link in self.opportunity_links]

    @property
    def last_contacted(self):
        """Get the most recent last_contacted date from all contacts."""
        dates = [c.last_contacted for c in self.contacts if c.last_contacted]
        return max(dates) if dates else None

    @property
    def days_since_last_activity(self):
        """Days since last contact with any contact at this account."""
        if self.last_contacted:
            return (date.today() - self.last_contacted).days
        return None

    @property
    def days_until_next_action(self):
        """Days until next action due date. Negative means overdue."""
        if self.next_action_due_date:
            return (self.next_action_due_date - date.today()).days
        return None

    def __repr__(self):
        return f"<Account {self.name}>"
