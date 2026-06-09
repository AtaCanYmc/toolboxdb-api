from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from src import models, schemas
from src.db import get_db
from src.llm.llm_factory import get_llm_provider
from src.llm.llm_provider import LLMProvider
import logging
from src.middleware.middleware import get_correlation_id

logger = logging.getLogger("api_tracker")

suggestion_router = APIRouter(prefix="/api/v1/suggestions", tags=["Project Insights"])


@suggestion_router.post(
    "/project-ideas",
    response_model=schemas.ProjectSuggestionResponse,
    status_code=status.HTTP_200_OK
)
async def get_ai_project_suggestions(
        payload: schemas.ProjectSuggestionRequest,
        db: Session = Depends(get_db),
        llm: LLMProvider = Depends(get_llm_provider)
):
    """
    Veritabanındaki aktif stok komponentlerini otomatik analiz eder.
    Kullanıcının ilettiği ek parçalar, zorluk seviyesi ve özel temalarla
    harmanlayarak AI tabanlı structured proje reçeteleri üretir.
    """
    try:
        corr_id = get_correlation_id()
        logger.info(
            "Fetching active components for project suggestions", 
            extra={"correlation_id": corr_id}
        )
        # 1. Veritabanında miktarı 0'dan büyük olan aktif komponent kartlarını çekiyoruz
        active_components = (
            db.query(models.Component)
            .filter(models.Component.quantity > 0)
            .all()
        )

        # 2. LLM katmanının (Gevşek Bağlılık/Loose Coupling) bizden beklediği saf string listesini hazırlıyoruz
        stock_component_names = [c.name for c in active_components]

        logger.info(
            f"Generating suggestions with difficulty: {payload.difficulty_level}", 
            extra={"correlation_id": corr_id}
        )
        
        # 3. ABC Kontratımıza yeni eklediğimiz soyut metodu tetikliyoruz
        ai_suggestions = llm.suggest_projects(
            stock_components=stock_component_names,
            extra_components=payload.extra_components,
            difficulty_level=payload.difficulty_level,
            extra_message=payload.extra_message,
            response_format=schemas.ProjectSuggestionResponse
        )

        logger.info(
            "Project suggestions generated successfully", 
            extra={"correlation_id": corr_id}
        )
        return ai_suggestions

    except Exception as e:
        corr_id = get_correlation_id()
        logger.error(
            "Yapay zeka proje fikirleri üretilirken hata oluştu", 
            extra={"correlation_id": corr_id}, 
            exc_info=True
        )
        # Fail-Open Resilience Layer: Hata fırlatmak yerine boş bir yanıt dönüyoruz
        return schemas.ProjectSuggestionResponse(ideas=[])
