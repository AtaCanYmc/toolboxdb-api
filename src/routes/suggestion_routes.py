from fastapi import APIRouter, Depends, status, HTTPException, Header
import groq
from pydantic import ValidationError
from sqlalchemy.orm import Session
from src import models, schemas
from src.db import get_db
from src.llm.llm_factory import get_llm_provider
from src.llm.llm_provider import LLMProvider
import logging
from src.middleware.middleware import get_correlation_id
from src.routes.auth_deps import RoleChecker
from fastapi_i18n import _

logger = logging.getLogger("api_tracker")

suggestion_router = APIRouter(
    prefix="/api/v1/suggestions",
    tags=["Project Insights"],
)


@suggestion_router.post(
    "/project-ideas",
    response_model=schemas.ProjectSuggestionResponse,
    status_code=status.HTTP_200_OK,
)
async def get_ai_project_suggestions(
    payload: schemas.ProjectSuggestionRequest,
    accept_language: str = Header("en"),
    db: Session = Depends(get_db),
    llm: LLMProvider = Depends(get_llm_provider),
    current_user: models.User = Depends(RoleChecker(["admin", "user", "chatter"])),
):
    """
    Automatically analyzes active stock components in the database.
    Blends them with extra parts, difficulty level, and special themes
    provided by the user to generate AI-based structured project recipes.
    """
    try:
        corr_id = get_correlation_id()
        logger.info(
            "Fetching active components for project suggestions",
            extra={"correlation_id": corr_id},
        )
        active_components = (
            db.query(models.Component)
            .filter(models.Component.quantity > 0)
            .filter(models.Component.user_id == current_user.id)
            .all()
        )

        # 2. Prepare the pure string list expected by the LLM layer (Loose Coupling)
        stock_component_names = [c.name for c in active_components]

        logger.info(
            f"Generating suggestions with difficulty: {payload.difficulty_level}",
            extra={"correlation_id": corr_id},
        )

        # 3. Trigger the newly added abstract method in our ABC Contract
        ai_suggestions = llm.suggest_projects(
            stock_components=stock_component_names,
            extra_components=payload.extra_components,
            difficulty_level=payload.difficulty_level,
            extra_message=payload.extra_message,
            response_format=schemas.ProjectSuggestionResponse,
            target_language=accept_language.split(",")[0],
        )

        logger.info(
            "Project suggestions generated successfully",
            extra={"correlation_id": corr_id},
        )
        return ai_suggestions

    except (groq.APIError, ValidationError, RuntimeError) as ai_err:
        corr_id = get_correlation_id()
        logger.warning(
            f"AI layer error (Fail-Open): {str(ai_err)}",
            extra={"correlation_id": corr_id},
            exc_info=True,
        )
        # Fail-Open Resilience Layer: Return an empty response instead of throwing an error
        return schemas.ProjectSuggestionResponse(ideas=[])
    except Exception:
        corr_id = get_correlation_id()
        logger.error(
            "Critical system error (While generating project ideas)",
            extra={"correlation_id": corr_id},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=_("A critical error occurred on the server side."),
        )


@suggestion_router.post(
    "/give-detail",
    response_model=schemas.AIProjectSuggestion,
    status_code=status.HTTP_200_OK,
)
async def get_project_details(
    payload: schemas.ProjectDetailRequest,
    accept_language: str = Header("en"),
    llm: LLMProvider = Depends(get_llm_provider),
    current_user: models.User = Depends(RoleChecker(["admin", "user", "chatter"])),
):
    """
    Fetches the circuit diagram and sample code sketch of a specific project from the LLM.
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
            target_language=accept_language.split(",")[0],
        )

        logger.info(
            "Project details generated successfully",
            extra={"correlation_id": corr_id},
        )
        return project_details

    except (groq.APIError, ValidationError, RuntimeError) as ai_err:
        corr_id = get_correlation_id()
        logger.warning(
            f"AI layer error (Fail-Open): {str(ai_err)}",
            extra={"correlation_id": corr_id},
            exc_info=True,
        )
        # Fail-Open: Return empty content so the system doesn't crash
        return schemas.AIProjectSuggestion(
            project_name=payload.project_title,
            difficulty=payload.difficulty,
            wiring_guide="The AI service is currently unavailable.",
            code_sketch="// Temporarily unavailable.",
        )
    except Exception:
        corr_id = get_correlation_id()
        logger.error(
            "Critical system error (While generating project details)",
            extra={"correlation_id": corr_id},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=_("A critical error occurred on the server side."),
        )
