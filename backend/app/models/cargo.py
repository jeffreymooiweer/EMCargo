"""Packaging master data and indexed identities of deliberately kept units."""
from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PackagingTemplate(Base):
    __tablename__ = "packaging_templates"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(160), index=True)
    data_json: Mapped[str] = mapped_column(Text, default="{}")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    version: Mapped[int] = mapped_column(Integer, default=1)


class CargoIdentity(Base):
    __tablename__ = "cargo_identities"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True)
    reusable: Mapped[bool] = mapped_column(Boolean, default=False)
    equipment_id: Mapped[int | None] = mapped_column(ForeignKey("equipment_items.id", ondelete="SET NULL"), nullable=True, unique=True)
    # Master identity has no shipment content. Historic contents live only in
    # the shipment's own immutable-at-read snapshot and share its retention.
    unit_json: Mapped[str] = mapped_column(Text, default="{}")


class CargoUse(Base):
    __tablename__ = "cargo_uses"
    __table_args__ = (UniqueConstraint("shipment_id", "unit_id"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    shipment_id: Mapped[int] = mapped_column(ForeignKey("shipments.id", ondelete="CASCADE"), index=True)
    unit_id: Mapped[str] = mapped_column(ForeignKey("cargo_identities.id", ondelete="CASCADE"), index=True)
