"""Custom exceptions for the application."""

from typing import Any, Optional


class AppException(Exception):
    """Base exception for all application errors."""

    def __init__(
        self,
        message: str = "An error occurred",
        status_code: int = 500,
        error_code: Optional[str] = None,
        details: Optional[Any] = None,
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code or "INTERNAL_ERROR"
        self.details = details
        super().__init__(self.message)

    def to_dict(self) -> dict:
        """Convert exception to dictionary for API response."""
        result = {
            "error": self.error_code,
            "message": self.message,
        }
        if self.details:
            result["details"] = self.details
        return result


class AuthenticationError(AppException):
    """Authentication failed."""

    def __init__(
        self,
        message: str = "Authentication failed",
        error_code: str = "AUTHENTICATION_ERROR",
        details: Optional[Any] = None,
    ):
        super().__init__(
            message=message,
            status_code=401,
            error_code=error_code,
            details=details,
        )


class InvalidCredentialsError(AuthenticationError):
    """Invalid login credentials."""

    def __init__(self, message: str = "Invalid email or password"):
        super().__init__(message=message, error_code="INVALID_CREDENTIALS")


class TokenExpiredError(AuthenticationError):
    """Token has expired."""

    def __init__(self, message: str = "Token has expired"):
        super().__init__(message=message, error_code="TOKEN_EXPIRED")


class InvalidTokenError(AuthenticationError):
    """Token is invalid."""

    def __init__(self, message: str = "Invalid token"):
        super().__init__(message=message, error_code="INVALID_TOKEN")


class AuthorizationError(AppException):
    """Authorization/permission denied."""

    def __init__(
        self,
        message: str = "Permission denied",
        error_code: str = "AUTHORIZATION_ERROR",
        details: Optional[Any] = None,
    ):
        super().__init__(
            message=message,
            status_code=403,
            error_code=error_code,
            details=details,
        )


class PermissionDeniedError(AuthorizationError):
    """Specific permission denied."""

    def __init__(self, permission: str = None, message: str = None):
        msg = message or f"Permission denied: {permission}" if permission else "Permission denied"
        super().__init__(message=msg, error_code="PERMISSION_DENIED")


class NotFoundError(AppException):
    """Resource not found."""

    def __init__(
        self,
        resource: str = "Resource",
        resource_id: Any = None,
        message: str = None,
    ):
        if message:
            msg = message
        elif resource_id:
            msg = f"{resource} with ID '{resource_id}' not found"
        else:
            msg = f"{resource} not found"

        super().__init__(
            message=msg,
            status_code=404,
            error_code="NOT_FOUND",
        )


class ValidationError(AppException):
    """Validation error."""

    def __init__(
        self,
        message: str = "Validation error",
        errors: Optional[list] = None,
        field: Optional[str] = None,
    ):
        details = {"errors": errors} if errors else None
        if field:
            details = details or {}
            details["field"] = field

        super().__init__(
            message=message,
            status_code=422,
            error_code="VALIDATION_ERROR",
            details=details,
        )


class ConflictError(AppException):
    """Resource conflict (e.g., duplicate)."""

    def __init__(
        self,
        message: str = "Resource already exists",
        resource: str = None,
        field: str = None,
    ):
        details = {}
        if resource:
            details["resource"] = resource
        if field:
            details["field"] = field

        super().__init__(
            message=message,
            status_code=409,
            error_code="CONFLICT",
            details=details if details else None,
        )


class DuplicateError(ConflictError):
    """Duplicate resource error."""

    def __init__(self, resource: str, field: str, value: Any = None):
        msg = f"{resource} with {field}"
        if value:
            msg += f" '{value}'"
        msg += " already exists"
        super().__init__(message=msg, resource=resource, field=field)


class BadRequestError(AppException):
    """Bad request error."""

    def __init__(
        self,
        message: str = "Bad request",
        error_code: str = "BAD_REQUEST",
        details: Optional[Any] = None,
    ):
        super().__init__(
            message=message,
            status_code=400,
            error_code=error_code,
            details=details,
        )


class BusinessLogicError(BadRequestError):
    """Business logic violation."""

    def __init__(self, message: str, error_code: str = "BUSINESS_LOGIC_ERROR"):
        super().__init__(message=message, error_code=error_code)


class SlotNotAvailableError(BusinessLogicError):
    """Time slot not available."""

    def __init__(self, message: str = "Time slot is not available"):
        super().__init__(message=message, error_code="SLOT_NOT_AVAILABLE")


class InsufficientStockError(BusinessLogicError):
    """Insufficient inventory stock."""

    def __init__(self, medicine: str = None, available: int = None, requested: int = None):
        msg = "Insufficient stock"
        if medicine:
            msg = f"Insufficient stock for {medicine}"
        details = {}
        if available is not None:
            details["available"] = available
        if requested is not None:
            details["requested"] = requested
        super().__init__(message=msg, error_code="INSUFFICIENT_STOCK")


class InvalidStateError(BusinessLogicError):
    """Invalid state transition."""

    def __init__(self, message: str, current_state: str = None, allowed_states: list = None):
        super().__init__(message=message, error_code="INVALID_STATE")


class RateLimitError(AppException):
    """Rate limit exceeded."""

    def __init__(self, message: str = "Rate limit exceeded", retry_after: int = None):
        details = {"retry_after": retry_after} if retry_after else None
        super().__init__(
            message=message,
            status_code=429,
            error_code="RATE_LIMIT_EXCEEDED",
            details=details,
        )


class ServiceUnavailableError(AppException):
    """Service temporarily unavailable."""

    def __init__(self, message: str = "Service temporarily unavailable"):
        super().__init__(
            message=message,
            status_code=503,
            error_code="SERVICE_UNAVAILABLE",
        )


class DatabaseError(AppException):
    """Database operation error."""

    def __init__(self, message: str = "Database error occurred"):
        super().__init__(
            message=message,
            status_code=500,
            error_code="DATABASE_ERROR",
        )
