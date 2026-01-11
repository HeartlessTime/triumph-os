from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Date,
    Boolean,
    ForeignKey,
)
from sqlalchemy.orm import relationship
from app.database import Base


class Contact(Base):
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True)
    account_id = Column(
        Integer,
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    title = Column(String(100), nullable=True)
    email = Column(String(255), nullable=True, index=True)
    phone = Column(String(50), nullable=True)
    mobile = Column(String(50), nullable=True)
    is_primary = Column(Boolean, nullable=False, default=False)
    notes = Column(Text, nullable=True)
    last_contacted = Column(Date, nullable=True)
    next_followup = Column(Date, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    account = relationship("Account", back_populates="contacts")
    opportunities = relationship("Opportunity", back_populates="primary_contact")
    activities = relationship("Activity", back_populates="contact")

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def display_name(self):
        """Full name with title if available."""
        if self.title:
            return f"{self.full_name} ({self.title})"
        return self.full_name

    @property
    def best_phone(self):
        """Return mobile if available, otherwise office phone."""
        return self.mobile or self.phone

    def __repr__(self):
        return f"<Contact {self.full_name}>"
