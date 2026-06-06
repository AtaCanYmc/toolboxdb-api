from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from src import models, schemas
from src.db import get_db
from src.llm.llm_factory import get_llm_provider
from src.llm.llm_provider import LLMProvider

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
        # 1. Veritabanında miktarı 0'dan büyük olan aktif komponent kartlarını çekiyoruz
        active_components = (
            db.query(models.Component)
            .filter(models.Component.quantity > 0)
            .all()
        )

        # 2. LLM katmanının (Gevşek Bağlılık/Loose Coupling) bizden beklediği saf string listesini hazırlıyoruz
        stock_component_names = [c.name for c in active_components]

        # 3. ABC Kontratımıza yeni eklediğimiz soyut metodu tetikliyoruz
        ai_suggestions = llm.suggest_projects(
            stock_components=stock_component_names,
            extra_components=payload.extra_components,
            difficulty_level=payload.difficulty_level,
            extra_message=payload.extra_message,
            response_format=schemas.ProjectSuggestionResponse
        )

        return ai_suggestions

    except Exception as e:
        # Kurumsal hata loglama standartlarına uygun olarak 500 fırlatıyoruz
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Proje fikirleri üretilirken bir yapay zeka hatası oluştu: {str(e)}"
        )
