from fastapi import APIRouter, Depends, status, HTTPException
import groq
from pydantic import ValidationError
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
    status_code=status.HTTP_200_OK,
)
async def get_ai_project_suggestions(
    payload: schemas.ProjectSuggestionRequest,
    db: Session = Depends(get_db),
    llm: LLMProvider = Depends(get_llm_provider),
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
            extra={"correlation_id": corr_id},
        )
        # 1. Veritabanında miktarı 0'dan büyük olan aktif komponent kartlarını çekiyoruz
        active_components = (
            db.query(models.Component).filter(models.Component.quantity > 0).all()
        )

        # 2. LLM katmanının (Gevşek Bağlılık/Loose Coupling) bizden beklediği saf string listesini hazırlıyoruz
        stock_component_names = [c.name for c in active_components]

        logger.info(
            f"Generating suggestions with difficulty: {payload.difficulty_level}",
            extra={"correlation_id": corr_id},
        )

        # 3. ABC Kontratımıza yeni eklediğimiz soyut metodu tetikliyoruz
        ai_suggestions = llm.suggest_projects(
            stock_components=stock_component_names,
            extra_components=payload.extra_components,
            difficulty_level=payload.difficulty_level,
            extra_message=payload.extra_message,
            response_format=schemas.ProjectSuggestionResponse,
        )

        logger.info(
            "Project suggestions generated successfully",
            extra={"correlation_id": corr_id},
        )
        return ai_suggestions

    except (groq.APIError, ValidationError, RuntimeError) as ai_err:
        corr_id = get_correlation_id()
        logger.warning(
            f"Yapay zeka katmanı hatası (Fail-Open): {str(ai_err)}",
            extra={"correlation_id": corr_id},
            exc_info=True,
        )
        # Fail-Open Resilience Layer: Hata fırlatmak yerine boş bir yanıt dönüyoruz
        return schemas.ProjectSuggestionResponse(ideas=[])
    except Exception:
        corr_id = get_correlation_id()
        logger.error(
            "Sistem kritik hatası (Proje fikirleri üretilirken)",
            extra={"correlation_id": corr_id},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Sunucu tarafında kritik bir hata oluştu.",
        )


@suggestion_router.post(
    "/give-detail",
    response_model=schemas.AIProjectSuggestion,
    status_code=status.HTTP_200_OK,
)
async def get_project_details(
    payload: schemas.ProjectDetailRequest,
    llm: LLMProvider = Depends(get_llm_provider),
):
    """
    Belirli bir projenin devre şeması ve örnek kod taslağını LLM'den çeker.
    """
    try:
        corr_id = get_correlation_id()
        logger.info(
            f"Getting details for project: {payload.project_title}",
            extra={"correlation_id": corr_id},
        )

        project_details = llm.get_project_details(
            project_title=payload.project_title,
            project_description=payload.project_description,
            difficulty=payload.difficulty,
            components=payload.components,
            response_format=schemas.AIProjectSuggestion,
        )

        logger.info(
            "Project details generated successfully",
            extra={"correlation_id": corr_id},
        )
        return project_details

    except (groq.APIError, ValidationError, RuntimeError) as ai_err:
        corr_id = get_correlation_id()
        logger.warning(
            f"Yapay zeka katmanı hatası (Fail-Open): {str(ai_err)}",
            extra={"correlation_id": corr_id},
            exc_info=True,
        )
        # Fail-Open: Boş içerik dönüyoruz ki sistem çökmesin
        return schemas.AIProjectSuggestion(
            project_name=payload.project_title,
            difficulty=payload.difficulty,
            wiring_guide="Şu anda yapay zeka servisine ulaşılamıyor.",
            code_sketch="// Geçici olarak kullanılamıyor.",
        )
    except Exception:
        corr_id = get_correlation_id()
        logger.error(
            "Sistem kritik hatası (Proje detayı üretilirken)",
            extra={"correlation_id": corr_id},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Sunucu tarafında kritik bir hata oluştu.",
        )
