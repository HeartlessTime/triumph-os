from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class WalkSegment(Base):
    __tablename__ = "walk_segments"

    id = Column(Integer, primary_key=True)
    activity_id = Column(
        Integer,
        ForeignKey("activities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    location_name = Column(String(255), nullable=False)
    segment_type = Column(String(50), nullable=False)  # idf, mdf, room, closet, other
    description = Column(Text, nullable=True)
    quantity_count = Column(Integer, nullable=True)
    quantity_label = Column(String(100), nullable=True)  # "drops", "runs", "ports"
    photo_notes = Column(Text, nullable=True)
    estimated_cable_length = Column(Integer, nullable=True)  # feet
    sort_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    activity = relationship("Activity", back_populates="walk_segments")

    SEGMENT_TYPES = [
        ("idf", "IDF"),
        ("mdf", "MDF"),
        ("room", "Room"),
        ("closet", "Telecom Closet"),
        ("other", "Other"),
    ]

    @property
    def type_display(self):
        for code, name in self.SEGMENT_TYPES:
            if code == self.segment_type:
                return name
        return self.segment_type

    @property
    def quantity_display(self):
        if self.quantity_count is not None:
            label = self.quantity_label or ""
            return f"{self.quantity_count} {label}".strip()
        return None

    def __repr__(self):
        return f"<WalkSegment {self.segment_type}: {self.location_name}>"
