import os
from src.llm.openai_provider import OpenAIProvider
from src.llm.groq_provider import GroqProvider
from src.llm.ollama_provider import OllamaProvider
from src.llm.llm_provider import LLMProvider


def get_llm_provider() -> LLMProvider:
    """.env dosyasındaki ayarlara göre doğru LLM sağlayıcısını döner."""
    provider_type = os.getenv("LLM_PROVIDER", "OPENAI").upper()

    if provider_type == "OPENAI":
        return OpenAIProvider(
            api_key=os.getenv("OPENAI_API_KEY"),
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        )
    elif provider_type == "GROQ":
        return GroqProvider(
            api_key=os.getenv("GROQ_API_KEY"),
            model=os.getenv("GROQ_MODEL", "llama-3.3-70b-specdec")
        )
    elif provider_type == "OLLAMA":
        return OllamaProvider(
            model=os.getenv("OLLAMA_MODEL", "llama3.1")
        )
    else:
        raise ValueError(f"Unknown LLM Provider: {provider_type}")
