import groq
import instructor
from typing import Type, List
from pydantic import BaseModel
from src.llm.llm_provider import LLMProvider
from src.llm.prompt_provider import render_prompt


# models: "https://console.groq.com/docs/models"

class GroqProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "llama-3.3-70b-versatile"):
        self.client = instructor.from_groq(groq.Groq(api_key=api_key))
        self.model = model

    def parse_invoice(
            self,
            invoice_text: str,
            response_format: Type[BaseModel],
            existing_categories: List[str] = None
    ) -> BaseModel:
        if existing_categories is None:
            existing_categories = []

        system_prompt = render_prompt(
            template_name="invoice_parser_system_prompt.jinja2",
            context={"existing_categories": existing_categories},
        )

        return self.client.chat.completions.create(  # type: ignore
            model=self.model,
            response_model=response_format,
            messages=[  # type: ignore
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": invoice_text},
            ],
        )

    def suggest_projects(
            self,
            stock_components: List[str],
            extra_components: List[str],
            difficulty_level: str,
            extra_message: str | None,
            response_format: Type[BaseModel]
    ) -> BaseModel:
        """
        Eldeki komponent havuzunu Jinja2 şablonuyla işler ve
        Groq üzerinden Pydantic yapısında proje fikirleri döndürür.
        """

        system_prompt = render_prompt(
            template_name="project_suggest_system_prompt.jinja2",
            context={
                "stock_components": stock_components,
                "extra_components": extra_components,
                "difficulty_level": difficulty_level,
                "extra_message": extra_message
            }
        )

        user_content = f"Generate innovative project suggestions for difficulty level: {difficulty_level}."

        return self.client.chat.completions.create(  # type: ignore
            model=self.model,
            response_model=response_format,
            messages=[  # type: ignore
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ]
        )
