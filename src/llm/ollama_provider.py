import ollama
from typing import Type
from pydantic import BaseModel
from src.llm.llm_provider import LLMProvider
from src.llm.prompts import INVOICE_SYSTEM_PROMPT


class OllamaProvider(LLMProvider):
    def __init__(self, model: str = "llama3.1"):
        self.model = model

    def parse_invoice(self, invoice_text: str, response_format: Type[BaseModel]) -> BaseModel:
        json_schema = response_format.model_json_schema()

        response = ollama.chat(
            model=self.model,
            messages=[  # type: ignore
                {"role": "system", "content": INVOICE_SYSTEM_PROMPT},
                {"role": "user", "content": invoice_text}
            ],
            format=json_schema  # Ollama'ya şemayı dikte ediyoruz
        )

        # Gelen string yanıtı pydantic nesnesine geri yüklüyoruz
        return response_format.model_validate_json(response['message']['content'])
