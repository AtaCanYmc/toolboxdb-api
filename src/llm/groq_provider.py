import groq
import instructor
from typing import Type
from pydantic import BaseModel
from src.llm.llm_provider import LLMProvider
from src.llm.prompts import INVOICE_SYSTEM_PROMPT


class GroqProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "llama-3.3-70b-specdec"):
        self.client = instructor.from_groq(groq.Groq(api_key=api_key))
        self.model = model

    def parse_invoice(self, invoice_text: str, response_format: Type[BaseModel]) -> BaseModel:
        return self.client.chat.completions.create(  # type: ignore
            model=self.model,
            response_model=response_format,
            messages=[  # type: ignore
                {"role": "system", "content": INVOICE_SYSTEM_PROMPT},
                {"role": "user", "content": invoice_text}
            ],
        )
