# Hospital Management System - FastAPI Backend

A comprehensive Hospital Management System backend built with FastAPI, featuring Role-Based Access Control (RBAC), JWT authentication, and full CRUD operations for all hospital modules.

## Features

- **Role-Based Access Control (RBAC)**: 4 roles (Admin, Doctor, Staff, Patient) with 100+ granular permissions
- **Staff Departments**: 8 departments (Reception, Nursing, Pharmacy, Laboratory, Radiology, Billing, Housekeeping, Security)
- **Complete Hospital Modules**:
  - User Management & Authentication
  - Patient Management
  - Doctor Management with Schedules
  - Staff Management
  - Branch/Location Management
  - Appointment Scheduling
  - Medical Records & Vitals
  - Prescription Management
  - Lab Tests & Results
  - Inventory/Pharmacy Management
  - Room & Bed Management
  - Patient Admissions
  - Billing & Payments
  - Notifications
  - Audit Logging

## Tech Stack

- **Framework**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL with async SQLAlchemy 2.0
- **Authentication**: JWT (python-jose) with refresh tokens
- **Password Hashing**: Passlib with bcrypt
- **Migrations**: Alembic
- **Validation**: Pydantic v2
- **Async Driver**: asyncpg

## Project Structure

```
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── endpoints/      # API route handlers
│   │       ├── schemas/        # Pydantic models
│   │       └── router.py       # API router
│   ├── core/
│   │   ├── config.py           # Settings and configuration
│   │   ├── database.py         # Database connection
│   │   ├── security.py         # JWT and password utilities
│   │   ├── permissions.py      # RBAC permission system
│   │   └── exceptions.py       # Custom exceptions
│   ├── models/                 # SQLAlchemy models (33 tables)
│   ├── repositories/           # Data access layer
│   ├── services/               # Business logic layer
│   ├── middleware/             # Custom middleware
│   └── main.py                 # Application entry point
├── alembic/                    # Database migrations
├── scripts/                    # Utility scripts
├── tests/                      # Test files
├── requirements.txt            # Python dependencies
├── .env.example                # Environment variables template
└── alembic.ini                 # Alembic configuration
```

## Setup Instructions

### Prerequisites

- Python 3.11+
- PostgreSQL 14+
- pip or poetry

### 1. Clone the Repository

```bash
git clone <repository-url>
cd letSeebyGivingZotikoshERD-SQL
```

### 2. Create Virtual Environment

```bash
python -m venv venv

# On Linux/Mac
source venv/bin/activate

# On Windows
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your settings
nano .env  # or use your preferred editor
```

Required environment variables:
```env
# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/hospital_db

# Security
SECRET_KEY=your-super-secret-key-change-this
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Application
DEBUG=true
ENVIRONMENT=development
```

### 5. Create Database

```bash
# Create the PostgreSQL database
createdb hospital_db

# Or using psql
psql -U postgres -c "CREATE DATABASE hospital_db;"
```

### 6. Run Migrations

```bash
# Run all migrations
alembic upgrade head
```

### 7. Seed Sample Data (Optional)

```bash
# Seed the database with sample data
python -m scripts.seed_data
```

This creates:
- Admin user: `admin@hospital.com` / `admin123`
- Doctor users: `doctor1@hospital.com` / `doctor123`
- Staff users: `reception@hospital.com` / `staff123`
- Patient users: `patient1@email.com` / `patient123`
- Sample branches, rooms, beds, medicines, and lab test types

### 8. Run the Application

```bash
# Development mode with auto-reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Or run directly
python -m app.main
```

### 9. Access the API

- **API Documentation**: http://localhost:8000/api/v1/docs
- **ReDoc**: http://localhost:8000/api/v1/redoc
- **Health Check**: http://localhost:8000/health

## API Endpoints

### Authentication
- `POST /api/v1/auth/login` - User login
- `POST /api/v1/auth/register` - Patient registration
- `POST /api/v1/auth/refresh` - Refresh tokens
- `POST /api/v1/auth/logout` - Logout
- `GET /api/v1/auth/me` - Get current user

### Users
- `GET /api/v1/users` - List users
- `POST /api/v1/users` - Create user
- `GET /api/v1/users/{id}` - Get user
- `PUT /api/v1/users/{id}` - Update user
- `DELETE /api/v1/users/{id}` - Delete user

### Patients
- `GET /api/v1/patients` - List patients
- `POST /api/v1/patients` - Create patient
- `GET /api/v1/patients/{id}` - Get patient
- `PUT /api/v1/patients/{id}` - Update patient
- `GET /api/v1/patients/me` - Get own profile

### Doctors
- `GET /api/v1/doctors` - List doctors (public)
- `GET /api/v1/doctors/{id}` - Get doctor (public)
- `GET /api/v1/doctors/{id}/availability` - Get availability
- `GET /api/v1/doctors/{id}/schedules` - Get schedules

### Appointments
- `GET /api/v1/appointments` - List appointments
- `POST /api/v1/appointments` - Create appointment
- `POST /api/v1/appointments/book` - Book appointment (patients)
- `POST /api/v1/appointments/{id}/check-in` - Check in
- `POST /api/v1/appointments/{id}/check-out` - Check out

### Medical Records
- `GET /api/v1/medical-records` - List records
- `POST /api/v1/medical-records` - Create record
- `GET /api/v1/medical-records/patient/{id}/vitals` - Get vitals

### Prescriptions
- `GET /api/v1/prescriptions` - List prescriptions
- `POST /api/v1/prescriptions` - Create prescription
- `POST /api/v1/prescriptions/{id}/dispense` - Dispense

### Lab Tests
- `GET /api/v1/lab-tests` - List lab tests
- `POST /api/v1/lab-tests` - Order lab test
- `POST /api/v1/lab-tests/{id}/collect-sample` - Collect sample
- `POST /api/v1/lab-tests/{id}/results` - Enter results

### And more...
See the full API documentation at `/api/v1/docs`

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_auth.py -v
```

## Development

### Creating New Migrations

```bash
# Generate migration from model changes
alembic revision --autogenerate -m "Description of changes"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1
```

### Creating Admin User

```bash
python -m scripts.create_admin admin@hospital.com securepassword
```

## RBAC Permission System

The system uses a granular permission-based access control:

```python
# Permission decorators
@require_permissions(Permission.VIEW_PATIENT)
async def list_patients(...):
    ...

@require_permissions(Permission.CREATE_PRESCRIPTION)
async def create_prescription(...):
    ...
```

Roles and their key permissions:
- **Admin**: Full system access
- **Doctor**: Patient records, prescriptions, lab orders
- **Staff**: Department-specific (pharmacy dispense, lab collection, etc.)
- **Patient**: View own records, book appointments

## License

MIT License