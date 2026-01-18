"""Application constants."""

# ==========================================
# ID PREFIXES
# ==========================================
PATIENT_ID_PREFIX = "PAT"
EMPLOYEE_ID_PREFIX = "EMP"
APPOINTMENT_NO_PREFIX = "APT"
MEDICAL_RECORD_NO_PREFIX = "MR"
PRESCRIPTION_NO_PREFIX = "RX"
LAB_TEST_NO_PREFIX = "LAB"
ADMISSION_NO_PREFIX = "ADM"
BILL_NO_PREFIX = "BILL"
RECEIPT_NO_PREFIX = "RCP"
DISPENSE_NO_PREFIX = "DSP"
SAMPLE_NO_PREFIX = "SMP"

# ==========================================
# PAGINATION DEFAULTS
# ==========================================
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100
MIN_PAGE_SIZE = 1

# ==========================================
# TOKEN TYPES
# ==========================================
TOKEN_TYPE_ACCESS = "access"
TOKEN_TYPE_REFRESH = "refresh"

# ==========================================
# CACHE KEYS
# ==========================================
CACHE_KEY_USER_PERMISSIONS = "user_permissions:{user_id}"
CACHE_KEY_SYSTEM_SETTINGS = "system_settings"
CACHE_KEY_LAB_TEST_TYPES = "lab_test_types"
CACHE_KEY_MEDICINES = "medicines:page_{page}"

# ==========================================
# TIME CONSTANTS (in minutes)
# ==========================================
DEFAULT_SLOT_DURATION = 30
MIN_SLOT_DURATION = 5
MAX_SLOT_DURATION = 120

# Appointment
APPOINTMENT_REMINDER_HOURS = 24
APPOINTMENT_CHECKIN_WINDOW_MINUTES = 30

# ==========================================
# FILE UPLOAD
# ==========================================
ALLOWED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/gif", "image/webp"]
ALLOWED_DOCUMENT_TYPES = ["application/pdf", "image/jpeg", "image/png"]
MAX_PROFILE_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB
MAX_DOCUMENT_SIZE = 10 * 1024 * 1024  # 10MB

# ==========================================
# BLOOD GROUPS
# ==========================================
BLOOD_GROUPS = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]

# ==========================================
# MARITAL STATUS
# ==========================================
MARITAL_STATUS = ["single", "married", "divorced", "widowed", "separated"]

# ==========================================
# VISIT TYPES
# ==========================================
VISIT_TYPES = ["in_person", "video", "phone"]

# ==========================================
# MEDICINE ROUTES
# ==========================================
MEDICINE_ROUTES = [
    "oral",
    "intravenous",
    "intramuscular",
    "subcutaneous",
    "topical",
    "inhalation",
    "sublingual",
    "rectal",
    "ophthalmic",
    "otic",
    "nasal",
]

# ==========================================
# MEDICINE FREQUENCIES
# ==========================================
MEDICINE_FREQUENCIES = [
    "once_daily",
    "twice_daily",
    "thrice_daily",
    "four_times_daily",
    "every_4_hours",
    "every_6_hours",
    "every_8_hours",
    "every_12_hours",
    "as_needed",
    "at_bedtime",
]

# ==========================================
# MEAL RELATIONS
# ==========================================
MEAL_RELATIONS = [
    "before_meal",
    "after_meal",
    "with_meal",
    "empty_stomach",
    "regardless_of_meal",
]

# ==========================================
# LAB TEST CATEGORIES
# ==========================================
LAB_TEST_CATEGORIES = [
    "Hematology",
    "Biochemistry",
    "Urinalysis",
    "Serology",
    "Microbiology",
    "Cardiology",
    "Radiology",
    "Pathology",
    "Immunology",
    "Endocrinology",
]

# ==========================================
# DAYS OF WEEK
# ==========================================
DAYS_OF_WEEK = {
    0: "Sunday",
    1: "Monday",
    2: "Tuesday",
    3: "Wednesday",
    4: "Thursday",
    5: "Friday",
    6: "Saturday",
}

# ==========================================
# NOTIFICATION TEMPLATES
# ==========================================
NOTIFICATION_TEMPLATE_CODES = {
    "APPOINTMENT_REMINDER": "APT_REMINDER",
    "APPOINTMENT_CONFIRMED": "APT_CONFIRMED",
    "APPOINTMENT_CANCELLED": "APT_CANCELLED",
    "LAB_RESULT_READY": "LAB_READY",
    "PRESCRIPTION_READY": "RX_READY",
    "BILL_GENERATED": "BILL_GENERATED",
    "PAYMENT_RECEIVED": "PAYMENT_RECEIVED",
    "PASSWORD_RESET": "PASSWORD_RESET",
    "WELCOME": "WELCOME",
}

# ==========================================
# SYSTEM SETTING KEYS
# ==========================================
SETTING_HOSPITAL_NAME = "hospital_name"
SETTING_HOSPITAL_EMAIL = "hospital_email"
SETTING_HOSPITAL_PHONE = "hospital_phone"
SETTING_DEFAULT_SLOT_DURATION = "default_slot_duration"
SETTING_TAX_RATE = "tax_rate"
SETTING_CURRENCY = "currency"
SETTING_CURRENCY_SYMBOL = "currency_symbol"
