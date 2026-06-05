from abc import ABC, abstractmethod
from typing import Type
from pydantic import BaseModel


class LLMProvider(ABC):
    @abstractmethod
    def parse_invoice(
        self, invoice_text: str, response_format: Type[BaseModel]
    ) -> BaseModel:
        """Fatura metnini okur ve verilen Pydantic şemasına göre parse eder."""
        pass
