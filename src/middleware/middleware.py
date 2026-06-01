import time
import uuid
from contextvars import ContextVar
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import logging

logger = logging.getLogger("api_tracker")
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - [%(correlation_id)s] - %(message)s")

correlation_id_ctx_var: ContextVar[str] = ContextVar("correlation_id", default="")


class LoggingAndCorrelationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        corr_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
        token = correlation_id_ctx_var.set(corr_id)
        start_time = time.time()

        logger.info(
            f"İstek başladı: {request.method} {request.url.path}",
            extra={"correlation_id": corr_id}
        )

        try:
            response = await call_next(request)
            process_time = round((time.time() - start_time) * 1000, 2)

            logger.info(
                f"İstek bitti: {request.method} {request.url.path} - Statü: {response.status_code} - Süre: {process_time}ms",
                extra={"correlation_id": corr_id}
            )

            response.headers["X-Correlation-ID"] = corr_id
            return response

        except Exception as e:
            process_time = round((time.time() - start_time) * 1000, 2)
            logger.error(
                f"İstek patladı: {request.method} {request.url.path} - Hata: {str(e)} - Süre: {process_time}ms",
                extra={"correlation_id": corr_id},
                exc_info=True
            )
            raise e

        finally:
            correlation_id_ctx_var.reset(token)


def get_correlation_id() -> str:
    return correlation_id_ctx_var.get()
