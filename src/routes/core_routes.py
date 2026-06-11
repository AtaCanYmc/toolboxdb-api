import os
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session
from src.db import get_db
import time
from fastapi_i18n import _

load_dotenv()
core_router = APIRouter(tags=["System & Health"])


@core_router.get("/", status_code=status.HTTP_200_OK)
async def root_welcome():
    """API Karşılama ve Durum Bilgisi"""
    return {
        "project": os.getenv("APP_TITLE", "toolbox backend"),
        "status": "running",
        "version": os.getenv("APP_VERSION", "1.0.0"),
        "docs_url": "/docs",
    }


@core_router.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """
    Sistem Sağlık Kontrolü (Health Check).
    Hem API'nin hem de Supabase veritabanının ayakta olduğunu doğrular.
    """
    start_time = time.time()
    try:
        query_str = text("SELECT 1")
        db.execute(query_str)
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy (Error: {str(e)})"

    latency = round((time.time() - start_time) * 1000, 2)

    if "unhealthy" in db_status:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=_("Database connection is down."),
        )

    return {"status": "healthy", "database": db_status, "latency_ms": latency}


# =====================================================================
# 2. ÖZELLEŞTİRİLMİŞ 404 NOT FOUND YANITI
# =====================================================================
def custom_404_handler(request, exc):
    """Sistemde bulunmayan bir URL tetiklendiğinde standart JSON döner."""
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "error": "Not Found",
            "message": _(f"İstediğiniz rota bulunamadı: '{request.url.path}'"),
            "documentation": "/docs",
        },
    )
