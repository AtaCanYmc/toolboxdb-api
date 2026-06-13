from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from src import models, schemas
from src.db import get_db
from src.llm.llm_factory import get_llm_provider
from src.llm.llm_provider import LLMProvider
import logging
from src.middleware.middleware import get_correlation_id
from src.routes.auth_deps import RoleChecker
from fastapi_i18n import _

from src.agents.hardware_consultant import HardwareConsultantAgent
from src.llm.tools.stock_tool import get_stock_search_tool
from src.llm.tools.inventory_tool import get_full_inventory_tool

logger = logging.getLogger("api_tracker")

suggestion_router = APIRouter(
    prefix="/api/v1/suggestions",
    tags=["Hardware Consultant"],
)


@suggestion_router.post(
    "/chat",
    response_model=schemas.ChatResponse,
    status_code=status.HTTP_200_OK,
)
async def hardware_consultant_chat(
    payload: schemas.ChatRequest,
    db: Session = Depends(get_db),
    llm: LLMProvider = Depends(get_llm_provider),
    current_user: models.User = Depends(RoleChecker(["admin", "user", "chatter"])),
):
    """
    Unified interactive Hardware Consultant Agent.
    Handles project brainstorming, BOM extraction, circuit design, and market/cargo optimization dynamically.
    """
    corr_id = get_correlation_id()
    logger.info(
        f"Processing chat message for user {current_user.id}",
        extra={"correlation_id": corr_id},
    )

    try:
        # 1. Fetch the underlying LangChain model
        lc_model = llm.get_langchain_model()

        # 2. Instantiate Dynamic DB-aware Tools
        stock_tool = get_stock_search_tool(db, current_user.id)
        inventory_tool = get_full_inventory_tool(db, current_user.id)

        # 3. Create the Consultant Agent
        agent = HardwareConsultantAgent(
            llm=lc_model, extra_tools=[stock_tool, inventory_tool]
        )

        # 4. Extract history from payload
        history_dicts = [
            {"role": msg.role, "content": msg.content} for msg in payload.history
        ]

        # 5. Invoke the Agent
        response_text = agent.chat(user_input=payload.message, history=history_dicts)

        logger.info(
            "Chat response generated successfully",
            extra={"correlation_id": corr_id},
        )
        return schemas.ChatResponse(response=response_text)

    except Exception as e:
        logger.error(
            f"Error in hardware consultant chat: {str(e)}",
            extra={"correlation_id": corr_id},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=_(
                "An error occurred while communicating with the hardware consultant."
            ),
        )
