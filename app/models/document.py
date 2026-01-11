from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True)
    opportunity_id = Column(
        Integer,
        ForeignKey("opportunities.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    estimate_id = Column(
        Integer, ForeignKey("estimates.id", ondelete="SET NULL"), nullable=True
    )
    name = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=True)
    mime_type = Column(String(100), nullable=True)
    document_type = Column(
        String(50), nullable=True
    )  # proposal, spec, drawing, quote, other
    uploaded_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    opportunity = relationship("Opportunity", back_populates="documents")
    estimate = relationship("Estimate", back_populates="documents")
    uploaded_by = relationship("User", back_populates="uploaded_documents")

    DOCUMENT_TYPES = [
        ("proposal", "Proposal"),
        ("spec", "Specification"),
        ("drawing", "Drawing"),
        ("quote", "Quote"),
        ("contract", "Contract"),
        ("photo", "Photo"),
        ("other", "Other"),
    ]

    TYPE_ICONS = {
        "proposal": "📄",
        "spec": "📋",
        "drawing": "📐",
        "quote": "💰",
        "contract": "📝",
        "photo": "📷",
        "other": "📎",
    }

    @property
    def type_display(self):
        """Get display name for document type."""
        for code, name in self.DOCUMENT_TYPES:
            if code == self.document_type:
                return name
        return "Document"

    @property
    def icon(self):
        """Get icon for document type."""
        return self.TYPE_ICONS.get(self.document_type, "📎")

    @property
    def file_size_display(self):
        """Return human-readable file size."""
        if not self.file_size:
            return "Unknown"
        size = self.file_size
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    @property
    def extension(self):
        """Get file extension."""
        if "." in self.original_filename:
            return self.original_filename.rsplit(".", 1)[1].lower()
        return ""

    def __repr__(self):
        return f"<Document {self.name}>"
