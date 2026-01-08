from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class Activity(Base):
    __tablename__ = 'activities'

    id = Column(Integer, primary_key=True)
    opportunity_id = Column(Integer, ForeignKey('opportunities.id', ondelete='CASCADE'), nullable=False, index=True)
    activity_type = Column(String(50), nullable=False)  # call, meeting, email, note
    subject = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    activity_date = Column(DateTime, nullable=False, index=True)
    contact_id = Column(Integer, ForeignKey('contacts.id'), nullable=True)
    created_by_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    opportunity = relationship("Opportunity", back_populates="activities")
    contact = relationship("Contact", back_populates="activities")
    created_by = relationship("User", back_populates="created_activities")

    ACTIVITY_TYPES = [
        ('call', 'Phone Call'),
        ('meeting', 'Meeting'),
        ('email', 'Email'),
        ('note', 'Note'),
        ('site_visit', 'Site Visit'),
    ]

    TYPE_ICONS = {
        'call': '📞',
        'meeting': '🤝',
        'email': '✉️',
        'note': '📝',
        'site_visit': '🏗️',
    }

    @property
    def type_display(self):
        """Get display name for activity type."""
        for code, name in self.ACTIVITY_TYPES:
            if code == self.activity_type:
                return name
        return self.activity_type

    @property
    def icon(self):
        """Get icon for activity type."""
        return self.TYPE_ICONS.get(self.activity_type, '📋')

    def __repr__(self):
        return f"<Activity {self.activity_type}: {self.subject}>"
