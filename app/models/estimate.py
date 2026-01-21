from datetime import datetime
from decimal import Decimal
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Numeric,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from app.database import Base


class Estimate(Base):
    __tablename__ = "estimates"
    __table_args__ = (
        UniqueConstraint("opportunity_id", "version", name="uq_estimate_version"),
    )

    id = Column(Integer, primary_key=True)
    opportunity_id = Column(
        Integer,
        ForeignKey("opportunities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version = Column(Integer, nullable=False, default=1)
    name = Column(String(255), nullable=True)
    status = Column(String(50), nullable=False, default="Draft")
    labor_total = Column(Numeric(15, 2), nullable=False, default=Decimal("0"))
    material_total = Column(Numeric(15, 2), nullable=False, default=Decimal("0"))
    subtotal = Column(Numeric(15, 2), nullable=False, default=Decimal("0"))
    margin_percent = Column(Numeric(5, 2), nullable=False, default=Decimal("20"))
    margin_amount = Column(Numeric(15, 2), nullable=False, default=Decimal("0"))
    total = Column(Numeric(15, 2), nullable=False, default=Decimal("0"))
    notes = Column(Text, nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    opportunity = relationship("Opportunity", back_populates="estimates")
    created_by = relationship("User", back_populates="created_estimates")
    line_items = relationship(
        "EstimateLineItem",
        back_populates="estimate",
        cascade="all, delete-orphan",
        order_by="EstimateLineItem.sort_order",
    )

    STATUSES = ["Draft", "Review", "Approved", "Sent", "Revised"]

    @property
    def display_name(self):
        """Return display name like 'v1' or custom name."""
        if self.name:
            return f"v{self.version} - {self.name}"
        return f"v{self.version}"

    @property
    def labor_items(self):
        return [item for item in self.line_items if item.line_type == "labor"]

    @property
    def material_items(self):
        return [item for item in self.line_items if item.line_type == "material"]

    def calculate_totals(self):
        """Recalculate all totals from line items."""
        self.labor_total = sum(item.total or Decimal("0") for item in self.labor_items)
        self.material_total = sum(
            item.total or Decimal("0") for item in self.material_items
        )
        self.subtotal = self.labor_total + self.material_total

        if self.margin_percent:
            # Margin is calculated as: total = subtotal / (1 - margin_percent/100)
            # e.g., 20% margin means selling at 125% of cost
            divisor = Decimal("1") - (self.margin_percent / Decimal("100"))
            if divisor > 0:
                self.total = self.subtotal / divisor
                self.margin_amount = self.total - self.subtotal
            else:
                self.total = self.subtotal
                self.margin_amount = Decimal("0")
        else:
            self.total = self.subtotal
            self.margin_amount = Decimal("0")

        return self

    def __repr__(self):
        return f"<Estimate {self.opportunity_id} v{self.version}>"


class EstimateLineItem(Base):
    __tablename__ = "estimate_line_items"

    id = Column(Integer, primary_key=True)
    estimate_id = Column(
        Integer,
        ForeignKey("estimates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    line_type = Column(String(50), nullable=False)  # labor, material
    description = Column(String(500), nullable=False)
    quantity = Column(Numeric(15, 4), nullable=False, default=Decimal("1"))
    unit = Column(String(50), nullable=True)
    unit_cost = Column(Numeric(15, 4), nullable=False, default=Decimal("0"))
    total = Column(Numeric(15, 2), nullable=False, default=Decimal("0"))
    sort_order = Column(Integer, nullable=False, default=0)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    estimate = relationship("Estimate", back_populates="line_items")

    LINE_TYPES = ["labor", "material"]

    UNITS = [
        "each",
        "hour",
        "day",
        "sf",  # square feet
        "lf",  # linear feet
        "cy",  # cubic yards
        "ton",
        "gallon",
        "lot",
        "ls",  # lump sum
    ]

    def calculate_total(self):
        """Calculate line item total from quantity and unit cost."""
        self.total = (self.quantity or Decimal("0")) * (self.unit_cost or Decimal("0"))
        return self

    def __repr__(self):
        return f"<EstimateLineItem {self.description[:30]}>"
