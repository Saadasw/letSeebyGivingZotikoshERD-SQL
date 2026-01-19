"""
Pytest configuration and fixtures.
"""
import asyncio
from typing import AsyncGenerator, Generator
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.database import Base, get_db
from app.core.security import get_password_hash
from app.main import app
from app.models.user import User
from app.models.enums import UserRole


# Test database URL (use a separate test database)
TEST_DATABASE_URL = settings.DATABASE_URL.replace(
    settings.DATABASE_URL.split("/")[-1],
    "test_" + settings.DATABASE_URL.split("/")[-1]
)

# Create test engine
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    poolclass=NullPool,
)

# Create test session maker
TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestSessionLocal() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create test HTTP client."""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_admin(db_session: AsyncSession) -> User:
    """Create a test admin user."""
    admin = User(
        id=uuid4(),
        email="admin@test.com",
        password_hash=get_password_hash("testpassword"),
        role=UserRole.ADMIN,
        is_active=True,
        is_verified=True,
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    return admin


@pytest_asyncio.fixture
async def test_doctor(db_session: AsyncSession) -> User:
    """Create a test doctor user."""
    doctor = User(
        id=uuid4(),
        email="doctor@test.com",
        password_hash=get_password_hash("testpassword"),
        role=UserRole.DOCTOR,
        is_active=True,
        is_verified=True,
    )
    db_session.add(doctor)
    await db_session.commit()
    await db_session.refresh(doctor)
    return doctor


@pytest_asyncio.fixture
async def test_patient(db_session: AsyncSession) -> User:
    """Create a test patient user."""
    patient = User(
        id=uuid4(),
        email="patient@test.com",
        password_hash=get_password_hash("testpassword"),
        role=UserRole.PATIENT,
        is_active=True,
        is_verified=True,
    )
    db_session.add(patient)
    await db_session.commit()
    await db_session.refresh(patient)
    return patient


@pytest_asyncio.fixture
async def admin_token(client: AsyncClient, test_admin: User) -> str:
    """Get admin authentication token."""
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "admin@test.com",
            "password": "testpassword",
        }
    )
    return response.json()["access_token"]


@pytest_asyncio.fixture
async def doctor_token(client: AsyncClient, test_doctor: User) -> str:
    """Get doctor authentication token."""
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "doctor@test.com",
            "password": "testpassword",
        }
    )
    return response.json()["access_token"]


@pytest_asyncio.fixture
async def patient_token(client: AsyncClient, test_patient: User) -> str:
    """Get patient authentication token."""
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "patient@test.com",
            "password": "testpassword",
        }
    )
    return response.json()["access_token"]


def auth_header(token: str) -> dict:
    """Create authorization header."""
    return {"Authorization": f"Bearer {token}"}
