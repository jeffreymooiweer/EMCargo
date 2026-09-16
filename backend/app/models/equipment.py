"""Confirmed equipment movements and locally stored supporting files.

A shipment draft is not evidence that an asset moved. These records are written
only by explicit management actions, independently of optional shipment history.
"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, LargeBinary, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class EquipmentEvent(Base):
    __tablename__ = "equipment_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    equipment_id: Mapped[int] = mapped_column(ForeignKey("equipment_items.id", ondelete="CASCADE"), index=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    actor_name: Mapped[str] = mapped_column(String(64), default="")
    action: Mapped[str] = mapped_column(String(24))
    from_location: Mapped[str] = mapped_column(String(200), default="")
    to_location: Mapped[str] = mapped_column(String(200), default="")
    availability: Mapped[str] = mapped_column(String(24), default="unknown")
    reference: Mapped[str] = mapped_column(String(120), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EquipmentFile(Base):
    __tablename__ = "equipment_files"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    equipment_id: Mapped[int] = mapped_column(ForeignKey("equipment_items.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    media_type: Mapped[str] = mapped_column(String(64))
    kind: Mapped[str] = mapped_column(String(16))
    size: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64))
    content: Mapped[bytes] = mapped_column(LargeBinary, deferred=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
