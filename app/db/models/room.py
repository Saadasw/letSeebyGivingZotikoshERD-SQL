"""Room and Bed models."""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    CheckConstraint,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin
from app.db.models.enums import RoomType, RoomStatus, BedStatus

if TYPE_CHECKING:
    from app.db.models.branch import Branch
    from app.db.models.patient import PatientProfile
    from app.db.models.admission import Admission


class Room(Base, UUIDMixin, TimestampMixin):
    """Hospital room."""

    __tablename__ = "room"

    branch_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("branch.id", ondelete="CASCADE"),
        nullable=False,
    )
    room_number: Mapped[str] = mapped_column(String(50), nullable=False)
    room_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    room_type: Mapped[RoomType] = mapped_column(
        ENUM(RoomType, name="room_type", create_type=False),
        nullable=False,
        default=RoomType.GENERAL,
    )
    floor: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    wing: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    building: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    capacity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    daily_rate: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=True)
    hourly_rate: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=True)
    status: Mapped[RoomStatus] = mapped_column(
        ENUM(RoomStatus, name="room_status", create_type=False),
        nullable=False,
        default=RoomStatus.AVAILABLE,
    )
    amenities: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    equipment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    has_bathroom: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    has_ac: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    has_tv: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    has_wifi: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint("capacity > 0", name="ck_capacity_positive"),
        UniqueConstraint("branch_id", "room_number", name="uq_room"),
    )

    # Relationships
    branch: Mapped["Branch"] = relationship("Branch", back_populates="rooms")
    beds: Mapped[list["Bed"]] = relationship(
        "Bed", back_populates="room", cascade="all, delete-orphan"
    )
    admissions: Mapped[list["Admission"]] = relationship(
        "Admission", back_populates="room", foreign_keys="Admission.room_id"
    )
    transfer_admissions: Mapped[list["Admission"]] = relationship(
        "Admission", back_populates="transfer_to_room", foreign_keys="Admission.transfer_to_room_id"
    )

    @property
    def is_available(self) -> bool:
        """Check if room is available."""
        return self.status == RoomStatus.AVAILABLE

    @property
    def available_beds(self) -> int:
        """Count available beds in room."""
        return sum(1 for bed in self.beds if bed.status == BedStatus.AVAILABLE)

    @property
    def display_name(self) -> str:
        """Get display name for room."""
        if self.room_name:
            return f"{self.room_number} - {self.room_name}"
        return self.room_number

    def __repr__(self) -> str:
        return f"<Room {self.room_number} ({self.room_type.value})>"


class Bed(Base, UUIDMixin, TimestampMixin):
    """Hospital bed within a room."""

    __tablename__ = "bed"

    room_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("room.id", ondelete="CASCADE"),
        nullable=False,
    )
    bed_number: Mapped[str] = mapped_column(String(50), nullable=False)
    bed_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    status: Mapped[BedStatus] = mapped_column(
        ENUM(BedStatus, name="bed_status", create_type=False),
        nullable=False,
        default=BedStatus.AVAILABLE,
    )
    current_patient_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("patient_profile.id", ondelete="SET NULL"),
        nullable=True,
    )
    current_admission_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True), nullable=True
    )
    features: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_sanitized_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        UniqueConstraint("room_id", "bed_number", name="uq_bed"),
    )

    # Relationships
    room: Mapped["Room"] = relationship("Room", back_populates="beds")
    current_patient: Mapped[Optional["PatientProfile"]] = relationship(
        "PatientProfile", back_populates="current_bed", foreign_keys=[current_patient_id]
    )
    admissions: Mapped[list["Admission"]] = relationship(
        "Admission", back_populates="bed", foreign_keys="Admission.bed_id"
    )

    @property
    def is_available(self) -> bool:
        """Check if bed is available."""
        return self.status == BedStatus.AVAILABLE

    @property
    def full_number(self) -> str:
        """Get full bed number including room."""
        return f"{self.room.room_number}-{self.bed_number}"

    def __repr__(self) -> str:
        return f"<Bed {self.bed_number} ({self.status.value})>"
