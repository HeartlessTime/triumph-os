from datetime import date, datetime
import sqlalchemy as sa
from sqlalchemy import Boolean, Column, Date, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class Activity(Base):
    __tablename__ = "activities"

    id = Column(Integer, primary_key=True)
    opportunity_id = Column(
        Integer,
        ForeignKey("opportunities.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    activity_type = Column(String(50), nullable=False)  # call, meeting, email, note
    subject = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    activity_date = Column(DateTime, nullable=False, index=True)
    contact_id = Column(Integer, ForeignKey("contacts.id"), nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Job walk fields
    walk_notes = Column(Text, nullable=True)
    job_walk_status = Column(String(50), nullable=True)  # open, sent_to_estimator, complete
    estimate_due_by = Column(Date, nullable=True)

    # Job walk / estimating fields (job_walk activities only)
    requires_estimate = Column(Boolean, nullable=False, server_default=sa.text("false"))
    scope_summary = Column(Text, nullable=True)
    estimated_quantity = Column(String(100), nullable=True)
    complexity_notes = Column(Text, nullable=True)
    estimate_needed_by = Column(Date, nullable=True)
    assigned_estimator_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    estimate_completed = Column(Boolean, nullable=False, server_default=sa.text("false"))
    estimate_completed_at = Column(Date, nullable=True)

    # Relationships
    opportunity = relationship("Opportunity", back_populates="activities")
    contact = relationship("Contact", back_populates="activities")
    attendee_links = relationship(
        "ActivityAttendee",
        back_populates="activity",
        cascade="all, delete-orphan",
    )
    created_by = relationship(
        "User", back_populates="created_activities", foreign_keys=[created_by_id]
    )
    assigned_estimator = relationship("User", foreign_keys=[assigned_estimator_id])
    walk_segments = relationship(
        "WalkSegment",
        back_populates="activity",
        cascade="all, delete-orphan",
        order_by="WalkSegment.sort_order",
    )

    # Activity types for logging interactions.
    # "meeting_requested" is used when a meeting has been discussed/proposed but not yet
    # scheduled. The actual calendar invite lives in Outlook (source of truth for scheduled
    # meetings). This app only tracks reminders and follow-ups - not the calendar itself.
    ACTIVITY_TYPES = [
        ("call", "Phone Call"),
        ("meeting", "Meeting"),
        ("meeting_requested", "Meeting Requested"),  # Meeting discussed but not yet scheduled
        ("email", "Email"),
        ("note", "Note"),
        ("site_visit", "Site Visit"),
        ("job_walk", "Job Walk"),
        ("task_completed", "Task Completed"),
        ("other", "Other"),
    ]

    TYPE_ICONS = {
        "call": "📞",
        "meeting": "🤝",
        "meeting_requested": "📅",  # Calendar icon - pending meeting to schedule
        "email": "✉️",
        "note": "📝",
        "site_visit": "🏗️",
        "job_walk": "🚶",
        "task_completed": "✅",
        "other": "📋",
    }

    @property
    def attendees(self):
        """Get all attendee contacts for this activity.

        For meetings: uses the activity_attendees junction table.
        Falls back to the single contact_id for legacy/non-meeting activities.
        """
        if self.attendee_links:
            return [link.contact for link in self.attendee_links]
        if self.contact:
            return [self.contact]
        return []

    @property
    def attendees_display(self):
        """Human-readable attendee string.

        Examples:
          - 'John Smith'
          - 'John Smith and Sarah Lee'
          - 'John Smith + 2 others'
        """
        names = [c.full_name for c in self.attendees]
        if not names:
            return None
        if len(names) == 1:
            return names[0]
        if len(names) == 2:
            return f"{names[0]} and {names[1]}"
        return f"{names[0]} + {len(names) - 1} others"

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
        return self.TYPE_ICONS.get(self.activity_type, "📋")

    @property
    def estimate_status(self):
        """Derived status for job walks."""
        if not self.requires_estimate:
            return None
        if self.estimate_completed:
            return "completed"
        if self.estimate_needed_by and self.estimate_needed_by < date.today():
            return "overdue"
        if self.estimate_needed_by and self.estimate_needed_by == date.today():
            return "due_today"
        if self.estimate_needed_by and (self.estimate_needed_by - date.today()).days <= 3:
            return "due_soon"
        return "pending"

    @property
    def days_until_estimate_needed(self):
        """Days until estimate is needed. Negative = overdue."""
        if self.estimate_needed_by:
            return (self.estimate_needed_by - date.today()).days
        return None

    def __repr__(self):
        return f"<Activity {self.activity_type}: {self.subject}>"
