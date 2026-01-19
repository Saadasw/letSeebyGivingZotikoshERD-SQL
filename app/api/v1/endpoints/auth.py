"""
Authentication endpoints.
"""
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, get_current_active_user
from app.core.exceptions import (
    AuthenticationError,
    InvalidCredentialsError,
    TokenExpiredError,
    AccountLockedError,
    AccountInactiveError,
    ValidationError,
)
from app.api.v1.schemas.auth import (
    LoginRequest,
    LoginResponse,
    TokenResponse,
    RefreshTokenRequest,
    LogoutRequest,
    PatientRegistrationRequest,
    PasswordChangeRequest,
    PasswordResetRequest,
    PasswordResetConfirm,
    UserProfileResponse,
)
from app.api.v1.schemas.base import SuccessResponse
from app.services.auth import AuthService
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["Authentication"])


def get_client_info(request: Request) -> tuple[str, str]:
    """Extract client IP and user agent from request."""
    client_ip = request.client.host if request.client else "unknown"
    # Check for forwarded IP
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()

    user_agent = request.headers.get("User-Agent", "unknown")
    return client_ip, user_agent


@router.post("/login", response_model=LoginResponse)
async def login(
    request: Request,
    login_data: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Authenticate user and return access and refresh tokens.

    - **email**: User's email address
    - **password**: User's password
    - **remember_me**: If true, extends refresh token expiry
    """
    client_ip, user_agent = get_client_info(request)
    auth_service = AuthService(db)

    try:
        user, access_token, refresh_token = await auth_service.authenticate(
            email=login_data.email,
            password=login_data.password,
            ip_address=client_ip,
            user_agent=user_agent,
            remember_me=login_data.remember_me,
        )

        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            user=UserProfileResponse(
                id=user.id,
                email=user.email,
                role=user.role,
                is_active=user.is_active,
                is_verified=user.is_verified,
                phone=user.phone,
                created_at=user.created_at,
            ),
        )
    except InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except AccountLockedError as e:
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail=str(e),
        )
    except AccountInactiveError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive",
        )


@router.post("/login/form", response_model=LoginResponse)
async def login_form(
    request: Request,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    OAuth2 compatible login endpoint using form data.
    """
    client_ip, user_agent = get_client_info(request)
    auth_service = AuthService(db)

    try:
        user, access_token, refresh_token = await auth_service.authenticate(
            email=form_data.username,
            password=form_data.password,
            ip_address=client_ip,
            user_agent=user_agent,
        )

        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            user=UserProfileResponse(
                id=user.id,
                email=user.email,
                role=user.role,
                is_active=user.is_active,
                is_verified=user.is_verified,
                phone=user.phone,
                created_at=user.created_at,
            ),
        )
    except (InvalidCredentialsError, AccountLockedError, AccountInactiveError) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_data: RefreshTokenRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Refresh access token using refresh token.
    """
    auth_service = AuthService(db)

    try:
        access_token, new_refresh_token = await auth_service.refresh_tokens(
            refresh_token=refresh_data.refresh_token
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
        )
    except TokenExpiredError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except AuthenticationError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/logout", response_model=SuccessResponse)
async def logout(
    logout_data: LogoutRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Logout user and invalidate refresh token.
    """
    auth_service = AuthService(db)
    await auth_service.logout(logout_data.refresh_token)

    return SuccessResponse(message="Successfully logged out")


@router.post("/logout/all", response_model=SuccessResponse)
async def logout_all_sessions(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Logout from all sessions/devices.
    """
    auth_service = AuthService(db)
    await auth_service.logout_all(current_user.id)

    return SuccessResponse(message="Successfully logged out from all sessions")


@router.post("/register", response_model=LoginResponse, status_code=status.HTTP_201_CREATED)
async def register_patient(
    request: Request,
    registration_data: PatientRegistrationRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Register a new patient account.

    Only patients can self-register. Staff and doctors must be created by admins.
    """
    client_ip, user_agent = get_client_info(request)
    auth_service = AuthService(db)

    try:
        user, access_token, refresh_token = await auth_service.register_patient(
            email=registration_data.email,
            password=registration_data.password,
            phone=registration_data.phone,
            first_name=registration_data.first_name,
            last_name=registration_data.last_name,
            date_of_birth=registration_data.date_of_birth,
            gender=registration_data.gender,
            blood_group=registration_data.blood_group,
            address=registration_data.address,
            emergency_contact_name=registration_data.emergency_contact_name,
            emergency_contact_phone=registration_data.emergency_contact_phone,
            ip_address=client_ip,
            user_agent=user_agent,
        )

        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            user=UserProfileResponse(
                id=user.id,
                email=user.email,
                role=user.role,
                is_active=user.is_active,
                is_verified=user.is_verified,
                phone=user.phone,
                created_at=user.created_at,
            ),
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/password/change", response_model=SuccessResponse)
async def change_password(
    password_data: PasswordChangeRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Change current user's password.
    """
    auth_service = AuthService(db)

    try:
        await auth_service.change_password(
            user_id=current_user.id,
            current_password=password_data.current_password,
            new_password=password_data.new_password,
        )

        return SuccessResponse(message="Password changed successfully")
    except InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )


@router.post("/password/reset", response_model=SuccessResponse)
async def request_password_reset(
    reset_data: PasswordResetRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Request a password reset email.

    Always returns success even if email doesn't exist (security).
    """
    auth_service = AuthService(db)
    await auth_service.request_password_reset(reset_data.email)

    return SuccessResponse(
        message="If the email exists, a password reset link has been sent"
    )


@router.post("/password/reset/confirm", response_model=SuccessResponse)
async def confirm_password_reset(
    confirm_data: PasswordResetConfirm,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Confirm password reset with token.
    """
    auth_service = AuthService(db)

    try:
        await auth_service.reset_password(
            token=confirm_data.token,
            new_password=confirm_data.new_password,
        )

        return SuccessResponse(message="Password has been reset successfully")
    except (TokenExpiredError, AuthenticationError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )


@router.get("/me", response_model=UserProfileResponse)
async def get_current_user_profile(
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """
    Get current authenticated user's profile.
    """
    return UserProfileResponse(
        id=current_user.id,
        email=current_user.email,
        role=current_user.role,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        phone=current_user.phone,
        created_at=current_user.created_at,
    )


@router.get("/sessions")
async def get_user_sessions(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Get all active sessions for current user.
    """
    auth_service = AuthService(db)
    sessions = await auth_service.get_user_sessions(current_user.id)

    return {
        "sessions": [
            {
                "id": str(s.id),
                "ip_address": s.ip_address,
                "user_agent": s.user_agent,
                "created_at": s.created_at.isoformat(),
                "last_activity": s.last_activity.isoformat() if s.last_activity else None,
            }
            for s in sessions
        ]
    }


@router.delete("/sessions/{session_id}", response_model=SuccessResponse)
async def revoke_session(
    session_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Revoke a specific session.
    """
    from uuid import UUID

    auth_service = AuthService(db)

    try:
        session_uuid = UUID(session_id)
        await auth_service.revoke_session(current_user.id, session_uuid)
        return SuccessResponse(message="Session revoked successfully")
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid session ID",
        )
