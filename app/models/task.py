from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Text, DateTime, Date, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True)
    opportunity_id = Column(
        Integer,
        ForeignKey("opportunities.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    due_date = Column(Date, nullable=True, index=True)
    priority = Column(String(20), nullable=False, default="Medium")
    status = Column(String(20), nullable=False, default="Open", index=True)
    completed_at = Column(DateTime, nullable=True)
    completed_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    account_id = Column(
        Integer,
        ForeignKey("accounts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    assigned_to_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    opportunity = relationship("Opportunity", back_populates="tasks")
    account = relationship("Account", back_populates="tasks")
    completed_by = relationship(
        "User", back_populates="completed_tasks", foreign_keys=[completed_by_id]
    )
    assigned_to = relationship(
        "User", back_populates="assigned_tasks", foreign_keys=[assigned_to_id]
    )
    created_by = relationship(
        "User", back_populates="created_tasks", foreign_keys=[created_by_id]
    )

    STATUSES = ["Open", "Completed"]

    @property
    def is_overdue(self):
        """Check if task is overdue."""
        if self.status == "Completed":
            return False
        if self.due_date:
            return self.due_date < date.today()
        return False

    @property
    def days_until_due(self):
        """Return days until due date."""
        if self.due_date:
            delta = self.due_date - date.today()
            return delta.days
        return None

    def complete(self, completed_by_user_id: int = None):
        """Mark task as complete."""
        self.status = "Completed"
        self.completed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        # Only set completed_by_id if not already set (preserve original completer)
        if self.completed_by_id is None and completed_by_user_id is not None:
            self.completed_by_id = completed_by_user_id
        return self

    def reopen(self):
        """Reopen a completed task."""
        self.status = "Open"
        return self

    def __repr__(self):
        return f"<Task {self.title}>"
