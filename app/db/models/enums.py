"""Database Enums matching PostgreSQL enum types."""

from enum import Enum


class UserRole(str, Enum):
    """User roles in the system."""
    ADMIN = "admin"
    DOCTOR = "doctor"
    STAFF = "staff"
    PATIENT = "patient"


class StaffDepartment(str, Enum):
    """Staff departments with specific permissions."""
    RECEPTION = "reception"
    LABORATORY = "laboratory"
    PHARMACY = "pharmacy"
    BILLING = "billing"
    NURSING = "nursing"
    HOUSEKEEPING = "housekeeping"
    RADIOLOGY = "radiology"
    RECORDS = "records"
    IT = "it"
    HR = "hr"
    GENERAL = "general"


class GenderType(str, Enum):
    """Gender types."""
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"


class ScheduleOverrideType(str, Enum):
    """Types of schedule overrides."""
    LEAVE = "leave"
    EXTRA_HOURS = "extra_hours"
    MODIFIED = "modified"


class TimeSlotStatus(str, Enum):
    """Time slot statuses."""
    AVAILABLE = "available"
    BOOKED = "booked"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class AppointmentType(str, Enum):
    """Types of appointments."""
    CONSULTATION = "consultation"
    FOLLOW_UP = "follow_up"
    EMERGENCY = "emergency"
    PROCEDURE = "procedure"


class AppointmentStatus(str, Enum):
    """Appointment statuses."""
    SCHEDULED = "scheduled"
    CONFIRMED = "confirmed"
    CHECKED_IN = "checked_in"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


class MedicalRecordStatus(str, Enum):
    """Medical record statuses."""
    DRAFT = "draft"
    FINALIZED = "finalized"
    AMENDED = "amended"


class PrescriptionStatus(str, Enum):
    """Prescription statuses."""
    ACTIVE = "active"
    PARTIALLY_DISPENSED = "partially_dispensed"
    FULLY_DISPENSED = "fully_dispensed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class DispenseStatus(str, Enum):
    """Dispense statuses for prescription items."""
    PENDING = "pending"
    PARTIAL = "partial"
    COMPLETE = "complete"


class DispenseLogStatus(str, Enum):
    """Dispense log statuses."""
    DISPENSED = "dispensed"
    RETURNED = "returned"
    CANCELLED = "cancelled"


class LabPriority(str, Enum):
    """Lab test priorities."""
    ROUTINE = "routine"
    URGENT = "urgent"
    STAT = "stat"


class LabTestStatus(str, Enum):
    """Lab test statuses."""
    ORDERED = "ordered"
    SAMPLE_PENDING = "sample_pending"
    SAMPLE_COLLECTED = "sample_collected"
    PROCESSING = "processing"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class SampleType(str, Enum):
    """Sample types for lab tests."""
    BLOOD = "blood"
    URINE = "urine"
    STOOL = "stool"
    TISSUE = "tissue"
    SWAB = "swab"
    SALIVA = "saliva"
    CSF = "csf"
    OTHER = "other"


class StorageCondition(str, Enum):
    """Storage conditions for samples."""
    ROOM_TEMP = "room_temp"
    REFRIGERATED = "refrigerated"
    FROZEN = "frozen"


class SampleStatus(str, Enum):
    """Sample statuses."""
    COLLECTED = "collected"
    IN_TRANSIT = "in_transit"
    RECEIVED = "received"
    PROCESSING = "processing"
    ANALYZED = "analyzed"
    DISPOSED = "disposed"
    REJECTED = "rejected"


class RoomType(str, Enum):
    """Room types."""
    GENERAL = "general"
    SEMI_PRIVATE = "semi_private"
    PRIVATE = "private"
    ICU = "icu"
    NICU = "nicu"
    OPERATION = "operation"
    EMERGENCY = "emergency"


class RoomStatus(str, Enum):
    """Room statuses."""
    AVAILABLE = "available"
    OCCUPIED = "occupied"
    MAINTENANCE = "maintenance"
    RESERVED = "reserved"


class BedStatus(str, Enum):
    """Bed statuses."""
    AVAILABLE = "available"
    OCCUPIED = "occupied"
    RESERVED = "reserved"
    MAINTENANCE = "maintenance"


class AdmissionStatus(str, Enum):
    """Admission statuses."""
    ADMITTED = "admitted"
    DISCHARGED = "discharged"
    TRANSFERRED = "transferred"
    DECEASED = "deceased"


class AdmissionType(str, Enum):
    """Admission types."""
    EMERGENCY = "emergency"
    ELECTIVE = "elective"
    TRANSFER = "transfer"


class PaymentStatus(str, Enum):
    """Payment statuses for bills."""
    PENDING = "pending"
    PARTIAL = "partial"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class PaymentMethod(str, Enum):
    """Payment methods."""
    CASH = "cash"
    CARD = "card"
    BANK_TRANSFER = "bank_transfer"
    MOBILE_BANKING = "mobile_banking"
    CHEQUE = "cheque"


class PaymentTransactionStatus(str, Enum):
    """Payment transaction statuses."""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class BillItemType(str, Enum):
    """Bill item types."""
    CONSULTATION = "consultation"
    LAB_TEST = "lab_test"
    MEDICINE = "medicine"
    ROOM = "room"
    PROCEDURE = "procedure"
    OTHER = "other"


class NotificationType(str, Enum):
    """Notification types."""
    APPOINTMENT = "appointment"
    LAB_RESULT = "lab_result"
    PRESCRIPTION = "prescription"
    BILLING = "billing"
    SYSTEM = "system"
    REMINDER = "reminder"


class NotificationPriority(str, Enum):
    """Notification priorities."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class NotificationChannel(str, Enum):
    """Notification channels."""
    IN_APP = "in_app"
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"


class AuditAction(str, Enum):
    """Audit log actions."""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    EXPORT = "export"
    PRINT = "print"


class AuditStatus(str, Enum):
    """Audit log statuses."""
    SUCCESS = "success"
    FAILURE = "failure"


class DosageForm(str, Enum):
    """Medicine dosage forms."""
    TABLET = "tablet"
    CAPSULE = "capsule"
    SYRUP = "syrup"
    INJECTION = "injection"
    CREAM = "cream"
    OINTMENT = "ointment"
    DROPS = "drops"
    INHALER = "inhaler"
    POWDER = "powder"
    OTHER = "other"


class InventoryStatus(str, Enum):
    """Inventory statuses."""
    IN_STOCK = "in_stock"
    LOW_STOCK = "low_stock"
    OUT_OF_STOCK = "out_of_stock"
    EXPIRED = "expired"
