"""Repositories package."""

from .base import BaseRepository, SoftDeleteRepository
from .user import UserRepository
from .patient import PatientRepository
from .doctor import DoctorRepository
from .staff import StaffRepository
from .branch import BranchRepository
from .appointment import AppointmentRepository, TimeSlotRepository
from .medical_record import MedicalRecordRepository, VitalsRepository
from .prescription import PrescriptionRepository
from .lab_test import LabTestRepository, LabTestTypeRepository
from .inventory import MedicineRepository, InventoryRepository
from .room import RoomRepository, BedRepository
from .admission import AdmissionRepository
from .billing import BillRepository, PaymentRepository
from .notification import NotificationRepository, NotificationTemplateRepository
from .audit import AuditLogRepository, SystemSettingRepository

__all__ = [
    "BaseRepository",
    "SoftDeleteRepository",
    "UserRepository",
    "PatientRepository",
    "DoctorRepository",
    "StaffRepository",
    "BranchRepository",
    "AppointmentRepository",
    "TimeSlotRepository",
    "MedicalRecordRepository",
    "VitalsRepository",
    "PrescriptionRepository",
    "LabTestRepository",
    "LabTestTypeRepository",
    "MedicineRepository",
    "InventoryRepository",
    "RoomRepository",
    "BedRepository",
    "AdmissionRepository",
    "BillRepository",
    "PaymentRepository",
    "NotificationRepository",
    "NotificationTemplateRepository",
    "AuditLogRepository",
    "SystemSettingRepository",
]
