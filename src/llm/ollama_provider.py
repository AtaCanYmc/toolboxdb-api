import ollama
from typing import Type, List
from pydantic import BaseModel
from src.llm.llm_provider import LLMProvider
from src.llm.prompt_provider import render_prompt


class OllamaProvider(LLMProvider):
    def __init__(self, model: str = "llama3.1"):
        self.model = model

    def parse_invoice(
        self,
        invoice_text: str,
        response_format: Type[BaseModel],
        existing_categories: List[str] = None,
        target_language: str = "English",
    ) -> BaseModel:
        json_schema = response_format.model_json_schema()

        if existing_categories is None:
            existing_categories = []

        system_prompt = render_prompt(
            template_name="invoice_parser_system_prompt.jinja2",
            context={
                "existing_categories": existing_categories,
                "target_language": target_language,
            },
        )

        response = ollama.chat(
            model=self.model,
            messages=[  # type: ignore
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": invoice_text},
            ],
            format=json_schema,
        )

        return response_format.model_validate_json(response["message"]["content"])

    def suggest_projects(
        self,
        stock_components: List[str],
        extra_components: List[str],
        difficulty_level: str,
        extra_message: str | None,
        response_format: Type[BaseModel],
        target_language: str = "English",
    ) -> BaseModel:
        """
        Brainstorm innovative maker project ideas based on available components and user criteria.
         - stock_components: The basic components the user has (e.g., "Arduino, LED, Resistor").
         - extra_components: Additional components that can be used (e.g., "Bluetooth module, LCD screen").
         - difficulty_level: The desired difficulty level for the projects.
         - extra_message: Any additional instructions or preferences from the user.
         - response_format: The Pydantic model class that defines the expected structure of the response.
         Returns a structured response containing project suggestions that fit the given criteria.
        """

        json_schema = response_format.model_json_schema()

        system_prompt = render_prompt(
            template_name="project_suggest_system_prompt.jinja2",
            context={
                "stock_components": stock_components,
                "extra_components": extra_components,
                "difficulty_level": difficulty_level,
                "extra_message": extra_message,
                "target_language": target_language,
            },
        )

        user_content = f"Generate 3-5 innovative project suggestions for difficulty level: {difficulty_level}."

        response = ollama.chat(
            model=self.model,
            messages=[  # type: ignore
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            format=json_schema,
        )

        return response_format.model_validate_json(response["message"]["content"])

    def get_project_details(
        self,
        project_title: str,
        project_description: str,
        difficulty: str,
        components: List[str],
        response_format: Type[BaseModel],
        target_language: str = "English",
    ) -> BaseModel:
        json_schema = response_format.model_json_schema()

        system_prompt = render_prompt(
            template_name="project_detail_system_prompt.jinja2",
            context={
                "project_title": project_title,
                "project_description": project_description,
                "difficulty": difficulty,
                "components": components,
                "target_language": target_language,
            },
        )

        user_content = f"Please create a detailed circuit diagram and code sketch for the '{project_title}' project."

        response = ollama.chat(
            model=self.model,
            messages=[  # type: ignore
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            format=json_schema,
        )

        return response_format.model_validate_json(response["message"]["content"])
