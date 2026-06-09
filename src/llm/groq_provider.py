import groq
import instructor
from typing import Type, List
from pydantic import BaseModel
from src.llm.llm_provider import LLMProvider
from src.llm.prompt_provider import render_prompt
import logging
from src.middleware.middleware import get_correlation_id
import time

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
    ) -> BaseModel:
        if existing_categories is None:
            existing_categories = []

        system_prompt = render_prompt(
            template_name="invoice_parser_system_prompt.jinja2",
            context={"existing_categories": existing_categories},
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

    def suggest_projects(
        self,
        stock_components: List[str],
        extra_components: List[str],
        difficulty_level: str,
        extra_message: str | None,
        response_format: Type[BaseModel],
    ) -> BaseModel:
        """
        Brainstorm innovative maker project ideas based on available components and user criteria.
         - stock_components: The basic components the user has (e.g., "Arduino, LED, Resistor").
         - extra_components: Additional components that can be used (e.g., "Bluetooth module, LCD screen").
         - difficulty_level: The desired difficulty level for the projects.
         - extra_message: Any additional instructions or preferences from the user.
         - response_format: The Pydantic model class that defines the expected structure of the response.
         Returns a structured response containing project suggestions that fit the given criteria.
        """

        system_prompt = render_prompt(
            template_name="project_suggest_system_prompt.jinja2",
            context={
                "stock_components": stock_components,
                "extra_components": extra_components,
                "difficulty_level": difficulty_level,
                "extra_message": extra_message,
            },
        )

        user_content = f"Generate innovative project suggestions for difficulty level: {difficulty_level}."

        corr_id = get_correlation_id()
        logger.info(
            f"Sending suggest_projects request to Groq using model: {self.model}",
            extra={"correlation_id": corr_id},
        )

        start_time = time.time()
        try:
            result = self.client.chat.completions.create(  # type: ignore
                model=self.model,
                response_model=response_format,
                messages=[  # type: ignore
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
            )
            process_time = round((time.time() - start_time) * 1000, 2)
            logger.info(
                f"Groq suggest_projects request completed in {process_time}ms",
                extra={"correlation_id": corr_id},
            )
            return result
        except Exception as e:
            process_time = round((time.time() - start_time) * 1000, 2)
            logger.error(
                f"Groq suggest_projects request failed after {process_time}ms: {str(e)}",
                extra={"correlation_id": corr_id},
                exc_info=True,
            )
            raise e
