from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from sqlalchemy.orm import relationship
from app.database import Base


class ScopePackage(Base):
    __tablename__ = 'scope_packages'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    sort_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    opportunities = relationship("OpportunityScope", back_populates="scope_package")

    def __repr__(self):
        return f"<ScopePackage {self.name}>"
