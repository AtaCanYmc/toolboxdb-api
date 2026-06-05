from openai import OpenAI
from typing import Type
from pydantic import BaseModel
from src.llm.llm_provider import LLMProvider
from src.llm.prompts import INVOICE_SYSTEM_PROMPT


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def parse_invoice(
        self, invoice_text: str, response_format: Type[BaseModel]
    ) -> BaseModel:
        completion = self.client.beta.chat.completions.parse(
            model=self.model,
            messages=[  # type: ignore
                {"role": "system", "content": INVOICE_SYSTEM_PROMPT},
                {"role": "user", "content": invoice_text},
            ],
            response_format=response_format,
        )
        return completion.choices[0].message.parsed
