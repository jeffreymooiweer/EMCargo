from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, LargeBinary, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Department(Base):
    """A group of users whose kept shipments are theirs to see.

    Only meaningful with the shipment history: it decides who sees whose
    shipments on the shipments page. An organisation that never makes one
    keeps today's behaviour, in which everybody sees everything.
    """

    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(16), default="user")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    #: Added in v1.174.0 by schema step 2; nullable, because a user without a
    #: department is the ordinary case and the one every older database has.
    department_id: Mapped[int | None] = mapped_column(
        ForeignKey("departments.id", ondelete="SET NULL"), nullable=True)

    jobs: Mapped[list["Job"]] = relationship(back_populates="creator")
    department: Mapped[Department | None] = relationship()
    avatar: Mapped["UserAvatar | None"] = relationship(
        cascade="all, delete-orphan", uselist=False)
    personal_profile: Mapped["UserProfile | None"] = relationship(
        cascade="all, delete-orphan", uselist=False)

    @property
    def display_name(self) -> str:
        profile = self.personal_profile
        if profile is None:
            return ""
        return profile.display_name or " ".join(
            part for part in (profile.first_name, profile.last_name) if part)

    @property
    def avatar_url(self) -> str | None:
        return f"/api/users/{self.id}/avatar?v={self.avatar.etag}" if self.avatar else None


class UserProfile(Base):
    """Optional personal details, separate from account identity and privileges.

    A new table lets existing installations upgrade through create_all without
    changing their users table. Account deletion also removes these details.
    Only the display name is included in the user directory's public DTO.
    """

    __tablename__ = "user_profiles"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(80), default="")
    first_name: Mapped[str] = mapped_column(String(80), default="")
    last_name: Mapped[str] = mapped_column(String(80), default="")
    job_title: Mapped[str] = mapped_column(String(120), default="")
    phone_number: Mapped[str] = mapped_column(String(40), default="")


class UserAvatar(Base):
    """A bounded, normalized profile image owned by one account.

    A separate table is created by the existing bootstrap on upgrades; no
    existing user columns change. Image bytes are deferred when listing users.
    """

    __tablename__ = "user_avatars"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    image: Mapped[bytes] = mapped_column(LargeBinary, deferred=True)
    etag: Mapped[str] = mapped_column(String(64))


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(255), default="New shipment")
    status: Mapped[str] = mapped_column(String(32), default="draft")
    input_raw: Mapped[str | None] = mapped_column(Text, nullable=True)
    parsed_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    calculated_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    export_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    creator: Mapped[User] = relationship(back_populates="jobs")


class Material(Base):
    __tablename__ = "materials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    canonical_name: Mapped[str] = mapped_column(String(128))
    category: Mapped[str] = mapped_column(String(64))
    density_kg_m3: Mapped[float] = mapped_column()
    density_min_kg_m3: Mapped[float | None] = mapped_column(nullable=True)
    density_max_kg_m3: Mapped[float | None] = mapped_column(nullable=True)
    unit: Mapped[str] = mapped_column(String(16), default="kg/m3")
    condition: Mapped[str | None] = mapped_column(String(64), nullable=True)
    language_labels_json: Mapped[str] = mapped_column(Text, default="{}")
    aliases_json: Mapped[str] = mapped_column(Text, default="[]")
    source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_type: Mapped[str] = mapped_column(String(64))
    size_label: Mapped[str] = mapped_column(String(64))
    kg_per_meter: Mapped[float] = mapped_column()
    material: Mapped[str] = mapped_column(String(64), default="steel")
    standard: Mapped[str | None] = mapped_column(String(64), nullable=True)
    aliases_json: Mapped[str] = mapped_column(Text, default="[]")
    source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class ReferenceItem(Base):
    __tablename__ = "reference_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    canonical_name: Mapped[str] = mapped_column(String(128))
    category: Mapped[str] = mapped_column(String(64), default="electrical")
    reference_weight_kg: Mapped[float] = mapped_column()
    reference_volume_m3: Mapped[float | None] = mapped_column(nullable=True)
    aliases_json: Mapped[str] = mapped_column(Text, default="[]")
    language_labels_json: Mapped[str] = mapped_column(Text, default="{}")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Equipment(Base):
    """The equipment library: the items an organisation ships regularly.

    The SAP material number the list once carried is gone (v1.116.0): it came
    from one organisation's old system, meant nothing anywhere else, and yet
    it was the column an item was named by. The wall thickness took its
    place — a measurement that actually describes the thing, and without
    which the weight of a hollow section cannot be worked out.
    """

    __tablename__ = "equipment_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    specifications: Mapped[str] = mapped_column(String(255))
    length_cm: Mapped[float | None] = mapped_column(nullable=True)
    width_cm: Mapped[float | None] = mapped_column(nullable=True)
    height_cm: Mapped[float | None] = mapped_column(nullable=True)
    #: Millimetres on the screen and in the file, as people write down a wall.
    wall_thickness_mm: Mapped[float | None] = mapped_column(nullable=True)
    weight_kg: Mapped[float] = mapped_column()
    aliases_json: Mapped[str] = mapped_column(Text, default="[]")
    language_labels_json: Mapped[str] = mapped_column(Text, default="{}")
    source: Mapped[str | None] = mapped_column(String(64), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
