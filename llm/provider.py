import os

from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI


def get_llm() -> BaseChatModel:
    provider = os.getenv("LLM_PROVIDER", "anthropic")
    model = os.getenv("MODEL", "claude-sonnet-4-6")

    match provider:
        case "anthropic":
            return ChatAnthropic(model=model)
        case "ollama":
            base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            return ChatOllama(model=model, base_url=base_url)
        case "openai":
            return ChatOpenAI(model=model)
        case _:
            raise ValueError(
                f"Unknown LLM_PROVIDER: {provider!r}. Choose from: anthropic, ollama, openai"
            )
