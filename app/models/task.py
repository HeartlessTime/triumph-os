from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Text, DateTime, Date, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class Task(Base):
    __tablename__ = 'tasks'

    id = Column(Integer, primary_key=True)
    opportunity_id = Column(Integer, ForeignKey('opportunities.id', ondelete='CASCADE'), nullable=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    due_date = Column(Date, nullable=True, index=True)
    priority = Column(String(20), nullable=False, default='Medium')
    status = Column(String(20), nullable=False, default='Open', index=True)
    assigned_to_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    created_by_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    opportunity = relationship("Opportunity", back_populates="tasks")
    assigned_to = relationship("User", back_populates="assigned_tasks", foreign_keys=[assigned_to_id])
    created_by = relationship("User", back_populates="created_tasks", foreign_keys=[created_by_id])

    PRIORITIES = ['Low', 'Medium', 'High', 'Urgent']
    STATUSES = ['Open', 'Complete']

    PRIORITY_COLORS = {
        'Low': '#6c757d',
        'Medium': '#0d6efd',
        'High': '#fd7e14',
        'Urgent': '#dc3545',
    }

    @property
    def is_overdue(self):
        """Check if task is overdue."""
        if self.status == 'Complete':
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

    @property
    def priority_color(self):
        return self.PRIORITY_COLORS.get(self.priority, '#6c757d')

    def complete(self):
        """Mark task as complete."""
        self.status = 'Complete'
        self.completed_at = datetime.utcnow()
        return self

    def reopen(self):
        """Reopen a completed task."""
        self.status = 'Open'
        self.completed_at = None
        return self

    def __repr__(self):
        return f"<Task {self.title}>"
