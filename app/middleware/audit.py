"""
Audit Middleware.

Logs API requests for audit purposes.
"""
import time
import logging
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)


class AuditMiddleware(BaseHTTPMiddleware):
    """Middleware to log API requests for auditing."""

    # Paths to skip auditing
    SKIP_PATHS = {
        "/health",
        "/",
        "/api/v1/docs",
        "/api/v1/redoc",
        "/api/v1/openapi.json",
    }

    # Methods that modify data
    AUDIT_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process the request and log audit information."""
        # Skip certain paths
        if request.url.path in self.SKIP_PATHS:
            return await call_next(request)

        # Record start time
        start_time = time.time()

        # Get request information
        request_id = getattr(request.state, "request_id", "unknown")
        client_ip = request.client.host if request.client else "unknown"
        method = request.method
        path = request.url.path
        query_params = str(request.query_params) if request.query_params else ""

        # Process request
        try:
            response = await call_next(request)
            status_code = response.status_code
            error = None
        except Exception as e:
            status_code = 500
            error = str(e)
            raise

        finally:
            # Calculate duration
            duration = time.time() - start_time

            # Log audit information
            log_data = {
                "request_id": request_id,
                "client_ip": client_ip,
                "method": method,
                "path": path,
                "query_params": query_params,
                "status_code": status_code,
                "duration_ms": round(duration * 1000, 2),
            }

            if error:
                log_data["error"] = error

            # Get user ID if authenticated
            if hasattr(request.state, "user_id"):
                log_data["user_id"] = str(request.state.user_id)

            # Log based on method and status
            if method in self.AUDIT_METHODS:
                if status_code >= 400:
                    logger.warning("API Request: %s", log_data)
                else:
                    logger.info("API Request: %s", log_data)
            elif status_code >= 400:
                logger.warning("API Request: %s", log_data)
            else:
                logger.debug("API Request: %s", log_data)

        return response
