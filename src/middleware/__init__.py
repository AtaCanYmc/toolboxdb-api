from starlette.middleware.cors import CORSMiddleware

from .middleware import LoggingAndCorrelationMiddleware, get_correlation_id
from .rate_limit import RateLimitMiddleware, RATE_LIMIT_CONFIG


def add_middleware(app):
    """
    Register all middleware in the correct order.
    
    Order matters:
    1. CORS middleware (outermost, handles preflight)
    2. Rate Limiting middleware (checks limits before logging)
    3. Correlation ID middleware (adds context to all requests)
    """
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(LoggingAndCorrelationMiddleware)


__all__ = ["add_middleware", "get_correlation_id", "RateLimitMiddleware", "RATE_LIMIT_CONFIG"]
