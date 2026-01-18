"""
Role-Based Access Control (RBAC) System.

This module provides:
1. Permission enum with all system permissions
2. Role-based permission mappings
3. Department-based permission mappings
4. Permission checker classes
5. Resource-level access control
"""

from enum import Enum
from typing import Any, Optional, Set, List, Dict
from uuid import UUID

from app.db.models.enums import UserRole, StaffDepartment


class Permission(str, Enum):
    """All system permissions."""

    # ==========================================
    # USER MANAGEMENT
    # ==========================================
    USER_VIEW_ALL = "user:view_all"
    USER_VIEW_SELF = "user:view_self"
    USER_CREATE_ADMIN = "user:create_admin"
    USER_CREATE_DOCTOR = "user:create_doctor"
    USER_CREATE_STAFF = "user:create_staff"
    USER_UPDATE_ANY = "user:update_any"
    USER_UPDATE_SELF = "user:update_self"
    USER_DELETE = "user:delete"
    USER_DEACTIVATE = "user:deactivate"
    USER_RESET_PASSWORD = "user:reset_password"

    # ==========================================
    # BRANCH MANAGEMENT
    # ==========================================
    BRANCH_VIEW_ALL = "branch:view_all"
    BRANCH_CREATE = "branch:create"
    BRANCH_UPDATE = "branch:update"
    BRANCH_DELETE = "branch:delete"
    BRANCH_ASSIGN_DOCTOR = "branch:assign_doctor"
    BRANCH_ASSIGN_STAFF = "branch:assign_staff"

    # ==========================================
    # DOCTOR MANAGEMENT
    # ==========================================
    DOCTOR_VIEW_ALL = "doctor:view_all"
    DOCTOR_VIEW_DETAILS = "doctor:view_details"
    DOCTOR_VIEW_SCHEDULE = "doctor:view_schedule"
    DOCTOR_UPDATE_OWN_SCHEDULE = "doctor:update_own_schedule"
    DOCTOR_UPDATE_ANY_SCHEDULE = "doctor:update_any_schedule"
    DOCTOR_SET_AVAILABILITY = "doctor:set_availability"
    DOCTOR_UPDATE_FEE = "doctor:update_fee"

    # ==========================================
    # PATIENT MANAGEMENT
    # ==========================================
    PATIENT_REGISTER_SELF = "patient:register_self"
    PATIENT_VIEW_ALL = "patient:view_all"
    PATIENT_SEARCH = "patient:search"
    PATIENT_VIEW_DETAILS = "patient:view_details"
    PATIENT_VIEW_OWN = "patient:view_own"
    PATIENT_UPDATE_ANY = "patient:update_any"
    PATIENT_UPDATE_OWN = "patient:update_own"
    PATIENT_DELETE = "patient:delete"
    PATIENT_VIEW_HISTORY = "patient:view_history"
    PATIENT_VIEW_OWN_HISTORY = "patient:view_own_history"

    # ==========================================
    # APPOINTMENT MANAGEMENT
    # ==========================================
    APPOINTMENT_VIEW_ALL = "appointment:view_all"
    APPOINTMENT_VIEW_BRANCH = "appointment:view_branch"
    APPOINTMENT_VIEW_OWN_DOCTOR = "appointment:view_own_doctor"
    APPOINTMENT_VIEW_OWN_PATIENT = "appointment:view_own_patient"
    APPOINTMENT_VIEW_SLOTS = "appointment:view_slots"
    APPOINTMENT_BOOK_ANY = "appointment:book_any"
    APPOINTMENT_BOOK_OWN = "appointment:book_own"
    APPOINTMENT_CONFIRM = "appointment:confirm"
    APPOINTMENT_CHECKIN = "appointment:checkin"
    APPOINTMENT_START = "appointment:start"
    APPOINTMENT_COMPLETE = "appointment:complete"
    APPOINTMENT_CANCEL_ANY = "appointment:cancel_any"
    APPOINTMENT_CANCEL_OWN = "appointment:cancel_own"
    APPOINTMENT_RESCHEDULE_ANY = "appointment:reschedule_any"
    APPOINTMENT_RESCHEDULE_OWN = "appointment:reschedule_own"
    APPOINTMENT_BLOCK_SLOTS = "appointment:block_slots"

    # ==========================================
    # MEDICAL RECORDS
    # ==========================================
    MEDICAL_RECORD_CREATE = "medical_record:create"
    MEDICAL_RECORD_VIEW_ALL = "medical_record:view_all"
    MEDICAL_RECORD_VIEW_ASSIGNED = "medical_record:view_assigned"
    MEDICAL_RECORD_VIEW_OWN = "medical_record:view_own"
    MEDICAL_RECORD_UPDATE = "medical_record:update"
    MEDICAL_RECORD_FINALIZE = "medical_record:finalize"
    MEDICAL_RECORD_AMEND = "medical_record:amend"
    MEDICAL_RECORD_VIEW_HISTORY = "medical_record:view_history"
    MEDICAL_RECORD_EXPORT = "medical_record:export"

    # ==========================================
    # VITALS
    # ==========================================
    VITALS_RECORD = "vitals:record"
    VITALS_VIEW_ALL = "vitals:view_all"
    VITALS_VIEW_ASSIGNED = "vitals:view_assigned"
    VITALS_VIEW_OWN = "vitals:view_own"
    VITALS_UPDATE = "vitals:update"

    # ==========================================
    # PRESCRIPTIONS
    # ==========================================
    PRESCRIPTION_CREATE = "prescription:create"
    PRESCRIPTION_VIEW_ALL = "prescription:view_all"
    PRESCRIPTION_VIEW_ASSIGNED = "prescription:view_assigned"
    PRESCRIPTION_VIEW_OWN = "prescription:view_own"
    PRESCRIPTION_UPDATE = "prescription:update"
    PRESCRIPTION_CANCEL = "prescription:cancel"
    PRESCRIPTION_DISPENSE = "prescription:dispense"
    PRESCRIPTION_VIEW_DISPENSE_HISTORY = "prescription:view_dispense_history"

    # ==========================================
    # LAB TESTS
    # ==========================================
    LAB_TEST_ORDER = "lab_test:order"
    LAB_TEST_VIEW_ALL = "lab_test:view_all"
    LAB_TEST_VIEW_ASSIGNED = "lab_test:view_assigned"
    LAB_TEST_VIEW_OWN = "lab_test:view_own"
    LAB_TEST_COLLECT_SAMPLE = "lab_test:collect_sample"
    LAB_TEST_UPDATE_SAMPLE = "lab_test:update_sample"
    LAB_TEST_ENTER_RESULTS = "lab_test:enter_results"
    LAB_TEST_VERIFY_RESULTS = "lab_test:verify_results"
    LAB_TEST_DOWNLOAD_REPORT = "lab_test:download_report"
    LAB_TEST_MANAGE_TYPES = "lab_test:manage_types"

    # ==========================================
    # MEDICINE & INVENTORY
    # ==========================================
    MEDICINE_VIEW_CATALOG = "medicine:view_catalog"
    MEDICINE_CREATE = "medicine:create"
    MEDICINE_UPDATE = "medicine:update"
    MEDICINE_DELETE = "medicine:delete"
    INVENTORY_VIEW = "inventory:view"
    INVENTORY_UPDATE = "inventory:update"
    INVENTORY_VIEW_ALERTS = "inventory:view_alerts"
    INVENTORY_ADJUST = "inventory:adjust"

    # ==========================================
    # ROOMS & BEDS
    # ==========================================
    ROOM_VIEW_ALL = "room:view_all"
    ROOM_VIEW_AVAILABLE = "room:view_available"
    ROOM_CREATE = "room:create"
    ROOM_UPDATE = "room:update"
    ROOM_DELETE = "room:delete"
    BED_VIEW = "bed:view"
    BED_UPDATE_STATUS = "bed:update_status"
    BED_CREATE = "bed:create"

    # ==========================================
    # ADMISSIONS
    # ==========================================
    ADMISSION_CREATE = "admission:create"
    ADMISSION_VIEW_ALL = "admission:view_all"
    ADMISSION_VIEW_ASSIGNED = "admission:view_assigned"
    ADMISSION_VIEW_OWN = "admission:view_own"
    ADMISSION_UPDATE = "admission:update"
    ADMISSION_DISCHARGE = "admission:discharge"
    ADMISSION_TRANSFER = "admission:transfer"

    # ==========================================
    # BILLING & PAYMENTS
    # ==========================================
    BILL_VIEW_ALL = "bill:view_all"
    BILL_VIEW_OWN = "bill:view_own"
    BILL_CREATE = "bill:create"
    BILL_UPDATE = "bill:update"
    BILL_CANCEL = "bill:cancel"
    BILL_APPLY_DISCOUNT = "bill:apply_discount"
    PAYMENT_VIEW_ALL = "payment:view_all"
    PAYMENT_VIEW_OWN = "payment:view_own"
    PAYMENT_RECORD = "payment:record"
    PAYMENT_REFUND = "payment:refund"
    INVOICE_GENERATE = "invoice:generate"

    # ==========================================
    # REPORTS & ANALYTICS
    # ==========================================
    REPORT_VIEW_DASHBOARD = "report:view_dashboard"
    REPORT_VIEW_REVENUE = "report:view_revenue"
    REPORT_VIEW_PATIENT_STATS = "report:view_patient_stats"
    REPORT_VIEW_INVENTORY = "report:view_inventory"
    REPORT_VIEW_LAB = "report:view_lab"
    REPORT_EXPORT = "report:export"

    # ==========================================
    # NOTIFICATIONS
    # ==========================================
    NOTIFICATION_VIEW_OWN = "notification:view_own"
    NOTIFICATION_MARK_READ = "notification:mark_read"
    NOTIFICATION_SEND_SYSTEM = "notification:send_system"
    NOTIFICATION_MANAGE_TEMPLATES = "notification:manage_templates"

    # ==========================================
    # SYSTEM SETTINGS
    # ==========================================
    SETTINGS_VIEW = "settings:view"
    SETTINGS_UPDATE = "settings:update"
    AUDIT_LOG_VIEW = "audit_log:view"
    AUDIT_LOG_EXPORT = "audit_log:export"


# ============================================
# ROLE-BASED PERMISSIONS
# ============================================

ROLE_PERMISSIONS: Dict[UserRole, Set[Permission]] = {
    # ADMIN - Full access
    UserRole.ADMIN: set(Permission),

    # DOCTOR
    UserRole.DOCTOR: {
        Permission.USER_VIEW_SELF,
        Permission.USER_UPDATE_SELF,
        Permission.BRANCH_VIEW_ALL,
        Permission.DOCTOR_VIEW_ALL,
        Permission.DOCTOR_VIEW_DETAILS,
        Permission.DOCTOR_VIEW_SCHEDULE,
        Permission.DOCTOR_UPDATE_OWN_SCHEDULE,
        Permission.DOCTOR_SET_AVAILABILITY,
        Permission.DOCTOR_UPDATE_FEE,
        Permission.PATIENT_VIEW_DETAILS,
        Permission.PATIENT_SEARCH,
        Permission.PATIENT_VIEW_HISTORY,
        Permission.APPOINTMENT_VIEW_OWN_DOCTOR,
        Permission.APPOINTMENT_VIEW_SLOTS,
        Permission.APPOINTMENT_BOOK_ANY,
        Permission.APPOINTMENT_CONFIRM,
        Permission.APPOINTMENT_START,
        Permission.APPOINTMENT_COMPLETE,
        Permission.APPOINTMENT_CANCEL_OWN,
        Permission.APPOINTMENT_RESCHEDULE_OWN,
        Permission.APPOINTMENT_BLOCK_SLOTS,
        Permission.MEDICAL_RECORD_CREATE,
        Permission.MEDICAL_RECORD_VIEW_ASSIGNED,
        Permission.MEDICAL_RECORD_UPDATE,
        Permission.MEDICAL_RECORD_FINALIZE,
        Permission.MEDICAL_RECORD_AMEND,
        Permission.MEDICAL_RECORD_VIEW_HISTORY,
        Permission.VITALS_RECORD,
        Permission.VITALS_VIEW_ASSIGNED,
        Permission.VITALS_UPDATE,
        Permission.PRESCRIPTION_CREATE,
        Permission.PRESCRIPTION_VIEW_ASSIGNED,
        Permission.PRESCRIPTION_UPDATE,
        Permission.PRESCRIPTION_CANCEL,
        Permission.LAB_TEST_ORDER,
        Permission.LAB_TEST_VIEW_ASSIGNED,
        Permission.LAB_TEST_VERIFY_RESULTS,
        Permission.LAB_TEST_DOWNLOAD_REPORT,
        Permission.MEDICINE_VIEW_CATALOG,
        Permission.ROOM_VIEW_ALL,
        Permission.ROOM_VIEW_AVAILABLE,
        Permission.BED_VIEW,
        Permission.ADMISSION_CREATE,
        Permission.ADMISSION_VIEW_ASSIGNED,
        Permission.ADMISSION_UPDATE,
        Permission.ADMISSION_DISCHARGE,
        Permission.ADMISSION_TRANSFER,
        Permission.REPORT_VIEW_DASHBOARD,
        Permission.REPORT_VIEW_PATIENT_STATS,
        Permission.NOTIFICATION_VIEW_OWN,
        Permission.NOTIFICATION_MARK_READ,
    },

    # STAFF - Base permissions (extended by department)
    UserRole.STAFF: {
        Permission.USER_VIEW_SELF,
        Permission.USER_UPDATE_SELF,
        Permission.BRANCH_VIEW_ALL,
        Permission.DOCTOR_VIEW_ALL,
        Permission.DOCTOR_VIEW_DETAILS,
        Permission.DOCTOR_VIEW_SCHEDULE,
        Permission.REPORT_VIEW_DASHBOARD,
        Permission.NOTIFICATION_VIEW_OWN,
        Permission.NOTIFICATION_MARK_READ,
    },

    # PATIENT - Self-service only
    UserRole.PATIENT: {
        Permission.USER_VIEW_SELF,
        Permission.USER_UPDATE_SELF,
        Permission.BRANCH_VIEW_ALL,
        Permission.DOCTOR_VIEW_ALL,
        Permission.DOCTOR_VIEW_DETAILS,
        Permission.DOCTOR_VIEW_SCHEDULE,
        Permission.PATIENT_VIEW_OWN,
        Permission.PATIENT_UPDATE_OWN,
        Permission.PATIENT_VIEW_OWN_HISTORY,
        Permission.APPOINTMENT_VIEW_OWN_PATIENT,
        Permission.APPOINTMENT_VIEW_SLOTS,
        Permission.APPOINTMENT_BOOK_OWN,
        Permission.APPOINTMENT_CANCEL_OWN,
        Permission.APPOINTMENT_RESCHEDULE_OWN,
        Permission.MEDICAL_RECORD_VIEW_OWN,
        Permission.MEDICAL_RECORD_VIEW_HISTORY,
        Permission.VITALS_VIEW_OWN,
        Permission.PRESCRIPTION_VIEW_OWN,
        Permission.PRESCRIPTION_VIEW_DISPENSE_HISTORY,
        Permission.LAB_TEST_VIEW_OWN,
        Permission.LAB_TEST_DOWNLOAD_REPORT,
        Permission.MEDICINE_VIEW_CATALOG,
        Permission.ADMISSION_VIEW_OWN,
        Permission.BILL_VIEW_OWN,
        Permission.PAYMENT_VIEW_OWN,
        Permission.INVOICE_GENERATE,
        Permission.REPORT_VIEW_DASHBOARD,
        Permission.NOTIFICATION_VIEW_OWN,
        Permission.NOTIFICATION_MARK_READ,
    },
}


# ============================================
# DEPARTMENT-BASED PERMISSIONS
# ============================================

DEPARTMENT_PERMISSIONS: Dict[StaffDepartment, Set[Permission]] = {
    StaffDepartment.RECEPTION: {
        Permission.PATIENT_VIEW_ALL,
        Permission.PATIENT_SEARCH,
        Permission.PATIENT_VIEW_DETAILS,
        Permission.PATIENT_UPDATE_ANY,
        Permission.APPOINTMENT_VIEW_ALL,
        Permission.APPOINTMENT_VIEW_BRANCH,
        Permission.APPOINTMENT_VIEW_SLOTS,
        Permission.APPOINTMENT_BOOK_ANY,
        Permission.APPOINTMENT_CONFIRM,
        Permission.APPOINTMENT_CHECKIN,
        Permission.APPOINTMENT_CANCEL_ANY,
        Permission.APPOINTMENT_RESCHEDULE_ANY,
        Permission.ROOM_VIEW_ALL,
        Permission.ROOM_VIEW_AVAILABLE,
        Permission.REPORT_VIEW_PATIENT_STATS,
    },

    StaffDepartment.LABORATORY: {
        Permission.PATIENT_SEARCH,
        Permission.PATIENT_VIEW_DETAILS,
        Permission.LAB_TEST_VIEW_ALL,
        Permission.LAB_TEST_COLLECT_SAMPLE,
        Permission.LAB_TEST_UPDATE_SAMPLE,
        Permission.LAB_TEST_ENTER_RESULTS,
        Permission.LAB_TEST_VERIFY_RESULTS,
        Permission.LAB_TEST_DOWNLOAD_REPORT,
        Permission.REPORT_VIEW_LAB,
    },

    StaffDepartment.PHARMACY: {
        Permission.PATIENT_SEARCH,
        Permission.PATIENT_VIEW_DETAILS,
        Permission.PRESCRIPTION_VIEW_ALL,
        Permission.PRESCRIPTION_DISPENSE,
        Permission.PRESCRIPTION_VIEW_DISPENSE_HISTORY,
        Permission.MEDICINE_VIEW_CATALOG,
        Permission.MEDICINE_CREATE,
        Permission.MEDICINE_UPDATE,
        Permission.INVENTORY_VIEW,
        Permission.INVENTORY_UPDATE,
        Permission.INVENTORY_VIEW_ALERTS,
        Permission.INVENTORY_ADJUST,
        Permission.REPORT_VIEW_INVENTORY,
    },

    StaffDepartment.BILLING: {
        Permission.PATIENT_SEARCH,
        Permission.PATIENT_VIEW_DETAILS,
        Permission.APPOINTMENT_VIEW_ALL,
        Permission.ADMISSION_VIEW_ALL,
        Permission.BILL_VIEW_ALL,
        Permission.BILL_CREATE,
        Permission.BILL_UPDATE,
        Permission.BILL_APPLY_DISCOUNT,
        Permission.PAYMENT_VIEW_ALL,
        Permission.PAYMENT_RECORD,
        Permission.INVOICE_GENERATE,
        Permission.REPORT_VIEW_REVENUE,
    },

    StaffDepartment.NURSING: {
        Permission.PATIENT_VIEW_ALL,
        Permission.PATIENT_SEARCH,
        Permission.PATIENT_VIEW_DETAILS,
        Permission.PATIENT_VIEW_HISTORY,
        Permission.APPOINTMENT_VIEW_ALL,
        Permission.APPOINTMENT_VIEW_BRANCH,
        Permission.APPOINTMENT_CHECKIN,
        Permission.MEDICAL_RECORD_VIEW_ASSIGNED,
        Permission.VITALS_RECORD,
        Permission.VITALS_VIEW_ALL,
        Permission.VITALS_UPDATE,
        Permission.PRESCRIPTION_VIEW_ALL,
        Permission.ROOM_VIEW_ALL,
        Permission.ROOM_VIEW_AVAILABLE,
        Permission.BED_VIEW,
        Permission.BED_UPDATE_STATUS,
        Permission.ADMISSION_VIEW_ALL,
        Permission.ADMISSION_UPDATE,
        Permission.REPORT_VIEW_PATIENT_STATS,
    },

    StaffDepartment.HOUSEKEEPING: {
        Permission.ROOM_VIEW_ALL,
        Permission.ROOM_UPDATE,
        Permission.BED_VIEW,
        Permission.BED_UPDATE_STATUS,
        Permission.ADMISSION_VIEW_ALL,
    },

    StaffDepartment.RADIOLOGY: {
        Permission.PATIENT_SEARCH,
        Permission.PATIENT_VIEW_DETAILS,
        Permission.LAB_TEST_VIEW_ALL,
        Permission.LAB_TEST_COLLECT_SAMPLE,
        Permission.LAB_TEST_UPDATE_SAMPLE,
        Permission.LAB_TEST_ENTER_RESULTS,
        Permission.LAB_TEST_DOWNLOAD_REPORT,
        Permission.APPOINTMENT_VIEW_ALL,
        Permission.REPORT_VIEW_LAB,
    },

    StaffDepartment.RECORDS: {
        Permission.PATIENT_VIEW_ALL,
        Permission.PATIENT_SEARCH,
        Permission.PATIENT_VIEW_DETAILS,
        Permission.PATIENT_VIEW_HISTORY,
        Permission.MEDICAL_RECORD_VIEW_ALL,
        Permission.MEDICAL_RECORD_VIEW_HISTORY,
        Permission.MEDICAL_RECORD_EXPORT,
        Permission.PRESCRIPTION_VIEW_ALL,
        Permission.LAB_TEST_VIEW_ALL,
        Permission.ADMISSION_VIEW_ALL,
        Permission.REPORT_VIEW_PATIENT_STATS,
        Permission.REPORT_EXPORT,
    },

    StaffDepartment.IT: {
        Permission.SETTINGS_VIEW,
        Permission.SETTINGS_UPDATE,
        Permission.AUDIT_LOG_VIEW,
        Permission.AUDIT_LOG_EXPORT,
        Permission.NOTIFICATION_SEND_SYSTEM,
        Permission.NOTIFICATION_MANAGE_TEMPLATES,
        Permission.REPORT_VIEW_DASHBOARD,
        Permission.REPORT_EXPORT,
    },

    StaffDepartment.HR: {
        Permission.USER_VIEW_ALL,
        Permission.REPORT_VIEW_DASHBOARD,
    },

    StaffDepartment.GENERAL: set(),  # No additional permissions
}


# ============================================
# PERMISSION CHECKER CLASS
# ============================================

class PermissionChecker:
    """Check user permissions based on role and department."""

    def __init__(self, user: Any):
        """
        Initialize with user object.

        User should have:
        - role: UserRole
        - staff_profile.department: StaffDepartment (if role is STAFF)
        """
        self.user = user
        self.role = UserRole(user.role) if isinstance(user.role, str) else user.role
        self._permissions = self._build_permissions()

    def _build_permissions(self) -> Set[Permission]:
        """Build complete permission set for user."""
        permissions = ROLE_PERMISSIONS.get(self.role, set()).copy()

        if self.role == UserRole.STAFF:
            staff_profile = getattr(self.user, "staff_profile", None)
            if staff_profile:
                department = staff_profile.department
                if isinstance(department, str):
                    department = StaffDepartment(department)
                dept_perms = DEPARTMENT_PERMISSIONS.get(department, set())
                permissions.update(dept_perms)

        return permissions

    def has_permission(self, permission: Permission) -> bool:
        """Check if user has a specific permission."""
        return permission in self._permissions

    def has_any_permission(self, *permissions: Permission) -> bool:
        """Check if user has any of the specified permissions."""
        return any(p in self._permissions for p in permissions)

    def has_all_permissions(self, *permissions: Permission) -> bool:
        """Check if user has all of the specified permissions."""
        return all(p in self._permissions for p in permissions)

    def get_permissions(self) -> Set[Permission]:
        """Get all permissions for this user."""
        return self._permissions.copy()

    def get_permissions_list(self) -> List[str]:
        """Get all permissions as a list of strings."""
        return sorted([p.value for p in self._permissions])


# ============================================
# RESOURCE ACCESS CHECKER
# ============================================

class ResourceAccessChecker:
    """Check access to specific resources based on ownership/assignment."""

    def __init__(self, user: Any):
        self.user = user
        self.role = UserRole(user.role) if isinstance(user.role, str) else user.role
        self.permission_checker = PermissionChecker(user)

    def _get_user_patient_id(self) -> Optional[UUID]:
        """Get patient profile ID if user is a patient."""
        profile = getattr(self.user, "patient_profile", None)
        return profile.id if profile else None

    def _get_user_doctor_id(self) -> Optional[UUID]:
        """Get doctor profile ID if user is a doctor."""
        profile = getattr(self.user, "doctor_profile", None)
        return profile.id if profile else None

    def _get_user_staff_id(self) -> Optional[UUID]:
        """Get staff profile ID if user is staff."""
        profile = getattr(self.user, "staff_profile", None)
        return profile.id if profile else None

    # ==========================================
    # PATIENT ACCESS
    # ==========================================

    def can_view_patient(self, patient_id: UUID) -> bool:
        """Check if user can view a patient's basic info."""
        if self.role == UserRole.ADMIN:
            return True
        if self.role == UserRole.STAFF:
            return self.permission_checker.has_permission(Permission.PATIENT_VIEW_ALL)
        if self.role == UserRole.DOCTOR:
            return self.permission_checker.has_permission(Permission.PATIENT_VIEW_DETAILS)
        if self.role == UserRole.PATIENT:
            return self._get_user_patient_id() == patient_id
        return False

    def can_view_patient_history(self, patient_id: UUID) -> bool:
        """Check if user can view a patient's medical history."""
        if self.role == UserRole.ADMIN:
            return True
        if self.role == UserRole.DOCTOR:
            return self.permission_checker.has_permission(Permission.PATIENT_VIEW_HISTORY)
        if self.role == UserRole.STAFF:
            return self.permission_checker.has_permission(Permission.PATIENT_VIEW_HISTORY)
        if self.role == UserRole.PATIENT:
            return self._get_user_patient_id() == patient_id
        return False

    def can_update_patient(self, patient_id: UUID) -> bool:
        """Check if user can update a patient's profile."""
        if self.role == UserRole.ADMIN:
            return True
        if self.role == UserRole.STAFF:
            return self.permission_checker.has_permission(Permission.PATIENT_UPDATE_ANY)
        if self.role == UserRole.PATIENT:
            return self._get_user_patient_id() == patient_id
        return False

    # ==========================================
    # APPOINTMENT ACCESS
    # ==========================================

    def can_view_appointment(self, appointment: Any) -> bool:
        """Check if user can view an appointment."""
        if self.role == UserRole.ADMIN:
            return True
        if self.role == UserRole.STAFF:
            return self.permission_checker.has_any_permission(
                Permission.APPOINTMENT_VIEW_ALL,
                Permission.APPOINTMENT_VIEW_BRANCH
            )
        if self.role == UserRole.DOCTOR:
            doctor_id = self._get_user_doctor_id()
            return doctor_id and appointment.doctor_id == doctor_id
        if self.role == UserRole.PATIENT:
            patient_id = self._get_user_patient_id()
            return patient_id and appointment.patient_id == patient_id
        return False

    def can_modify_appointment(self, appointment: Any) -> bool:
        """Check if user can modify (cancel/reschedule) an appointment."""
        if self.role == UserRole.ADMIN:
            return True
        if self.role == UserRole.STAFF:
            return self.permission_checker.has_permission(Permission.APPOINTMENT_CANCEL_ANY)
        if self.role == UserRole.DOCTOR:
            doctor_id = self._get_user_doctor_id()
            return doctor_id and appointment.doctor_id == doctor_id
        if self.role == UserRole.PATIENT:
            patient_id = self._get_user_patient_id()
            return patient_id and appointment.patient_id == patient_id
        return False

    # ==========================================
    # MEDICAL RECORD ACCESS
    # ==========================================

    def can_view_medical_record(self, record: Any) -> bool:
        """Check if user can view a medical record."""
        if self.role == UserRole.ADMIN:
            return True
        if self.role == UserRole.DOCTOR:
            doctor_id = self._get_user_doctor_id()
            return doctor_id and record.doctor_id == doctor_id
        if self.role == UserRole.STAFF:
            return self.permission_checker.has_permission(Permission.MEDICAL_RECORD_VIEW_ALL)
        if self.role == UserRole.PATIENT:
            patient_id = self._get_user_patient_id()
            return patient_id and record.patient_id == patient_id
        return False

    def can_update_medical_record(self, record: Any) -> bool:
        """Check if user can update a medical record."""
        if self.role == UserRole.ADMIN:
            return True
        if self.role == UserRole.DOCTOR:
            doctor_id = self._get_user_doctor_id()
            return doctor_id and record.doctor_id == doctor_id
        return False

    # ==========================================
    # PRESCRIPTION ACCESS
    # ==========================================

    def can_view_prescription(self, prescription: Any) -> bool:
        """Check if user can view a prescription."""
        if self.role == UserRole.ADMIN:
            return True
        if self.role == UserRole.DOCTOR:
            doctor_id = self._get_user_doctor_id()
            return doctor_id and prescription.doctor_id == doctor_id
        if self.role == UserRole.STAFF:
            return self.permission_checker.has_permission(Permission.PRESCRIPTION_VIEW_ALL)
        if self.role == UserRole.PATIENT:
            patient_id = self._get_user_patient_id()
            return patient_id and prescription.patient_id == patient_id
        return False

    def can_dispense_prescription(self) -> bool:
        """Check if user can dispense medicine for a prescription."""
        if self.role == UserRole.ADMIN:
            return True
        if self.role == UserRole.STAFF:
            return self.permission_checker.has_permission(Permission.PRESCRIPTION_DISPENSE)
        return False

    # ==========================================
    # LAB TEST ACCESS
    # ==========================================

    def can_view_lab_test(self, lab_test: Any) -> bool:
        """Check if user can view a lab test."""
        if self.role == UserRole.ADMIN:
            return True
        if self.role == UserRole.DOCTOR:
            doctor_id = self._get_user_doctor_id()
            return doctor_id and lab_test.doctor_id == doctor_id
        if self.role == UserRole.STAFF:
            return self.permission_checker.has_permission(Permission.LAB_TEST_VIEW_ALL)
        if self.role == UserRole.PATIENT:
            patient_id = self._get_user_patient_id()
            return patient_id and lab_test.patient_id == patient_id
        return False

    def can_process_lab_test(self) -> bool:
        """Check if user can process (collect sample, enter results) a lab test."""
        if self.role == UserRole.STAFF:
            return self.permission_checker.has_any_permission(
                Permission.LAB_TEST_COLLECT_SAMPLE,
                Permission.LAB_TEST_ENTER_RESULTS
            )
        return False

    # ==========================================
    # BILL ACCESS
    # ==========================================

    def can_view_bill(self, bill: Any) -> bool:
        """Check if user can view a bill."""
        if self.role == UserRole.ADMIN:
            return True
        if self.role == UserRole.STAFF:
            return self.permission_checker.has_permission(Permission.BILL_VIEW_ALL)
        if self.role == UserRole.PATIENT:
            patient_id = self._get_user_patient_id()
            return patient_id and bill.patient_id == patient_id
        return False

    def can_modify_bill(self) -> bool:
        """Check if user can modify a bill."""
        if self.role == UserRole.ADMIN:
            return True
        if self.role == UserRole.STAFF:
            return self.permission_checker.has_permission(Permission.BILL_UPDATE)
        return False

    # ==========================================
    # ADMISSION ACCESS
    # ==========================================

    def can_view_admission(self, admission: Any) -> bool:
        """Check if user can view an admission."""
        if self.role == UserRole.ADMIN:
            return True
        if self.role == UserRole.DOCTOR:
            doctor_id = self._get_user_doctor_id()
            return doctor_id and admission.doctor_id == doctor_id
        if self.role == UserRole.STAFF:
            return self.permission_checker.has_permission(Permission.ADMISSION_VIEW_ALL)
        if self.role == UserRole.PATIENT:
            patient_id = self._get_user_patient_id()
            return patient_id and admission.patient_id == patient_id
        return False
