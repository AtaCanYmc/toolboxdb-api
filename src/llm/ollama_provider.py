import ollama
from typing import Type, List
from pydantic import BaseModel
from src.llm.llm_provider import LLMProvider
from src.llm.prompt_provider import render_prompt


class OllamaProvider(LLMProvider):
    def __init__(self, model: str = "llama3.1"):
        self.model = model

    def parse_invoice(
            self,
            invoice_text: str,
            response_format: Type[BaseModel],
            existing_categories: List[str] = None
    ) -> BaseModel:
        json_schema = response_format.model_json_schema()

        if existing_categories is None:
            existing_categories = []

        system_prompt = render_prompt(
            template_name="invoice_parser_system_prompt.jinja2",
            context={"existing_categories": existing_categories},
        )

        response = ollama.chat(
            model=self.model,
            messages=[  # type: ignore
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": invoice_text},
            ],
            format=json_schema,
        )

        return response_format.model_validate_json(response["message"]["content"])
