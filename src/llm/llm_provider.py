from abc import ABC, abstractmethod
from typing import Type, List, TYPE_CHECKING
from pydantic import BaseModel

if TYPE_CHECKING:
    from langchain_core.language_models.chat_models import BaseChatModel


class LLMProvider(ABC):
    @abstractmethod
    def parse_invoice(
        self,
        invoice_text: str,
        response_format: Type[BaseModel],
        existing_categories: List[str] = None,
        target_language: str = "English",
    ) -> BaseModel:
        """
        Parse the given invoice text and return structured data in the specified format.

        Args:
            invoice_text (str): The raw text extracted from the invoice.
            response_format (Type[BaseModel]): The Pydantic model representing the expected output structure.
            existing_categories (List[str], optional): A list of existing component categories to match
                against. Defaults to None.
            target_language (str, optional): The target language to use. Defaults to "English".

        Returns:
            BaseModel: An instance of `response_format` populated with the extracted invoice data.
        """
        pass

    @abstractmethod
    def get_langchain_model(self) -> "BaseChatModel":
        """
        Returns the corresponding LangChain BaseChatModel for this provider.
        """
        pass
