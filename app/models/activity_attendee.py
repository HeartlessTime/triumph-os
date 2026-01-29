from datetime import datetime
from sqlalchemy import Column, Integer, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.database import Base


class ActivityAttendee(Base):
    __tablename__ = "activity_attendees"

    id = Column(Integer, primary_key=True)
    activity_id = Column(
        Integer,
        ForeignKey("activities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    contact_id = Column(
        Integer,
        ForeignKey("contacts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    activity = relationship("Activity", back_populates="attendee_links")
    contact = relationship("Contact")

    def __repr__(self):
        return f"<ActivityAttendee activity={self.activity_id} contact={self.contact_id}>"
