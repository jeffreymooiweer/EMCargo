"""An explicitly submitted shipment, independent of optional shipment history."""
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class DgReview(Base):
    __tablename__ = "dg_reviews"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    created_by: Mapped[str] = mapped_column(String(64))
    shipment_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reference: Mapped[str] = mapped_column(String(255), default="")
    modality: Mapped[str] = mapped_column(String(16))
    payload_json: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(24), default="pending", index=True)
    reviewed_by: Mapped[str] = mapped_column(String(64), default="")
    comment: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    work_due_date: Mapped[str | None] = mapped_column(String(10), nullable=True)
    work_draft_fingerprint: Mapped[str] = mapped_column(String(64), default="")
    work_consignee: Mapped[str] = mapped_column(String(255), default="")
    work_completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
