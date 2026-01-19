"""Initial schema - Hospital Management System

Revision ID: 001_initial
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create ENUM types
    op.execute("""
        CREATE TYPE user_role AS ENUM ('admin', 'doctor', 'staff', 'patient');
        CREATE TYPE staff_department AS ENUM (
            'reception', 'nursing', 'pharmacy', 'laboratory',
            'radiology', 'billing', 'housekeeping', 'security'
        );
        CREATE TYPE gender AS ENUM ('male', 'female', 'other');
        CREATE TYPE blood_group AS ENUM ('A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-');
        CREATE TYPE day_of_week AS ENUM (
            'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'
        );
        CREATE TYPE appointment_status AS ENUM (
            'scheduled', 'confirmed', 'checked_in', 'in_progress',
            'completed', 'cancelled', 'no_show', 'rescheduled'
        );
        CREATE TYPE appointment_type AS ENUM (
            'consultation', 'follow_up', 'emergency', 'routine_checkup',
            'vaccination', 'lab_test', 'procedure'
        );
        CREATE TYPE record_type AS ENUM (
            'consultation', 'diagnosis', 'treatment', 'procedure',
            'lab_result', 'imaging', 'prescription', 'note'
        );
        CREATE TYPE prescription_status AS ENUM ('active', 'completed', 'cancelled', 'expired');
        CREATE TYPE lab_test_status AS ENUM (
            'ordered', 'sample_collected', 'processing', 'completed',
            'verified', 'cancelled'
        );
        CREATE TYPE room_type AS ENUM (
            'general_ward', 'private', 'semi_private', 'icu',
            'emergency', 'operation_theater', 'consultation', 'laboratory'
        );
        CREATE TYPE room_status AS ENUM ('available', 'occupied', 'maintenance', 'reserved');
        CREATE TYPE bed_status AS ENUM ('available', 'occupied', 'maintenance', 'reserved');
        CREATE TYPE admission_status AS ENUM ('admitted', 'discharged', 'transferred', 'deceased');
        CREATE TYPE bill_status AS ENUM ('draft', 'pending', 'partial', 'paid', 'overdue', 'cancelled');
        CREATE TYPE payment_status AS ENUM ('pending', 'completed', 'failed', 'refunded');
        CREATE TYPE payment_method AS ENUM (
            'cash', 'credit_card', 'debit_card', 'insurance',
            'bank_transfer', 'upi', 'other'
        );
        CREATE TYPE notification_type AS ENUM (
            'appointment_reminder', 'appointment_confirmation', 'appointment_cancelled',
            'prescription_ready', 'lab_result_ready', 'payment_due', 'payment_received',
            'general', 'emergency', 'system'
        );
        CREATE TYPE notification_status AS ENUM ('pending', 'sent', 'read', 'failed');
    """)

    # Create branches table
    op.create_table(
        'branches',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('branch_code', sa.String(20), unique=True, nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('address', sa.Text, nullable=False),
        sa.Column('city', sa.String(50), nullable=False),
        sa.Column('state', sa.String(50)),
        sa.Column('country', sa.String(50), default='India'),
        sa.Column('postal_code', sa.String(20)),
        sa.Column('phone', sa.String(20)),
        sa.Column('email', sa.String(100)),
        sa.Column('is_main_branch', sa.Boolean, default=False),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )
    op.create_index('ix_branches_city', 'branches', ['city'])
    op.create_index('ix_branches_is_active', 'branches', ['is_active'])

    # Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String(255), unique=True, nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('role', postgresql.ENUM('admin', 'doctor', 'staff', 'patient', name='user_role', create_type=False), nullable=False),
        sa.Column('phone', sa.String(20)),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('is_verified', sa.Boolean, default=False),
        sa.Column('failed_login_attempts', sa.Integer, default=0),
        sa.Column('locked_until', sa.DateTime(timezone=True)),
        sa.Column('last_login', sa.DateTime(timezone=True)),
        sa.Column('password_changed_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )
    op.create_index('ix_users_email', 'users', ['email'])
    op.create_index('ix_users_role', 'users', ['role'])
    op.create_index('ix_users_is_active', 'users', ['is_active'])

    # Create user_sessions table
    op.create_table(
        'user_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('refresh_token_hash', sa.String(255), nullable=False),
        sa.Column('ip_address', sa.String(45)),
        sa.Column('user_agent', sa.Text),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_activity', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_user_sessions_user_id', 'user_sessions', ['user_id'])
    op.create_index('ix_user_sessions_is_active', 'user_sessions', ['is_active'])

    # Create profile_images table
    op.create_table(
        'profile_images',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=False),
        sa.Column('file_path', sa.String(500), nullable=False),
        sa.Column('file_name', sa.String(255), nullable=False),
        sa.Column('content_type', sa.String(100)),
        sa.Column('file_size', sa.Integer),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )

    # Create patients table
    op.create_table(
        'patients',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=False),
        sa.Column('patient_id', sa.String(20), unique=True, nullable=False),
        sa.Column('first_name', sa.String(50), nullable=False),
        sa.Column('last_name', sa.String(50), nullable=False),
        sa.Column('date_of_birth', sa.Date, nullable=False),
        sa.Column('gender', postgresql.ENUM('male', 'female', 'other', name='gender', create_type=False), nullable=False),
        sa.Column('blood_group', postgresql.ENUM('A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-', name='blood_group', create_type=False)),
        sa.Column('address', sa.Text),
        sa.Column('city', sa.String(50)),
        sa.Column('state', sa.String(50)),
        sa.Column('postal_code', sa.String(20)),
        sa.Column('emergency_contact_name', sa.String(100)),
        sa.Column('emergency_contact_phone', sa.String(20)),
        sa.Column('emergency_contact_relationship', sa.String(50)),
        sa.Column('insurance_provider', sa.String(100)),
        sa.Column('insurance_policy_number', sa.String(50)),
        sa.Column('allergies', postgresql.JSONB),
        sa.Column('chronic_conditions', postgresql.JSONB),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )
    op.create_index('ix_patients_patient_id', 'patients', ['patient_id'])
    op.create_index('ix_patients_last_name', 'patients', ['last_name'])
    op.create_index('ix_patients_date_of_birth', 'patients', ['date_of_birth'])

    # Create doctors table
    op.create_table(
        'doctors',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=False),
        sa.Column('doctor_id', sa.String(20), unique=True, nullable=False),
        sa.Column('first_name', sa.String(50), nullable=False),
        sa.Column('last_name', sa.String(50), nullable=False),
        sa.Column('specialization', sa.String(100), nullable=False),
        sa.Column('qualification', sa.String(200)),
        sa.Column('experience_years', sa.Integer),
        sa.Column('license_number', sa.String(50), unique=True),
        sa.Column('consultation_fee', sa.Numeric(10, 2)),
        sa.Column('bio', sa.Text),
        sa.Column('is_available', sa.Boolean, default=True),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )
    op.create_index('ix_doctors_doctor_id', 'doctors', ['doctor_id'])
    op.create_index('ix_doctors_specialization', 'doctors', ['specialization'])
    op.create_index('ix_doctors_is_available', 'doctors', ['is_available'])

    # Create doctor_branches table
    op.create_table(
        'doctor_branches',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('doctor_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('doctors.id', ondelete='CASCADE'), nullable=False),
        sa.Column('branch_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('branches.id', ondelete='CASCADE'), nullable=False),
        sa.Column('is_primary', sa.Boolean, default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint('doctor_id', 'branch_id', name='uq_doctor_branch'),
    )

    # Create doctor_schedules table
    op.create_table(
        'doctor_schedules',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('doctor_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('doctors.id', ondelete='CASCADE'), nullable=False),
        sa.Column('branch_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('branches.id', ondelete='CASCADE'), nullable=False),
        sa.Column('day_of_week', postgresql.ENUM('monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday', name='day_of_week', create_type=False), nullable=False),
        sa.Column('start_time', sa.Time, nullable=False),
        sa.Column('end_time', sa.Time, nullable=False),
        sa.Column('slot_duration_minutes', sa.Integer, default=30),
        sa.Column('max_patients', sa.Integer),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )
    op.create_index('ix_doctor_schedules_doctor_id', 'doctor_schedules', ['doctor_id'])

    # Create staff table
    op.create_table(
        'staff',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=False),
        sa.Column('staff_id', sa.String(20), unique=True, nullable=False),
        sa.Column('first_name', sa.String(50), nullable=False),
        sa.Column('last_name', sa.String(50), nullable=False),
        sa.Column('department', postgresql.ENUM('reception', 'nursing', 'pharmacy', 'laboratory', 'radiology', 'billing', 'housekeeping', 'security', name='staff_department', create_type=False), nullable=False),
        sa.Column('position', sa.String(100)),
        sa.Column('branch_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('branches.id'), nullable=False),
        sa.Column('hire_date', sa.Date),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )
    op.create_index('ix_staff_staff_id', 'staff', ['staff_id'])
    op.create_index('ix_staff_department', 'staff', ['department'])
    op.create_index('ix_staff_branch_id', 'staff', ['branch_id'])

    # Create rooms table
    op.create_table(
        'rooms',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('branch_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('branches.id', ondelete='CASCADE'), nullable=False),
        sa.Column('room_number', sa.String(20), nullable=False),
        sa.Column('room_type', postgresql.ENUM('general_ward', 'private', 'semi_private', 'icu', 'emergency', 'operation_theater', 'consultation', 'laboratory', name='room_type', create_type=False), nullable=False),
        sa.Column('floor', sa.Integer),
        sa.Column('building', sa.String(50)),
        sa.Column('capacity', sa.Integer, default=1),
        sa.Column('daily_rate', sa.Numeric(10, 2)),
        sa.Column('status', postgresql.ENUM('available', 'occupied', 'maintenance', 'reserved', name='room_status', create_type=False), default='available'),
        sa.Column('facilities', postgresql.JSONB),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.UniqueConstraint('branch_id', 'room_number', name='uq_branch_room'),
    )
    op.create_index('ix_rooms_branch_id', 'rooms', ['branch_id'])
    op.create_index('ix_rooms_room_type', 'rooms', ['room_type'])
    op.create_index('ix_rooms_status', 'rooms', ['status'])

    # Create beds table
    op.create_table(
        'beds',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('room_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('rooms.id', ondelete='CASCADE'), nullable=False),
        sa.Column('bed_number', sa.String(20), nullable=False),
        sa.Column('status', postgresql.ENUM('available', 'occupied', 'maintenance', 'reserved', name='bed_status', create_type=False), default='available'),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.UniqueConstraint('room_id', 'bed_number', name='uq_room_bed'),
    )
    op.create_index('ix_beds_room_id', 'beds', ['room_id'])
    op.create_index('ix_beds_status', 'beds', ['status'])

    # Create appointments table
    op.create_table(
        'appointments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('appointment_number', sa.String(20), unique=True, nullable=False),
        sa.Column('patient_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('patients.id', ondelete='CASCADE'), nullable=False),
        sa.Column('doctor_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('doctors.id', ondelete='CASCADE'), nullable=False),
        sa.Column('branch_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('branches.id'), nullable=False),
        sa.Column('appointment_date', sa.Date, nullable=False),
        sa.Column('appointment_time', sa.Time, nullable=False),
        sa.Column('end_time', sa.Time),
        sa.Column('appointment_type', postgresql.ENUM('consultation', 'follow_up', 'emergency', 'routine_checkup', 'vaccination', 'lab_test', 'procedure', name='appointment_type', create_type=False), nullable=False),
        sa.Column('status', postgresql.ENUM('scheduled', 'confirmed', 'checked_in', 'in_progress', 'completed', 'cancelled', 'no_show', 'rescheduled', name='appointment_status', create_type=False), default='scheduled'),
        sa.Column('reason', sa.Text),
        sa.Column('notes', sa.Text),
        sa.Column('check_in_time', sa.DateTime(timezone=True)),
        sa.Column('check_out_time', sa.DateTime(timezone=True)),
        sa.Column('room_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('rooms.id')),
        sa.Column('cancelled_at', sa.DateTime(timezone=True)),
        sa.Column('cancellation_reason', sa.Text),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )
    op.create_index('ix_appointments_patient_id', 'appointments', ['patient_id'])
    op.create_index('ix_appointments_doctor_id', 'appointments', ['doctor_id'])
    op.create_index('ix_appointments_date', 'appointments', ['appointment_date'])
    op.create_index('ix_appointments_status', 'appointments', ['status'])
    op.create_index('ix_appointments_branch_id', 'appointments', ['branch_id'])

    # Create medical_records table
    op.create_table(
        'medical_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('record_number', sa.String(30), unique=True, nullable=False),
        sa.Column('patient_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('patients.id', ondelete='CASCADE'), nullable=False),
        sa.Column('doctor_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('doctors.id'), nullable=False),
        sa.Column('appointment_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('appointments.id')),
        sa.Column('record_type', postgresql.ENUM('consultation', 'diagnosis', 'treatment', 'procedure', 'lab_result', 'imaging', 'prescription', 'note', name='record_type', create_type=False), nullable=False),
        sa.Column('record_date', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('chief_complaint', sa.Text),
        sa.Column('present_illness', sa.Text),
        sa.Column('examination_findings', sa.Text),
        sa.Column('diagnosis', sa.Text),
        sa.Column('treatment_plan', sa.Text),
        sa.Column('notes', sa.Text),
        sa.Column('attachments', postgresql.JSONB),
        sa.Column('is_confidential', sa.Boolean, default=False),
        sa.Column('version', sa.Integer, default=1),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )
    op.create_index('ix_medical_records_patient_id', 'medical_records', ['patient_id'])
    op.create_index('ix_medical_records_doctor_id', 'medical_records', ['doctor_id'])
    op.create_index('ix_medical_records_record_date', 'medical_records', ['record_date'])
    op.create_index('ix_medical_records_record_type', 'medical_records', ['record_type'])

    # Create vitals table
    op.create_table(
        'vitals',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('patient_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('patients.id', ondelete='CASCADE'), nullable=False),
        sa.Column('medical_record_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('medical_records.id')),
        sa.Column('recorded_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('recorded_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id')),
        sa.Column('temperature', sa.Numeric(4, 1)),
        sa.Column('blood_pressure_systolic', sa.Integer),
        sa.Column('blood_pressure_diastolic', sa.Integer),
        sa.Column('pulse_rate', sa.Integer),
        sa.Column('respiratory_rate', sa.Integer),
        sa.Column('oxygen_saturation', sa.Numeric(4, 1)),
        sa.Column('weight', sa.Numeric(5, 2)),
        sa.Column('height', sa.Numeric(5, 2)),
        sa.Column('bmi', sa.Numeric(4, 1)),
        sa.Column('blood_sugar', sa.Numeric(5, 1)),
        sa.Column('notes', sa.Text),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_vitals_patient_id', 'vitals', ['patient_id'])
    op.create_index('ix_vitals_recorded_at', 'vitals', ['recorded_at'])

    # Create medical_history table
    op.create_table(
        'medical_history',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('patient_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('patients.id', ondelete='CASCADE'), nullable=False),
        sa.Column('condition', sa.String(200), nullable=False),
        sa.Column('diagnosed_date', sa.Date),
        sa.Column('status', sa.String(50)),
        sa.Column('notes', sa.Text),
        sa.Column('recorded_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )
    op.create_index('ix_medical_history_patient_id', 'medical_history', ['patient_id'])

    # Create prescriptions table
    op.create_table(
        'prescriptions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('prescription_number', sa.String(30), unique=True, nullable=False),
        sa.Column('patient_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('patients.id', ondelete='CASCADE'), nullable=False),
        sa.Column('doctor_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('doctors.id'), nullable=False),
        sa.Column('medical_record_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('medical_records.id')),
        sa.Column('appointment_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('appointments.id')),
        sa.Column('prescription_date', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('status', postgresql.ENUM('active', 'completed', 'cancelled', 'expired', name='prescription_status', create_type=False), default='active'),
        sa.Column('diagnosis', sa.Text),
        sa.Column('notes', sa.Text),
        sa.Column('valid_until', sa.Date),
        sa.Column('dispensed_at', sa.DateTime(timezone=True)),
        sa.Column('dispensed_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )
    op.create_index('ix_prescriptions_patient_id', 'prescriptions', ['patient_id'])
    op.create_index('ix_prescriptions_doctor_id', 'prescriptions', ['doctor_id'])
    op.create_index('ix_prescriptions_status', 'prescriptions', ['status'])

    # Create medicines table
    op.create_table(
        'medicines',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('medicine_code', sa.String(20), unique=True, nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('generic_name', sa.String(200)),
        sa.Column('manufacturer', sa.String(100)),
        sa.Column('category', sa.String(100)),
        sa.Column('dosage_form', sa.String(50)),
        sa.Column('strength', sa.String(50)),
        sa.Column('unit', sa.String(20)),
        sa.Column('description', sa.Text),
        sa.Column('requires_prescription', sa.Boolean, default=True),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )
    op.create_index('ix_medicines_name', 'medicines', ['name'])
    op.create_index('ix_medicines_category', 'medicines', ['category'])

    # Create prescription_items table
    op.create_table(
        'prescription_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('prescription_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('prescriptions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('medicine_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('medicines.id')),
        sa.Column('medicine_name', sa.String(200), nullable=False),
        sa.Column('dosage', sa.String(100)),
        sa.Column('frequency', sa.String(100)),
        sa.Column('duration', sa.String(100)),
        sa.Column('quantity', sa.Integer),
        sa.Column('instructions', sa.Text),
        sa.Column('is_dispensed', sa.Boolean, default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_prescription_items_prescription_id', 'prescription_items', ['prescription_id'])

    # Create lab_test_types table
    op.create_table(
        'lab_test_types',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('test_code', sa.String(20), unique=True, nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('category', sa.String(100)),
        sa.Column('description', sa.Text),
        sa.Column('sample_type', sa.String(100)),
        sa.Column('preparation_instructions', sa.Text),
        sa.Column('turnaround_time', sa.String(50)),
        sa.Column('price', sa.Numeric(10, 2)),
        sa.Column('normal_range', sa.Text),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )
    op.create_index('ix_lab_test_types_category', 'lab_test_types', ['category'])

    # Create lab_tests table
    op.create_table(
        'lab_tests',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('test_number', sa.String(30), unique=True, nullable=False),
        sa.Column('patient_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('patients.id', ondelete='CASCADE'), nullable=False),
        sa.Column('doctor_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('doctors.id'), nullable=False),
        sa.Column('test_type_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('lab_test_types.id'), nullable=False),
        sa.Column('appointment_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('appointments.id')),
        sa.Column('medical_record_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('medical_records.id')),
        sa.Column('ordered_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('status', postgresql.ENUM('ordered', 'sample_collected', 'processing', 'completed', 'verified', 'cancelled', name='lab_test_status', create_type=False), default='ordered'),
        sa.Column('priority', sa.String(20), default='normal'),
        sa.Column('clinical_notes', sa.Text),
        sa.Column('sample_collected_at', sa.DateTime(timezone=True)),
        sa.Column('sample_collected_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id')),
        sa.Column('result', sa.Text),
        sa.Column('result_value', sa.String(100)),
        sa.Column('result_unit', sa.String(50)),
        sa.Column('is_abnormal', sa.Boolean),
        sa.Column('result_notes', sa.Text),
        sa.Column('result_entered_at', sa.DateTime(timezone=True)),
        sa.Column('result_entered_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id')),
        sa.Column('verified_at', sa.DateTime(timezone=True)),
        sa.Column('verified_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )
    op.create_index('ix_lab_tests_patient_id', 'lab_tests', ['patient_id'])
    op.create_index('ix_lab_tests_doctor_id', 'lab_tests', ['doctor_id'])
    op.create_index('ix_lab_tests_status', 'lab_tests', ['status'])
    op.create_index('ix_lab_tests_ordered_at', 'lab_tests', ['ordered_at'])

    # Create inventory table
    op.create_table(
        'inventory',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('medicine_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('medicines.id', ondelete='CASCADE'), nullable=False),
        sa.Column('branch_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('branches.id', ondelete='CASCADE'), nullable=False),
        sa.Column('batch_number', sa.String(50)),
        sa.Column('quantity', sa.Integer, nullable=False, default=0),
        sa.Column('unit_price', sa.Numeric(10, 2)),
        sa.Column('selling_price', sa.Numeric(10, 2)),
        sa.Column('expiry_date', sa.Date),
        sa.Column('reorder_level', sa.Integer, default=10),
        sa.Column('max_stock', sa.Integer),
        sa.Column('location', sa.String(100)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.UniqueConstraint('medicine_id', 'branch_id', 'batch_number', name='uq_inventory'),
    )
    op.create_index('ix_inventory_medicine_id', 'inventory', ['medicine_id'])
    op.create_index('ix_inventory_branch_id', 'inventory', ['branch_id'])
    op.create_index('ix_inventory_expiry_date', 'inventory', ['expiry_date'])

    # Create dispense_log table
    op.create_table(
        'dispense_log',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('inventory_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('inventory.id'), nullable=False),
        sa.Column('prescription_item_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('prescription_items.id')),
        sa.Column('quantity', sa.Integer, nullable=False),
        sa.Column('dispensed_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('dispensed_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('notes', sa.Text),
    )

    # Create admissions table
    op.create_table(
        'admissions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('admission_number', sa.String(30), unique=True, nullable=False),
        sa.Column('patient_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('patients.id', ondelete='CASCADE'), nullable=False),
        sa.Column('doctor_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('doctors.id'), nullable=False),
        sa.Column('branch_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('branches.id'), nullable=False),
        sa.Column('bed_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('beds.id')),
        sa.Column('admission_date', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('expected_discharge', sa.Date),
        sa.Column('actual_discharge', sa.DateTime(timezone=True)),
        sa.Column('admission_reason', sa.Text, nullable=False),
        sa.Column('diagnosis', sa.Text),
        sa.Column('status', postgresql.ENUM('admitted', 'discharged', 'transferred', 'deceased', name='admission_status', create_type=False), default='admitted'),
        sa.Column('discharge_summary', sa.Text),
        sa.Column('discharge_notes', sa.Text),
        sa.Column('discharged_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id')),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )
    op.create_index('ix_admissions_patient_id', 'admissions', ['patient_id'])
    op.create_index('ix_admissions_doctor_id', 'admissions', ['doctor_id'])
    op.create_index('ix_admissions_status', 'admissions', ['status'])
    op.create_index('ix_admissions_admission_date', 'admissions', ['admission_date'])

    # Create bills table
    op.create_table(
        'bills',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('bill_number', sa.String(30), unique=True, nullable=False),
        sa.Column('patient_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('patients.id', ondelete='CASCADE'), nullable=False),
        sa.Column('admission_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('admissions.id')),
        sa.Column('appointment_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('appointments.id')),
        sa.Column('branch_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('branches.id'), nullable=False),
        sa.Column('bill_date', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('due_date', sa.Date),
        sa.Column('subtotal', sa.Numeric(12, 2), nullable=False, default=0),
        sa.Column('tax_amount', sa.Numeric(12, 2), default=0),
        sa.Column('discount_amount', sa.Numeric(12, 2), default=0),
        sa.Column('total_amount', sa.Numeric(12, 2), nullable=False, default=0),
        sa.Column('paid_amount', sa.Numeric(12, 2), default=0),
        sa.Column('balance_amount', sa.Numeric(12, 2), default=0),
        sa.Column('status', postgresql.ENUM('draft', 'pending', 'partial', 'paid', 'overdue', 'cancelled', name='bill_status', create_type=False), default='draft'),
        sa.Column('notes', sa.Text),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )
    op.create_index('ix_bills_patient_id', 'bills', ['patient_id'])
    op.create_index('ix_bills_status', 'bills', ['status'])
    op.create_index('ix_bills_bill_date', 'bills', ['bill_date'])

    # Create bill_items table
    op.create_table(
        'bill_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('bill_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('bills.id', ondelete='CASCADE'), nullable=False),
        sa.Column('description', sa.String(500), nullable=False),
        sa.Column('category', sa.String(100)),
        sa.Column('quantity', sa.Integer, nullable=False, default=1),
        sa.Column('unit_price', sa.Numeric(10, 2), nullable=False),
        sa.Column('discount', sa.Numeric(10, 2), default=0),
        sa.Column('total', sa.Numeric(12, 2), nullable=False),
        sa.Column('reference_type', sa.String(50)),
        sa.Column('reference_id', postgresql.UUID(as_uuid=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_bill_items_bill_id', 'bill_items', ['bill_id'])

    # Create payments table
    op.create_table(
        'payments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('payment_number', sa.String(30), unique=True, nullable=False),
        sa.Column('bill_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('bills.id', ondelete='CASCADE'), nullable=False),
        sa.Column('amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('payment_method', postgresql.ENUM('cash', 'credit_card', 'debit_card', 'insurance', 'bank_transfer', 'upi', 'other', name='payment_method', create_type=False), nullable=False),
        sa.Column('payment_date', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('status', postgresql.ENUM('pending', 'completed', 'failed', 'refunded', name='payment_status', create_type=False), default='pending'),
        sa.Column('transaction_id', sa.String(100)),
        sa.Column('notes', sa.Text),
        sa.Column('processed_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )
    op.create_index('ix_payments_bill_id', 'payments', ['bill_id'])
    op.create_index('ix_payments_status', 'payments', ['status'])

    # Create notifications table
    op.create_table(
        'notifications',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('notification_type', postgresql.ENUM('appointment_reminder', 'appointment_confirmation', 'appointment_cancelled', 'prescription_ready', 'lab_result_ready', 'payment_due', 'payment_received', 'general', 'emergency', 'system', name='notification_type', create_type=False), nullable=False),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('message', sa.Text, nullable=False),
        sa.Column('data', postgresql.JSONB),
        sa.Column('status', postgresql.ENUM('pending', 'sent', 'read', 'failed', name='notification_status', create_type=False), default='pending'),
        sa.Column('read_at', sa.DateTime(timezone=True)),
        sa.Column('sent_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_notifications_user_id', 'notifications', ['user_id'])
    op.create_index('ix_notifications_status', 'notifications', ['status'])
    op.create_index('ix_notifications_created_at', 'notifications', ['created_at'])

    # Create notification_templates table
    op.create_table(
        'notification_templates',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(100), unique=True, nullable=False),
        sa.Column('notification_type', postgresql.ENUM('appointment_reminder', 'appointment_confirmation', 'appointment_cancelled', 'prescription_ready', 'lab_result_ready', 'payment_due', 'payment_received', 'general', 'emergency', 'system', name='notification_type', create_type=False), nullable=False),
        sa.Column('title_template', sa.String(200), nullable=False),
        sa.Column('message_template', sa.Text, nullable=False),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )

    # Create notification_preferences table
    op.create_table(
        'notification_preferences',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=False),
        sa.Column('email_enabled', sa.Boolean, default=True),
        sa.Column('sms_enabled', sa.Boolean, default=True),
        sa.Column('push_enabled', sa.Boolean, default=True),
        sa.Column('appointment_reminders', sa.Boolean, default=True),
        sa.Column('lab_results', sa.Boolean, default=True),
        sa.Column('billing_notifications', sa.Boolean, default=True),
        sa.Column('marketing', sa.Boolean, default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )

    # Create audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id')),
        sa.Column('action', sa.String(50), nullable=False),
        sa.Column('entity_type', sa.String(50), nullable=False),
        sa.Column('entity_id', postgresql.UUID(as_uuid=True)),
        sa.Column('old_values', postgresql.JSONB),
        sa.Column('new_values', postgresql.JSONB),
        sa.Column('ip_address', sa.String(45)),
        sa.Column('user_agent', sa.Text),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_audit_logs_user_id', 'audit_logs', ['user_id'])
    op.create_index('ix_audit_logs_entity', 'audit_logs', ['entity_type', 'entity_id'])
    op.create_index('ix_audit_logs_created_at', 'audit_logs', ['created_at'])
    op.create_index('ix_audit_logs_action', 'audit_logs', ['action'])

    # Create system_settings table
    op.create_table(
        'system_settings',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('key', sa.String(100), unique=True, nullable=False),
        sa.Column('value', sa.Text),
        sa.Column('value_type', sa.String(20), default='string'),
        sa.Column('category', sa.String(50)),
        sa.Column('description', sa.Text),
        sa.Column('is_public', sa.Boolean, default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )
    op.create_index('ix_system_settings_category', 'system_settings', ['category'])


def downgrade() -> None:
    # Drop all tables in reverse order
    op.drop_table('system_settings')
    op.drop_table('audit_logs')
    op.drop_table('notification_preferences')
    op.drop_table('notification_templates')
    op.drop_table('notifications')
    op.drop_table('payments')
    op.drop_table('bill_items')
    op.drop_table('bills')
    op.drop_table('admissions')
    op.drop_table('dispense_log')
    op.drop_table('inventory')
    op.drop_table('lab_tests')
    op.drop_table('lab_test_types')
    op.drop_table('prescription_items')
    op.drop_table('medicines')
    op.drop_table('prescriptions')
    op.drop_table('medical_history')
    op.drop_table('vitals')
    op.drop_table('medical_records')
    op.drop_table('appointments')
    op.drop_table('beds')
    op.drop_table('rooms')
    op.drop_table('staff')
    op.drop_table('doctor_schedules')
    op.drop_table('doctor_branches')
    op.drop_table('doctors')
    op.drop_table('patients')
    op.drop_table('profile_images')
    op.drop_table('user_sessions')
    op.drop_table('users')
    op.drop_table('branches')

    # Drop ENUM types
    op.execute("""
        DROP TYPE IF EXISTS notification_status;
        DROP TYPE IF EXISTS notification_type;
        DROP TYPE IF EXISTS payment_method;
        DROP TYPE IF EXISTS payment_status;
        DROP TYPE IF EXISTS bill_status;
        DROP TYPE IF EXISTS admission_status;
        DROP TYPE IF EXISTS bed_status;
        DROP TYPE IF EXISTS room_status;
        DROP TYPE IF EXISTS room_type;
        DROP TYPE IF EXISTS lab_test_status;
        DROP TYPE IF EXISTS prescription_status;
        DROP TYPE IF EXISTS record_type;
        DROP TYPE IF EXISTS appointment_type;
        DROP TYPE IF EXISTS appointment_status;
        DROP TYPE IF EXISTS day_of_week;
        DROP TYPE IF EXISTS blood_group;
        DROP TYPE IF EXISTS gender;
        DROP TYPE IF EXISTS staff_department;
        DROP TYPE IF EXISTS user_role;
    """)
