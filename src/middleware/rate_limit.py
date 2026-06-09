"""
Rate Limiting Middleware for FastAPI - Fail-Open (High Availability) Pattern.

Implements a Fixed Window Counter algorithm using Redis atomic operations
to enforce request limits per client IP. Supports granular limits for different endpoints.

Features:
- Async Redis-based fixed-window counter algorithm
- Granular per-endpoint limits
- HTTP 429 responses with standard rate-limit headers
- **Fail-Open Resilience:** If Redis becomes unavailable (connection timeout, crash, network issue),
  the middleware gracefully degrades and allows all requests through without rate limiting.
  This prevents the rate limiter from becoming a single point of failure.
- Integrates with X-Correlation-ID for tracing
- Production-grade exception handling and logging
"""

import logging
import time
from typing import Dict, Tuple
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

logger = logging.getLogger(__name__)

# ============================================================================
# Configuration: Define rate limits per endpoint
# ============================================================================
# Format: route_pattern -> (requests_per_minute, window_size_seconds)
RATE_LIMIT_CONFIG: Dict[str, Tuple[int, int]] = {
    "/api/v1/invoices/upload": (5, 60),  # 5 req/min for heavy LLM endpoint
    "/api/v1/invoices": (20, 60),  # 20 req/min for invoice queries
    "/api/v1/components": (60, 60),  # 60 req/min for standard endpoints
    "/api/v1/categories": (60, 60),  # 60 req/min for standard endpoints
    # Default fallback: 60 requests per 60 seconds
    "default": (60, 60),
}


# ============================================================================
# Helper Functions
# ============================================================================


def get_client_identifier(request: Request) -> str:
    """
    Extract a unique identifier for the client.

    Strategy (in order of precedence):
    1. X-Forwarded-For header (for reverse proxy scenarios)
    2. Client IP from request.client
    3. Fallback to "unknown"

    Args:
        request: The incoming FastAPI request

    Returns:
        A string identifier (IP address or token)
    """
    # Check for X-Forwarded-For (reverse proxy scenario)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Take the first IP if there are multiple
        return forwarded_for.split(",")[0].strip()

    # Fall back to direct client IP
    if request.client:
        return request.client.host

    return "unknown"


def get_rate_limit_for_route(path: str) -> Tuple[int, int]:
    """
    Determine the rate limit (requests, window_size) for a given route.

    Performs prefix matching on the request path against the RATE_LIMIT_CONFIG.
    Falls back to the "default" limit if no specific route matches.

    Args:
        path: The request path (e.g., "/api/v1/invoices/upload")

    Returns:
        Tuple of (max_requests, window_size_seconds)
    """
    for route_pattern, limit_config in RATE_LIMIT_CONFIG.items():
        if route_pattern == "default":
            continue
        if path.startswith(route_pattern):
            return limit_config

    return RATE_LIMIT_CONFIG.get("default", (60, 60))


def get_correlation_id_safe(request: Request) -> str:
    """
    Safely retrieve the correlation ID from the request context.

    Returns the X-Correlation-ID header if present, otherwise 'N/A'.
    """
    return request.headers.get("X-Correlation-ID", "N/A")


# ============================================================================
# Rate Limit Middleware
# ============================================================================


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware that enforces rate limits using Redis with Fail-Open resilience.

    Algorithm: Fixed Window Counter
    - Each client gets a counter per route per minute
    - Counter is stored in Redis as "{route}:{client_id}:{window_start}"
    - On each request, increment the counter and check if it exceeds the limit
    - If exceeded, return 429 Too Many Requests
    - Counter expires after the window period

    **Fail-Open (High Availability) Behavior:**
    - If Redis is unavailable (connection error, timeout, server down), the middleware
      logs the error and allows the request to proceed without rate limiting.
    - If any Redis operation fails (INCR, EXPIRE), the middleware catches the exception,
      logs it, and allows the request through.
    - This design ensures that infrastructure issues with the cache layer do NOT impact
      the availability of your API. Valid users can always reach your service.
    - When Redis recovers, rate limiting automatically resumes without code changes.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Main middleware dispatch function.

        Intercepts the request, checks rate limits, and either:
        1. Short-circuits with HTTP 429 if limit exceeded
        2. Continues to the next handler and adds rate-limit headers to response
        3. If Redis is unavailable, seamlessly allows request through (Fail-Open)

        **Fail-Open Strategy:**
        If any exception occurs while checking rate limits (Redis unavailability,
        timeouts, connection errors), the middleware catches it, logs it, and
        allows the request to proceed. This prevents the rate limiter from
        becoming a single point of failure.

        Args:
            request: The incoming FastAPI request
            call_next: Callable to pass the request to the next middleware/handler

        Returns:
            Either a 429 response, a response with rate-limit headers,
            or the unmodified next response if rate limiting is bypassed.
        """
        # Skip rate limiting for health checks and other safe endpoints
        if self._should_skip_rate_limit(request.url.path):
            return await call_next(request)

        # Extract identifiers for rate limit key
        client_id = get_client_identifier(request)
        max_requests, window_size = get_rate_limit_for_route(request.url.path)
        correlation_id = get_correlation_id_safe(request)

        try:
            # Check rate limit (returns None if Redis is unavailable)
            limit_info = await self._check_rate_limit(
                request=request,
                client_id=client_id,
                path=request.url.path,
                max_requests=max_requests,
                window_size=window_size,
            )

            # If rate limiting was bypassed (Redis unavailable), proceed without headers
            if limit_info is None:
                logger.info(
                    f"Rate limit check bypassed for client {client_id}. "
                    f"Allowing request to proceed (Redis unavailable).",
                    extra={"correlation_id": correlation_id},
                )
                return await call_next(request)

            # If limit exceeded, return 429 Too Many Requests
            if limit_info["exceeded"]:
                log_msg = (
                    f"Rate limit exceeded for client {client_id} on {request.url.path} "
                    f"(limit: {max_requests}/{window_size}s)"
                )
                logger.warning(log_msg, extra={"correlation_id": correlation_id})

                return JSONResponse(
                    status_code=429,
                    content={
                        "error": "Too Many Requests",
                        "message": f"Rate limit exceeded. Max {max_requests} requests per {window_size} seconds.",
                        "retry_after": limit_info["retry_after"],
                    },
                    headers={
                        "X-RateLimit-Limit": str(max_requests),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(limit_info["reset_at"]),
                        "Retry-After": str(limit_info["retry_after"]),
                    },
                )

            # Limit not exceeded; proceed to handler
            response = await call_next(request)

            # Attach rate-limit headers to the response
            response.headers["X-RateLimit-Limit"] = str(max_requests)
            response.headers["X-RateLimit-Remaining"] = str(limit_info["remaining"])
            response.headers["X-RateLimit-Reset"] = str(limit_info["reset_at"])

            log_msg = (
                f"Request allowed for client {client_id} on {request.url.path} "
                f"(used: {limit_info['used']}/{max_requests})"
            )
            logger.debug(log_msg, extra={"correlation_id": correlation_id})

            return response

        except Exception as e:
            # Catch-all for any unexpected errors: fail-open and allow the request
            log_msg = (
                f"Unexpected error in rate limit middleware for client {client_id}: {str(e)}. "
                f"Allowing request to proceed (fail-open)."
            )
            logger.error(
                log_msg, extra={"correlation_id": correlation_id}, exc_info=True
            )

            # Continue without rate limiting
            return await call_next(request)

    @staticmethod
    def _should_skip_rate_limit(path: str) -> bool:
        """
        Determine if the given path should skip rate limiting.

        Paths to skip (typically health checks and utility endpoints):
        - /health
        - /docs
        - /openapi.json
        - /redoc

        Args:
            path: The request path

        Returns:
            True if the path should skip rate limiting
        """
        skip_paths = {"/health", "/docs", "/redoc", "/openapi.json"}
        return path in skip_paths

    async def _check_rate_limit(
        self,
        request: Request,
        client_id: str,
        path: str,
        max_requests: int,
        window_size: int,
    ) -> Dict | None:
        """
        Check and enforce rate limit for a client on a given path.

        Algorithm:
        1. Construct a Redis key: "{path}:{client_id}:{window_start}"
        2. Increment the counter atomically
        3. If counter > max_requests, return limit_exceeded=True
        4. Set expiry on the key to ensure cleanup

        **Fail-Open Behavior:**
        If Redis is unavailable or any operation fails, returns None instead of raising.
        The caller should treat None as "allow the request through".

        Args:
            client_id: Unique identifier for the client (IP, token, etc.)
            path: The request path
            max_requests: Maximum requests allowed in the window
            window_size: Window size in seconds

        Returns:
            Dict with keys if Redis is available:
            - exceeded: bool indicating if limit was exceeded
            - used: number of requests currently used
            - remaining: number of requests left
            - reset_at: Unix timestamp when the limit resets
            - retry_after: seconds to wait before retrying

            None if Redis is unavailable or any operation fails (fail-open).
        """
        redis_client = getattr(request.app.state, "redis", None)
        if redis_client is None:
            logger.warning(
                "Redis client not available. Rate limiting disabled (fail-open)."
            )
            return None

        try:
            # Construct rate limit key with path-based scoping
            # Window is determined by the current minute to implement fixed-window counter
            current_time = int(time.time())
            window_start = (current_time // window_size) * window_size
            redis_key = f"rate_limit:{path}:{client_id}:{window_start}"

            # Atomic increment in Redis
            current_count = await redis_client.incr(redis_key)

            # Set expiry on first request in the window
            if current_count == 1:
                await redis_client.expire(redis_key, window_size)

            # Calculate reset time (end of current window)
            reset_at = window_start + window_size
            used = current_count
            remaining = max(0, max_requests - used)
            exceeded = used > max_requests
            retry_after = reset_at - current_time if exceeded else 0

            return {
                "exceeded": exceeded,
                "used": used,
                "remaining": remaining,
                "reset_at": reset_at,
                "retry_after": retry_after,
            }

        except Exception as e:
            # Any Redis operation error (timeout, connection, etc.): fail-open
            logger.error(
                f"Redis operation failed during rate limit check: {str(e)}. "
                f"Allowing request (fail-open).",
                exc_info=True,
            )
            return None
