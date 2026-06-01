from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from src.db import get_db
import time

core_router = APIRouter(tags=["System & Health"])


@core_router.get("/", status_code=status.HTTP_200_OK)
async def root_welcome():
    """API Karşılama ve Durum Bilgisi"""
    return {
        "project": "Akıllı Komponent Yönetimi - Prototip",
        "status": "running",
        "version": "1.0.0",
        "docs_url": "/docs"
    }


@core_router.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """
    Sistem Sağlık Kontrolü (Health Check).
    Hem API'nin hem de Supabase veritabanının ayakta olduğunu doğrular.
    """
    start_time = time.time()
    try:
        # Veritabanına çok hafif bir sorgu fırlatarak bağlantıyı test ediyoruz
        db.execute("SELECT 1")
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy (Error: {str(e)})"

    latency = round((time.time() - start_time) * 1000, 2)

    if "unhealthy" in db_status:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection is down."
        )

    return {
        "status": "healthy",
        "database": db_status,
        "latency_ms": latency
    }


# =====================================================================
# 2. ÖZELLEŞTİRİLMİŞ 404 NOT FOUND YANITI
# =====================================================================
def custom_404_handler(request, exc):
    """Sistemde bulunmayan bir URL tetiklendiğinde standart JSON döner."""
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "error": "Not Found",
            "message": f"İstediğiniz rota bulunamadı: '{request.url.path}'",
            "documentation": "/docs"
        }
    )
