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
        """
        Parse the given invoice text and return structured data in the specified format.

        Args:
            invoice_text (str): The raw text extracted from the invoice.
            response_format (Type[BaseModel]): The Pydantic model representing the expected output structure.
            existing_categories (List[str], optional): A list of existing component categories to match against. Defaults to None.

        Returns:
            BaseModel: An instance of `response_format` populated with the extracted invoice data.
        """
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

        Args:
            stock_components (List[str]): List of components currently available in stock.
            extra_components (List[str]): List of additional components the user wants to include.
            difficulty_level (str): Target difficulty level for the projects (e.g., 'Beginner', 'Medium', 'Advanced').
            extra_message (str | None): Optional additional instructions or theme from the user.
            response_format (Type[BaseModel]): The Pydantic model representing the expected output structure.

        Returns:
            BaseModel: An instance of `response_format` containing the generated project ideas.
        """
        pass
