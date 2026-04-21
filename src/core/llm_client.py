import os
from abc import ABC, abstractmethod
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_ollama.chat_models import ChatOllama


class LLMProviderInterface(ABC):
    """Abstract interface for LLM provider implementations."""

    @abstractmethod
    def get_client(self) -> BaseChatModel: ...


class OllamaProvider(LLMProviderInterface):
    def __init__(self) -> None:
        self.model_name = os.getenv("LLM_MODEL", "gemma4:e2b")
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.temperature = float(os.getenv("LLM_TEMPERATURE", "0.7"))

    def get_client(self) -> BaseChatModel:
        return ChatOllama(
            model=self.model_name,
            base_url=self.base_url,
            temperature=self.temperature,
            num_ctx=4096,
            format="json",
        )


class LLMFactory:
    """Factory resolving the configured LLM provider."""

    _registry: dict[str, type[LLMProviderInterface]] = {
        "ollama": OllamaProvider,
    }

    @classmethod
    def get_provider(cls) -> LLMProviderInterface:
        provider_name = os.getenv("LLM_PROVIDER", "ollama").lower()
        provider_class = cls._registry.get(provider_name)
        if not provider_class:
            supported = ", ".join(cls._registry.keys())
            raise ValueError(
                f"Unsupported LLM provider: '{provider_name}'. Supported: {supported}"
            )
        return provider_class()

    @classmethod
    def register_provider(
        cls, name: str, provider_class: type[LLMProviderInterface]
    ) -> None:
        if not issubclass(provider_class, LLMProviderInterface):
            raise TypeError(
                f"{provider_class.__name__} must subclass LLMProviderInterface."
            )
        cls._registry[name.lower()] = provider_class


def create_llm() -> BaseChatModel:
    """Resolve configured provider and return a ready-to-use chat model."""
    return LLMFactory.get_provider().get_client()


def create_agent_llm(tools: list[Any] | None = None) -> BaseChatModel:
    """Create model instance, optionally binding LangChain tools."""
    llm = create_llm()
    if tools:
        return llm.bind_tools(tools)
    return llm