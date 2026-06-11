import time
import uuid
from contextvars import ContextVar
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import logging

correlation_id_ctx_var: ContextVar[str] = ContextVar("correlation_id", default="")


class CorrelationIdFilter(logging.Filter):
    def filter(self, record):
        if not hasattr(record, "correlation_id"):
            corr_id = correlation_id_ctx_var.get()
            record.correlation_id = corr_id if corr_id else "SYSTEM"
        return True


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - [%(correlation_id)s] - %(message)s",
)

for handler in logging.root.handlers:
    handler.addFilter(CorrelationIdFilter())

logger = logging.getLogger("api_tracker")


class LoggingAndCorrelationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        corr_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
        token = correlation_id_ctx_var.set(corr_id)
        start_time = time.time()

        logger.info(
            f"İstek başladı: {request.method} {request.url.path}",
            extra={"correlation_id": corr_id},
        )

        try:
            response = await call_next(request)
            process_time = round((time.time() - start_time) * 1000, 2)

            msg = (
                f"İstek bitti: {request.method} {request.url.path} - Statü: {response.status_code} - "
                f"Süre: {process_time}ms"
            )
            logger.info(msg, extra={"correlation_id": corr_id})

            response.headers["X-Correlation-ID"] = corr_id
            return response

        except Exception as e:
            process_time = round((time.time() - start_time) * 1000, 2)
            err_msg = (
                f"İstek patladı: {request.method} {request.url.path} - Hata: {str(e)} - "
                f"Süre: {process_time}ms"
            )
            logger.error(err_msg, extra={"correlation_id": corr_id}, exc_info=True)
            raise e

        finally:
            correlation_id_ctx_var.reset(token)


def get_correlation_id() -> str:
    return correlation_id_ctx_var.get()
