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

    @abstractmethod
    def suggest_projects(
            self,
            stock_components: List[str],
            extra_components: List[str],
            difficulty_level: str,
            extra_message: str | None,
            response_format: Type[BaseModel],
    ) -> BaseModel:
        """
        Brainstorm innovative maker project ideas based on available components and user criteria.
        """
        pass
