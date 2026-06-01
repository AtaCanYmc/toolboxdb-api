from openai import OpenAI
from typing import Type
from pydantic import BaseModel
from src.llm.llm_provider import LLMProvider


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def parse_invoice(self, invoice_text: str, response_format: Type[BaseModel]) -> BaseModel:
        completion = self.client.beta.chat.completions.parse(
            model=self.model,
            messages=[
                {"role": "system",
                 "content": "Sen faturalardan elektronik parça isimlerini, adetlerini ve kategorilerini çıkaran bir asistanısın."},
                {"role": "user", "content": invoice_text}
            ],
            response_format=response_format,
        )
        return completion.choices[0].message.parsed
