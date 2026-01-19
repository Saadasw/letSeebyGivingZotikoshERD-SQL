"""
API v1 Router - Combines all endpoint routers.
"""
from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    users,
    patients,
    doctors,
    staff,
    branches,
    appointments,
    medical_records,
    prescriptions,
    lab_tests,
    inventory,
    rooms,
    admissions,
    billing,
    notifications,
    audit,
)

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(patients.router)
api_router.include_router(doctors.router)
api_router.include_router(staff.router)
api_router.include_router(branches.router)
api_router.include_router(appointments.router)
api_router.include_router(medical_records.router)
api_router.include_router(prescriptions.router)
api_router.include_router(lab_tests.router)
api_router.include_router(inventory.router)
api_router.include_router(rooms.router)
api_router.include_router(admissions.router)
api_router.include_router(billing.router)
api_router.include_router(notifications.router)
api_router.include_router(audit.router)
