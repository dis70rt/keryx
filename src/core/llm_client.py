import os
from abc import ABC, abstractmethod
from typing import List, Optional, Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_ollama.chat_models import ChatOllama


class LLMProviderInterface(ABC):
    """
    Abstract interface that all new LLM providers must implement.
    This contract ensures that future models consistently integrate with the agent.
    """

    @abstractmethod
    def get_client(self) -> BaseChatModel:
        """Return a configured LangChain-compatible chat model instance."""
        pass


class OllamaProvider(LLMProviderInterface):

    def __init__(self):
        self.model_name = os.getenv("LLM_MODEL", "gemma")
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
        self.temperature = float(os.getenv("LLM_TEMPERATURE", "0.7"))

    def get_client(self) -> BaseChatModel:
        return ChatOllama(
            model=self.model_name,
            base_url=self.base_url,
            temperature=self.temperature,
        )


# ── Stub: OpenAI provider ────────────────────────────────────────────────────
# Uncomment and install `langchain-openai` to enable.
#
# class OpenAIProvider(LLMProviderInterface):
#     """
#     Provider implementation for OpenAI models.
#
#     Environment Variables:
#         LLM_MODEL    – Model name (default: 'gpt-4o')
#         OPENAI_API_KEY – Your OpenAI API key (required)
#     """
#
#     def get_client(self) -> BaseChatModel:
#         from langchain_openai import ChatOpenAI
#         return ChatOpenAI(
#             model=os.getenv("LLM_MODEL", "gpt-4o"),
#             temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
#         )


# ── Stub: Anthropic / Claude provider ────────────────────────────────────────
# Uncomment and install `langchain-anthropic` to enable.
#
# class AnthropicProvider(LLMProviderInterface):
#     """
#     Provider implementation for Anthropic Claude models.
#
#     Environment Variables:
#         LLM_MODEL         – Model name (default: 'claude-3-5-sonnet-20241022')
#         ANTHROPIC_API_KEY – Your Anthropic API key (required)
#     """
#
#     def get_client(self) -> BaseChatModel:
#         from langchain_anthropic import ChatAnthropic
#         return ChatAnthropic(
#             model=os.getenv("LLM_MODEL", "claude-3-5-sonnet-20241022"),
#             temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
#         )


class LLMFactory:
    """
    Factory that resolves and instantiates the requested LLM provider.

    To add a new provider:
        1. Implement a class that extends LLMProviderInterface.
        2. Add an entry to _registry below.
        3. Set the LLM_PROVIDER environment variable to the matching key.
    """

    # Register available providers here
    _registry: dict[str, type[LLMProviderInterface]] = {
        "ollama": OllamaProvider,
        # "openai":     OpenAIProvider,
        # "anthropic":  AnthropicProvider,
    }

    @classmethod
    def get_provider(cls) -> LLMProviderInterface:
        """
        Reads LLM_PROVIDER from the environment and returns the matching
        provider instance.

        Raises:
            ValueError: If the requested provider is not registered.
        """
        provider_name = os.getenv("LLM_PROVIDER", "ollama").lower()
        provider_class = cls._registry.get(provider_name)

        if not provider_class:
            supported = ", ".join(cls._registry.keys())
            raise ValueError(
                f"Unsupported LLM provider: '{provider_name}'. "
                f"Supported providers: {supported}"
            )

        return provider_class()

    @classmethod
    def register_provider(
        cls, name: str, provider_class: type[LLMProviderInterface]
    ) -> None:
        """
        Dynamically register a new provider at runtime.

        Args:
            name:           The key used to select this provider via LLM_PROVIDER.
            provider_class: A class that implements LLMProviderInterface.

        Raises:
            TypeError: If provider_class does not subclass LLMProviderInterface.
        """
        if not issubclass(provider_class, LLMProviderInterface):
            raise TypeError(
                f"{provider_class.__name__} must subclass LLMProviderInterface."
            )
        cls._registry[name.lower()] = provider_class


# ── Convenience helpers ───────────────────────────────────────────────────────

def create_llm() -> BaseChatModel:
    """
    Convenience wrapper: resolves the configured provider and returns a
    ready-to-use LangChain chat model.
    """
    provider = LLMFactory.get_provider()
    return provider.get_client()


def create_agent_llm(tools: Optional[List[Any]] = None) -> BaseChatModel:
    """
    Creates the model instance and optionally binds a list of tools to it.

    Args:
        tools: A list of LangChain-compatible tool objects. When provided,
               the model is returned with the tools already bound via
               `bind_tools`, enabling native function / tool calling.

    Returns:
        A BaseChatModel instance, with tools bound if supplied.
    """
    llm = create_llm()
    if tools:
        return llm.bind_tools(tools)
    return llm