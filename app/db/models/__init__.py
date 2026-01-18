"""SQLAlchemy ORM Models."""

from app.db.models.enums import (
    UserRole,
    StaffDepartment,
    GenderType,
    ScheduleOverrideType,
    TimeSlotStatus,
    AppointmentType,
    AppointmentStatus,
    MedicalRecordStatus,
    PrescriptionStatus,
    DispenseStatus,
    DispenseLogStatus,
    LabPriority,
    LabTestStatus,
    SampleType,
    StorageCondition,
    SampleStatus,
    RoomType,
    RoomStatus,
    BedStatus,
    AdmissionStatus,
    AdmissionType,
    PaymentStatus,
    PaymentMethod,
    PaymentTransactionStatus,
    BillItemType,
    NotificationType,
    NotificationPriority,
    NotificationChannel,
    AuditAction,
    AuditStatus,
    DosageForm,
    InventoryStatus,
)
from app.db.models.user import User, UserSession, ProfileImage
from app.db.models.branch import Branch
from app.db.models.doctor import (
    DoctorProfile,
    DoctorBranchAssignment,
    DoctorWeeklySchedule,
    DoctorScheduleOverride,
)
from app.db.models.staff import StaffProfile
from app.db.models.patient import PatientProfile
from app.db.models.appointment import TimeSlot, Appointment
from app.db.models.medical_record import MedicalRecord, MedicalRecordHistory, Vitals
from app.db.models.medicine import Medicine
from app.db.models.prescription import Prescription, PrescriptionItem
from app.db.models.inventory import Inventory, DispenseLog
from app.db.models.lab_test import LabTestType, LabTest, LabTestSample
from app.db.models.room import Room, Bed
from app.db.models.admission import Admission
from app.db.models.billing import Bill, BillItem, Payment
from app.db.models.notification import NotificationTemplate, Notification
from app.db.models.audit import AuditLog
from app.db.models.settings import SystemSetting

__all__ = [
    # Enums
    "UserRole",
    "StaffDepartment",
    "GenderType",
    "ScheduleOverrideType",
    "TimeSlotStatus",
    "AppointmentType",
    "AppointmentStatus",
    "MedicalRecordStatus",
    "PrescriptionStatus",
    "DispenseStatus",
    "DispenseLogStatus",
    "LabPriority",
    "LabTestStatus",
    "SampleType",
    "StorageCondition",
    "SampleStatus",
    "RoomType",
    "RoomStatus",
    "BedStatus",
    "AdmissionStatus",
    "AdmissionType",
    "PaymentStatus",
    "PaymentMethod",
    "PaymentTransactionStatus",
    "BillItemType",
    "NotificationType",
    "NotificationPriority",
    "NotificationChannel",
    "AuditAction",
    "AuditStatus",
    "DosageForm",
    "InventoryStatus",
    # User Models
    "User",
    "UserSession",
    "ProfileImage",
    # Organization
    "Branch",
    # Profiles
    "DoctorProfile",
    "DoctorBranchAssignment",
    "DoctorWeeklySchedule",
    "DoctorScheduleOverride",
    "StaffProfile",
    "PatientProfile",
    # Appointments
    "TimeSlot",
    "Appointment",
    # Medical Records
    "MedicalRecord",
    "MedicalRecordHistory",
    "Vitals",
    # Medicine & Prescriptions
    "Medicine",
    "Prescription",
    "PrescriptionItem",
    # Inventory
    "Inventory",
    "DispenseLog",
    # Lab
    "LabTestType",
    "LabTest",
    "LabTestSample",
    # Rooms
    "Room",
    "Bed",
    # Admissions
    "Admission",
    # Billing
    "Bill",
    "BillItem",
    "Payment",
    # Notifications
    "NotificationTemplate",
    "Notification",
    # Audit
    "AuditLog",
    # Settings
    "SystemSetting",
]
