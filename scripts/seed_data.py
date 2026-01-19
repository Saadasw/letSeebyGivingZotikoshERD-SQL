"""
Script to seed the database with sample data.

Usage:
    python -m scripts.seed_data
"""
import asyncio
from datetime import date, time, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select

from app.core.database import async_session_maker
from app.core.security import get_password_hash
from app.models.user import User
from app.models.branch import Branch
from app.models.patient import Patient
from app.models.doctor import Doctor, DoctorBranch, DoctorSchedule
from app.models.staff import Staff
from app.models.room import Room, Bed
from app.models.lab_test import LabTestType
from app.models.inventory import Medicine
from app.models.enums import (
    UserRole,
    Gender,
    BloodGroup,
    StaffDepartment,
    DayOfWeek,
    RoomType,
    RoomStatus,
    BedStatus,
)


async def seed_branches():
    """Seed branch data."""
    async with async_session_maker() as session:
        result = await session.execute(select(Branch))
        if result.scalars().first():
            print("Branches already seeded.")
            return

        branches = [
            Branch(
                id=uuid4(),
                branch_code="BR001",
                name="City Hospital - Main Branch",
                address="123 Healthcare Avenue",
                city="Mumbai",
                state="Maharashtra",
                country="India",
                postal_code="400001",
                phone="+91-22-12345678",
                email="main@cityhospital.com",
                is_main_branch=True,
                is_active=True,
            ),
            Branch(
                id=uuid4(),
                branch_code="BR002",
                name="City Hospital - North Branch",
                address="456 Medical Road",
                city="Mumbai",
                state="Maharashtra",
                country="India",
                postal_code="400050",
                phone="+91-22-87654321",
                email="north@cityhospital.com",
                is_main_branch=False,
                is_active=True,
            ),
        ]

        session.add_all(branches)
        await session.commit()
        print(f"Seeded {len(branches)} branches.")


async def seed_users_and_profiles():
    """Seed users with their profiles."""
    async with async_session_maker() as session:
        result = await session.execute(select(User).where(User.role == UserRole.ADMIN))
        if result.scalars().first():
            print("Users already seeded.")
            return

        # Get branch
        branch_result = await session.execute(select(Branch).where(Branch.is_main_branch == True))
        branch = branch_result.scalar_one()

        # Create admin user
        admin = User(
            id=uuid4(),
            email="admin@hospital.com",
            password_hash=get_password_hash("admin123"),
            role=UserRole.ADMIN,
            phone="+91-9876543210",
            is_active=True,
            is_verified=True,
        )
        session.add(admin)

        # Create doctors
        doctor_users = []
        doctors = []
        specializations = ["Cardiology", "Neurology", "Orthopedics", "Pediatrics", "General Medicine"]

        for i, spec in enumerate(specializations, 1):
            user = User(
                id=uuid4(),
                email=f"doctor{i}@hospital.com",
                password_hash=get_password_hash("doctor123"),
                role=UserRole.DOCTOR,
                phone=f"+91-98765432{i:02d}",
                is_active=True,
                is_verified=True,
            )
            doctor_users.append(user)
            session.add(user)

            doctor = Doctor(
                id=uuid4(),
                user_id=user.id,
                doctor_id=f"DR{i:04d}",
                first_name=f"Doctor{i}",
                last_name=spec.split()[0],
                specialization=spec,
                qualification="MBBS, MD",
                experience_years=10 + i,
                license_number=f"MED{i:05d}",
                consultation_fee=Decimal("500") + Decimal(i * 100),
                bio=f"Experienced {spec} specialist with {10+i} years of practice.",
                is_available=True,
                is_active=True,
            )
            doctors.append(doctor)
            session.add(doctor)

        await session.flush()

        # Create doctor-branch assignments and schedules
        for doctor in doctors:
            # Assign to main branch
            doctor_branch = DoctorBranch(
                id=uuid4(),
                doctor_id=doctor.id,
                branch_id=branch.id,
                is_primary=True,
            )
            session.add(doctor_branch)

            # Create schedules for weekdays
            for day in [DayOfWeek.MONDAY, DayOfWeek.TUESDAY, DayOfWeek.WEDNESDAY,
                        DayOfWeek.THURSDAY, DayOfWeek.FRIDAY]:
                schedule = DoctorSchedule(
                    id=uuid4(),
                    doctor_id=doctor.id,
                    branch_id=branch.id,
                    day_of_week=day,
                    start_time=time(9, 0),
                    end_time=time(17, 0),
                    slot_duration_minutes=30,
                    max_patients=16,
                    is_active=True,
                )
                session.add(schedule)

        # Create staff
        departments = list(StaffDepartment)
        for i, dept in enumerate(departments, 1):
            user = User(
                id=uuid4(),
                email=f"{dept.value}@hospital.com",
                password_hash=get_password_hash("staff123"),
                role=UserRole.STAFF,
                phone=f"+91-98765433{i:02d}",
                is_active=True,
                is_verified=True,
            )
            session.add(user)

            staff = Staff(
                id=uuid4(),
                user_id=user.id,
                staff_id=f"ST{i:04d}",
                first_name=f"Staff{i}",
                last_name=dept.value.title(),
                department=dept,
                position=f"Senior {dept.value.title()}",
                branch_id=branch.id,
                hire_date=date.today() - timedelta(days=365 * 2),
                is_active=True,
            )
            session.add(staff)

        # Create patients
        patient_data = [
            ("John", "Doe", Gender.MALE, BloodGroup.O_POSITIVE),
            ("Jane", "Smith", Gender.FEMALE, BloodGroup.A_POSITIVE),
            ("Robert", "Johnson", Gender.MALE, BloodGroup.B_POSITIVE),
            ("Emily", "Williams", Gender.FEMALE, BloodGroup.AB_POSITIVE),
            ("Michael", "Brown", Gender.MALE, BloodGroup.O_NEGATIVE),
        ]

        for i, (first, last, gender, blood) in enumerate(patient_data, 1):
            user = User(
                id=uuid4(),
                email=f"patient{i}@email.com",
                password_hash=get_password_hash("patient123"),
                role=UserRole.PATIENT,
                phone=f"+91-98765434{i:02d}",
                is_active=True,
                is_verified=True,
            )
            session.add(user)

            patient = Patient(
                id=uuid4(),
                user_id=user.id,
                patient_id=f"PT{i:06d}",
                first_name=first,
                last_name=last,
                date_of_birth=date(1990 - i * 5, 1, 15),
                gender=gender,
                blood_group=blood,
                address=f"{i}23 Patient Street",
                city="Mumbai",
                state="Maharashtra",
                postal_code="400001",
                emergency_contact_name=f"Emergency Contact {i}",
                emergency_contact_phone=f"+91-98765435{i:02d}",
                emergency_contact_relationship="Spouse",
                is_active=True,
            )
            session.add(patient)

        await session.commit()
        print("Seeded users and profiles.")


async def seed_rooms_and_beds():
    """Seed rooms and beds."""
    async with async_session_maker() as session:
        result = await session.execute(select(Room))
        if result.scalars().first():
            print("Rooms already seeded.")
            return

        # Get branch
        branch_result = await session.execute(select(Branch).where(Branch.is_main_branch == True))
        branch = branch_result.scalar_one()

        room_configs = [
            (RoomType.GENERAL_WARD, 5, 4, Decimal("500")),
            (RoomType.SEMI_PRIVATE, 3, 2, Decimal("1500")),
            (RoomType.PRIVATE, 5, 1, Decimal("3000")),
            (RoomType.ICU, 2, 4, Decimal("5000")),
            (RoomType.EMERGENCY, 1, 6, Decimal("2000")),
            (RoomType.CONSULTATION, 8, 0, Decimal("0")),
            (RoomType.OPERATION_THEATER, 2, 0, Decimal("10000")),
        ]

        room_number = 100
        for room_type, count, beds_per_room, rate in room_configs:
            for i in range(count):
                room_number += 1
                room = Room(
                    id=uuid4(),
                    branch_id=branch.id,
                    room_number=str(room_number),
                    room_type=room_type,
                    floor=room_number // 100,
                    building="Main",
                    capacity=beds_per_room if beds_per_room > 0 else 1,
                    daily_rate=rate,
                    status=RoomStatus.AVAILABLE,
                    facilities={"ac": True, "tv": room_type in [RoomType.PRIVATE, RoomType.SEMI_PRIVATE]},
                    is_active=True,
                )
                session.add(room)
                await session.flush()

                # Add beds
                for b in range(beds_per_room):
                    bed = Bed(
                        id=uuid4(),
                        room_id=room.id,
                        bed_number=f"{room_number}-{chr(65 + b)}",
                        status=BedStatus.AVAILABLE,
                        is_active=True,
                    )
                    session.add(bed)

        await session.commit()
        print("Seeded rooms and beds.")


async def seed_lab_test_types():
    """Seed lab test types."""
    async with async_session_maker() as session:
        result = await session.execute(select(LabTestType))
        if result.scalars().first():
            print("Lab test types already seeded.")
            return

        test_types = [
            ("CBC", "Complete Blood Count", "Hematology", "Blood", Decimal("500")),
            ("LFT", "Liver Function Test", "Biochemistry", "Blood", Decimal("800")),
            ("RFT", "Renal Function Test", "Biochemistry", "Blood", Decimal("700")),
            ("TFT", "Thyroid Function Test", "Endocrine", "Blood", Decimal("900")),
            ("LIPID", "Lipid Profile", "Biochemistry", "Blood", Decimal("600")),
            ("HBA1C", "Glycated Hemoglobin", "Diabetes", "Blood", Decimal("500")),
            ("URINE", "Urine Routine", "Microbiology", "Urine", Decimal("200")),
            ("XRAY", "X-Ray", "Radiology", "N/A", Decimal("400")),
            ("ECG", "Electrocardiogram", "Cardiology", "N/A", Decimal("300")),
            ("MRI", "MRI Scan", "Radiology", "N/A", Decimal("5000")),
        ]

        for code, name, category, sample, price in test_types:
            test_type = LabTestType(
                id=uuid4(),
                test_code=code,
                name=name,
                category=category,
                sample_type=sample,
                turnaround_time="24 hours",
                price=price,
                is_active=True,
            )
            session.add(test_type)

        await session.commit()
        print(f"Seeded {len(test_types)} lab test types.")


async def seed_medicines():
    """Seed medicines."""
    async with async_session_maker() as session:
        result = await session.execute(select(Medicine))
        if result.scalars().first():
            print("Medicines already seeded.")
            return

        medicines = [
            ("MED001", "Paracetamol 500mg", "Acetaminophen", "Painkillers", "Tablet", "500mg"),
            ("MED002", "Amoxicillin 250mg", "Amoxicillin", "Antibiotics", "Capsule", "250mg"),
            ("MED003", "Omeprazole 20mg", "Omeprazole", "Gastrointestinal", "Capsule", "20mg"),
            ("MED004", "Metformin 500mg", "Metformin", "Diabetes", "Tablet", "500mg"),
            ("MED005", "Atorvastatin 10mg", "Atorvastatin", "Cardiovascular", "Tablet", "10mg"),
            ("MED006", "Losartan 50mg", "Losartan", "Cardiovascular", "Tablet", "50mg"),
            ("MED007", "Cetirizine 10mg", "Cetirizine", "Antihistamine", "Tablet", "10mg"),
            ("MED008", "Aspirin 75mg", "Acetylsalicylic acid", "Cardiovascular", "Tablet", "75mg"),
            ("MED009", "Ibuprofen 400mg", "Ibuprofen", "Painkillers", "Tablet", "400mg"),
            ("MED010", "Azithromycin 500mg", "Azithromycin", "Antibiotics", "Tablet", "500mg"),
        ]

        for code, name, generic, category, form, strength in medicines:
            medicine = Medicine(
                id=uuid4(),
                medicine_code=code,
                name=name,
                generic_name=generic,
                category=category,
                dosage_form=form,
                strength=strength,
                manufacturer="PharmaCorp",
                requires_prescription=True,
                is_active=True,
            )
            session.add(medicine)

        await session.commit()
        print(f"Seeded {len(medicines)} medicines.")


async def main():
    """Main function to seed all data."""
    print("=" * 50)
    print("Hospital Management System - Seed Database")
    print("=" * 50)

    await seed_branches()
    await seed_users_and_profiles()
    await seed_rooms_and_beds()
    await seed_lab_test_types()
    await seed_medicines()

    print("=" * 50)
    print("Database seeding completed!")
    print("=" * 50)
    print("\nDefault credentials:")
    print("  Admin: admin@hospital.com / admin123")
    print("  Doctor: doctor1@hospital.com / doctor123")
    print("  Staff: reception@hospital.com / staff123")
    print("  Patient: patient1@email.com / patient123")


if __name__ == "__main__":
    asyncio.run(main())
