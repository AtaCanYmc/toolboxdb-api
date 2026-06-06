from openai import OpenAI
from typing import Type, List
from pydantic import BaseModel
from src.llm.llm_provider import LLMProvider
from src.llm.prompt_provider import render_prompt


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self.client = OpenAI(api_key=api_key)
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

        completion = self.client.beta.chat.completions.parse(
            model=self.model,
            messages=[  # type: ignore
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": invoice_text},
            ],
            response_format=response_format,
        )
        return completion.choices[0].message.parsed
