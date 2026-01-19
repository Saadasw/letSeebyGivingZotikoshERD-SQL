"""
Script to create an admin user.

Usage:
    python -m scripts.create_admin
"""
import asyncio
import sys
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_maker
from app.core.security import get_password_hash
from app.models.user import User
from app.models.enums import UserRole


async def create_admin_user(
    email: str,
    password: str,
    phone: str | None = None,
) -> User:
    """Create an admin user in the database."""
    async with async_session_maker() as session:
        # Check if admin already exists
        result = await session.execute(
            select(User).where(User.email == email)
        )
        existing_user = result.scalar_one_or_none()

        if existing_user:
            print(f"User with email {email} already exists.")
            return existing_user

        # Create admin user
        admin_user = User(
            id=uuid4(),
            email=email,
            password_hash=get_password_hash(password),
            role=UserRole.ADMIN,
            phone=phone,
            is_active=True,
            is_verified=True,
        )

        session.add(admin_user)
        await session.commit()
        await session.refresh(admin_user)

        print(f"Admin user created successfully!")
        print(f"  Email: {email}")
        print(f"  Role: {admin_user.role.value}")

        return admin_user


async def main():
    """Main function to create admin user."""
    print("=" * 50)
    print("Hospital Management System - Create Admin User")
    print("=" * 50)

    # Get user input
    if len(sys.argv) >= 3:
        email = sys.argv[1]
        password = sys.argv[2]
        phone = sys.argv[3] if len(sys.argv) > 3 else None
    else:
        email = input("Enter admin email: ").strip()
        password = input("Enter admin password: ").strip()
        phone = input("Enter phone (optional): ").strip() or None

    if not email or not password:
        print("Error: Email and password are required.")
        sys.exit(1)

    if len(password) < 8:
        print("Error: Password must be at least 8 characters.")
        sys.exit(1)

    await create_admin_user(email, password, phone)


if __name__ == "__main__":
    asyncio.run(main())
