import groq
import instructor
from typing import Type, List
from pydantic import BaseModel
from src.llm.llm_provider import LLMProvider
from src.llm.prompt_provider import render_prompt
import logging
from src.middleware.middleware import get_correlation_id
import time
from langchain_groq import ChatGroq
from langchain_core.language_models.chat_models import BaseChatModel

logger = logging.getLogger("api_tracker")


# models: "https://console.groq.com/docs/models"


class GroqProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "llama-3.3-70b-versatile"):
        self.client = instructor.from_groq(groq.Groq(api_key=api_key))
        self.model = model

    def parse_invoice(
        self,
        invoice_text: str,
        response_format: Type[BaseModel],
        existing_categories: List[str] = None,
        target_language: str = "English",
    ) -> BaseModel:
        if existing_categories is None:
            existing_categories = []

        system_prompt = render_prompt(
            template_name="invoice_parser_system_prompt.jinja2",
            context={
                "existing_categories": existing_categories,
                "target_language": target_language,
            },
        )

        corr_id = get_correlation_id()
        logger.info(
            f"Sending parse_invoice request to Groq using model: {self.model}",
            extra={"correlation_id": corr_id},
        )

        start_time = time.time()
        try:
            result = self.client.chat.completions.create(  # type: ignore
                model=self.model,
                response_model=response_format,
                messages=[  # type: ignore
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": invoice_text},
                ],
            )
            process_time = round((time.time() - start_time) * 1000, 2)
            logger.info(
                f"Groq parse_invoice request completed in {process_time}ms",
                extra={"correlation_id": corr_id},
            )
            return result
        except Exception as e:
            process_time = round((time.time() - start_time) * 1000, 2)
            logger.error(
                f"Groq parse_invoice request failed after {process_time}ms: {str(e)}",
                extra={"correlation_id": corr_id},
                exc_info=True,
            )
            raise e

    def get_langchain_model(self) -> BaseChatModel:
        return ChatGroq(
            api_key=self.client.client.api_key,  # instructor client wraps groq client
            model=self.model,
            temperature=0.0,
        )
