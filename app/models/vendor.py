from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Date, Numeric, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class Vendor(Base):
    __tablename__ = 'vendors'

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    contact_name = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    address = Column(Text, nullable=True)
    specialty = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    quote_requests = relationship("VendorQuoteRequest", back_populates="vendor")

    SPECIALTIES = [
        'Electrical',
        'Plumbing',
        'HVAC',
        'Concrete',
        'Steel',
        'Drywall',
        'Flooring',
        'Roofing',
        'Painting',
        'Equipment',
        'General Materials',
        'Other'
    ]

    def __repr__(self):
        return f"<Vendor {self.name}>"


class VendorQuoteRequest(Base):
    __tablename__ = 'vendor_quote_requests'

    id = Column(Integer, primary_key=True)
    opportunity_id = Column(Integer, ForeignKey('opportunities.id', ondelete='CASCADE'), nullable=False, index=True)
    vendor_id = Column(Integer, ForeignKey('vendors.id'), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, default='Pending')
    sent_date = Column(Date, nullable=True)
    due_date = Column(Date, nullable=True)
    received_date = Column(Date, nullable=True)
    quote_amount = Column(Numeric(15, 2), nullable=True)
    notes = Column(Text, nullable=True)
    created_by_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    opportunity = relationship("Opportunity", back_populates="vendor_quote_requests")
    vendor = relationship("Vendor", back_populates="quote_requests")
    created_by = relationship("User")

    STATUSES = ['Pending', 'Sent', 'Received', 'Declined', 'Expired']

    @property
    def is_overdue(self):
        """Check if quote request is overdue."""
        if self.status in ['Received', 'Declined', 'Expired']:
            return False
        if self.due_date:
            return self.due_date < datetime.now().date()
        return False

    def __repr__(self):
        return f"<VendorQuoteRequest {self.vendor.name if self.vendor else 'Unknown'}>"
