from openai import OpenAI
from typing import Type, List
from pydantic import BaseModel
from src.llm.llm_provider import LLMProvider
from src.llm.prompt_provider import render_prompt


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def parse_invoice(
        self,
        invoice_text: str,
        response_format: Type[BaseModel],
        existing_categories: List[str] = None,
        target_language: str = "English",
    ) -> BaseModel:
        if existing_categories is None:
            existing_categories = []

        system_prompt = render_prompt(
            template_name="invoice_parser_system_prompt.jinja2",
            context={
                "existing_categories": existing_categories,
                "target_language": target_language,
            },
        )

        completion = self.client.beta.chat.completions.parse(
            model=self.model,
            messages=[  # type: ignore
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": invoice_text},
            ],
            response_format=response_format,
        )
        return completion.choices[0].message.parsed

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

        user_content = f"Generate innovative project suggestions for difficulty level: {difficulty_level}."

        completion = self.client.beta.chat.completions.parse(
            model=self.model,
            response_format=response_format,
            messages=[  # type: ignore
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
        )
        return completion.choices[0].message.parsed

    def get_project_details(
        self,
        project_title: str,
        project_description: str,
        difficulty: str,
        components: List[str],
        response_format: Type[BaseModel],
        target_language: str = "English",
    ) -> BaseModel:
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

        completion = self.client.beta.chat.completions.parse(
            model=self.model,
            response_format=response_format,
            messages=[  # type: ignore
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
        )
        return completion.choices[0].message.parsed
