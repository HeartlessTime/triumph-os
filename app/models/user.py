from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, index=True)  # Admin, Sales, Estimator
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    owned_opportunities = relationship(
        "Opportunity", back_populates="owner", foreign_keys="Opportunity.owner_id"
    )
    assigned_estimates = relationship(
        "Opportunity",
        back_populates="assigned_estimator",
        foreign_keys="Opportunity.assigned_estimator_id",
    )
    created_accounts = relationship("Account", back_populates="created_by")
    created_estimates = relationship("Estimate", back_populates="created_by")
    created_activities = relationship("Activity", back_populates="created_by")
    assigned_tasks = relationship(
        "Task", back_populates="assigned_to", foreign_keys="Task.assigned_to_id"
    )
    created_tasks = relationship(
        "Task", back_populates="created_by", foreign_keys="Task.created_by_id"
    )
    completed_tasks = relationship(
        "Task", back_populates="completed_by", foreign_keys="Task.completed_by_id"
    )
    summary_suppressions = relationship(
        "UserSummarySuppression",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    ROLES = ["Admin", "Sales", "Estimator"]

    @property
    def is_admin(self):
        return self.role == "Admin"

    @property
    def is_sales(self):
        return self.role == "Sales"

    @property
    def is_estimator(self):
        return self.role == "Estimator"

    def can_edit_opportunity(self, opportunity):
        """Check if user can edit an opportunity."""
        if self.is_admin:
            return True
        if self.is_sales and opportunity.owner_id == self.id:
            return True
        if self.is_estimator and opportunity.assigned_estimator_id == self.id:
            return True
        return False

    def __repr__(self):
        return f"<User {self.email}>"
