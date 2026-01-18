"""Medicine catalog model."""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, Numeric, String, Text
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin
from app.db.models.enums import DosageForm

if TYPE_CHECKING:
    from app.db.models.prescription import PrescriptionItem
    from app.db.models.inventory import Inventory


class Medicine(Base, UUIDMixin, TimestampMixin):
    """Medicine catalog entry."""

    __tablename__ = "medicine"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    generic_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    brand_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    sub_category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    manufacturer: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    dosage_form: Mapped[Optional[DosageForm]] = mapped_column(
        ENUM(DosageForm, name="dosage_form", create_type=False),
        nullable=True,
    )
    strength: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    unit: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=True)
    requires_prescription: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_controlled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    contraindications: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    side_effects: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    storage_instructions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    prescription_items: Mapped[list["PrescriptionItem"]] = relationship(
        "PrescriptionItem", back_populates="medicine"
    )
    inventory: Mapped[list["Inventory"]] = relationship(
        "Inventory", back_populates="medicine"
    )

    @property
    def display_name(self) -> str:
        """Get display name with strength."""
        if self.strength:
            return f"{self.name} {self.strength}"
        return self.name

    @property
    def is_otc(self) -> bool:
        """Check if medicine is over-the-counter."""
        return not self.requires_prescription

    def __repr__(self) -> str:
        return f"<Medicine {self.code}: {self.name}>"
