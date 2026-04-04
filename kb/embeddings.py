import os

import requests
from google import genai

from core.logger import get_logger

logger = get_logger(__name__)

_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "gemini")

_DEFAULTS = {
    "gemini": {"model": "gemini-embedding-2-preview", "dimensions": 3072},
    "ollama": {"model": "nomic-embed-text", "dimensions": 768},
}

if _PROVIDER not in _DEFAULTS:
    raise ValueError(f"Unknown EMBEDDING_PROVIDER: {_PROVIDER!r}. Choose from: gemini, ollama")

_MODEL = os.getenv("EMBEDDING_MODEL", _DEFAULTS[_PROVIDER]["model"])
DIMENSIONS = int(os.getenv("EMBEDDING_DIMENSIONS", _DEFAULTS[_PROVIDER]["dimensions"]))


def _embed_gemini(text: str) -> list[float]:
    client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
    result = client.models.embed_content(
        model=_MODEL,
        contents=text,
        config={"output_dimensionality": DIMENSIONS},
    )
    return result.embeddings[0].values


def _embed_ollama(text: str) -> list[float]:
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    response = requests.post(
        f"{base_url}/api/embed",
        json={"model": _MODEL, "input": text},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["embeddings"][0]


def embed_text(text: str) -> list[float]:
    logger.debug("Embedding text (%d chars) with %s/%s", len(text), _PROVIDER, _MODEL)
    match _PROVIDER:
        case "gemini":
            return _embed_gemini(text)
        case "ollama":
            return _embed_ollama(text)
