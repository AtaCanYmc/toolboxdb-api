from abc import ABC, abstractmethod
from typing import Type, List
from pydantic import BaseModel


class LLMProvider(ABC):
    @abstractmethod
    def parse_invoice(
            self,
            invoice_text: str,
            response_format: Type[BaseModel],
            existing_categories: List[str] = None,
    ) -> BaseModel:
        """Parse the given invoice text and return structured data in the specified format."""
        pass
