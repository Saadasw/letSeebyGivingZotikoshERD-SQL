"""Security utilities - JWT tokens and password hashing."""

from datetime import datetime, timedelta
from typing import Any, Optional
from uuid import UUID

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def create_access_token(
    subject: str | UUID,
    expires_delta: Optional[timedelta] = None,
    additional_claims: Optional[dict[str, Any]] = None,
) -> str:
    """
    Create a JWT access token.

    Args:
        subject: The subject (usually user ID)
        expires_delta: Optional custom expiration time
        additional_claims: Additional claims to include in the token

    Returns:
        Encoded JWT token string
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode = {
        "sub": str(subject),
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access",
    }

    if additional_claims:
        to_encode.update(additional_claims)

    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(
    subject: str | UUID,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create a JWT refresh token.

    Args:
        subject: The subject (usually user ID)
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT token string
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode = {
        "sub": str(subject),
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh",
    }

    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> Optional[dict[str, Any]]:
    """
    Decode and validate a JWT token.

    Args:
        token: The JWT token to decode

    Returns:
        The token payload if valid, None otherwise
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None


def create_token_pair(
    subject: str | UUID,
    additional_claims: Optional[dict[str, Any]] = None,
) -> tuple[str, str]:
    """
    Create both access and refresh tokens.

    Args:
        subject: The subject (usually user ID)
        additional_claims: Additional claims for access token

    Returns:
        Tuple of (access_token, refresh_token)
    """
    access_token = create_access_token(subject, additional_claims=additional_claims)
    refresh_token = create_refresh_token(subject)
    return access_token, refresh_token


def get_token_expiry(token: str) -> Optional[datetime]:
    """
    Get the expiration time of a token.

    Args:
        token: The JWT token

    Returns:
        The expiration datetime if valid, None otherwise
    """
    payload = decode_token(token)
    if payload and "exp" in payload:
        return datetime.fromtimestamp(payload["exp"])
    return None


def is_token_expired(token: str) -> bool:
    """
    Check if a token is expired.

    Args:
        token: The JWT token

    Returns:
        True if expired or invalid, False otherwise
    """
    expiry = get_token_expiry(token)
    if not expiry:
        return True
    return expiry < datetime.utcnow()


def get_token_subject(token: str) -> Optional[str]:
    """
    Get the subject (user ID) from a token.

    Args:
        token: The JWT token

    Returns:
        The subject if valid, None otherwise
    """
    payload = decode_token(token)
    if payload:
        return payload.get("sub")
    return None


def hash_refresh_token(token: str) -> str:
    """
    Hash a refresh token for storage.

    Args:
        token: The refresh token

    Returns:
        Hashed token
    """
    return pwd_context.hash(token)


def verify_refresh_token_hash(token: str, hashed_token: str) -> bool:
    """
    Verify a refresh token against its hash.

    Args:
        token: The plain refresh token
        hashed_token: The hashed token from storage

    Returns:
        True if matches, False otherwise
    """
    return pwd_context.verify(token, hashed_token)
