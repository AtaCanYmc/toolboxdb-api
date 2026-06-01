from starlette.middleware.cors import CORSMiddleware

from .middleware import LoggingAndCorrelationMiddleware, get_correlation_id


def add_middleware(app):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(LoggingAndCorrelationMiddleware)


__all__ = ["add_middleware", "get_correlation_id"]
