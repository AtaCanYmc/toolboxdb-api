import groq
import instructor
from typing import Type
from pydantic import BaseModel
from src.llm.llm_provider import LLMProvider


class GroqProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "llama-3.3-70b-specdec"):
        self.client = instructor.from_groq(groq.Groq(api_key=api_key))
        self.model = model

    def parse_invoice(self, invoice_text: str, response_format: Type[BaseModel]) -> BaseModel:
        return self.client.chat.completions.create(
            model=self.model,
            response_model=response_format,  # Pydantic zorlaması
            messages=[
                {"role": "system",
                 "content": "Sen faturalardan elektronik parça isimlerini, adetlerini ve kategorilerini çıkaran bir asistanısın."},
                {"role": "user", "content": invoice_text}
            ],
        )
