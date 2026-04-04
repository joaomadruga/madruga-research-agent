import os

import requests
import torch
from google import genai
from google.genai import types
from sentence_transformers import SentenceTransformer

from core.logger import get_logger
from ingestion.pdf import render_pdf_pages, split_pdf_chunks

logger = get_logger(__name__)

_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "ollama")

_DEFAULTS = {
    "gemini": {"model": "gemini-embedding-2-preview", "dimensions": 3072},
    "jina":   {"model": "jinaai/jina-embeddings-v4",  "dimensions": 1024},
    "ollama": {"model": "nomic-embed-text",            "dimensions": 768},
}

if _PROVIDER not in _DEFAULTS:
    raise ValueError(f"Unknown EMBEDDING_PROVIDER: {_PROVIDER!r}. Choose from: gemini, jina, ollama")

_MODEL = os.getenv("EMBEDDING_MODEL", _DEFAULTS[_PROVIDER]["model"])
DIMENSIONS = int(os.getenv("EMBEDDING_DIMENSIONS", _DEFAULTS[_PROVIDER]["dimensions"]))

# Lazy singleton for the local Jina model — loaded once on first use
_jina_model_instance: SentenceTransformer | None = None


def _jina_model() -> SentenceTransformer:
    global _jina_model_instance
    if _jina_model_instance is None:
        logger.info("Loading Jina v4 model '%s' (first load may take a moment)...", _MODEL)
        _jina_model_instance = SentenceTransformer(_MODEL, trust_remote_code=True)
        logger.info("Jina v4 model loaded")
    return _jina_model_instance


# ── helpers ───────────────────────────────────────────────────────────────────

def _average_vectors(vectors: list[list[float]]) -> list[float]:
    dims = len(vectors[0])
    return [sum(v[i] for v in vectors) / len(vectors) for i in range(dims)]


# ── text embedding ────────────────────────────────────────────────────────────

def _embed_gemini_text(text: str) -> list[float]:
    client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
    result = client.models.embed_content(
        model=_MODEL,
        contents=text,
        config={"output_dimensionality": DIMENSIONS},
    )
    return result.embeddings[0].values


def _embed_jina_text(text: str) -> list[float]:
    model = _jina_model()
    vector = model.encode([text], task="retrieval")[0]
    return vector.tolist()


def _embed_ollama_text(text: str) -> list[float]:
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
            return _embed_gemini_text(text)
        case "jina":
            return _embed_jina_text(text)
        case "ollama":
            return _embed_ollama_text(text)


# ── PDF embedding (multimodal) ────────────────────────────────────────────────

def _embed_gemini_pdf(pdf_bytes: bytes) -> list[float]:
    client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
    result = client.models.embed_content(
        model=_MODEL,
        contents=types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
        config={"output_dimensionality": DIMENSIONS},
    )
    return result.embeddings[0].values


def _embed_jina_pdf(path: str) -> list[float]:
    model = _jina_model()
    pages = render_pdf_pages(path, dpi=72)
    all_vectors = []
    for i, page in enumerate(pages):
        batch_vectors = model.encode([page], task="retrieval")
        all_vectors.append(batch_vectors[0].tolist())
        if torch.backends.mps.is_available():
            torch.mps.empty_cache()
    logger.debug("Embedded %d page(s) from '%s'", len(pages), path)
    return _average_vectors(all_vectors)


def embed_pdf(path: str) -> list[float]:
    """Embed a PDF file. Captures text, images, tables, and layout."""
    logger.info("Embedding PDF '%s' with %s/%s", path, _PROVIDER, _MODEL)
    match _PROVIDER:
        case "gemini":
            chunks = split_pdf_chunks(path, chunk_size=6)
            vectors = [_embed_gemini_pdf(chunk) for chunk in chunks]
            logger.debug("Averaged %d chunk(s)", len(vectors))
            return _average_vectors(vectors)
        case "jina":
            return _embed_jina_pdf(path)
        case "ollama":
            raise NotImplementedError(
                "Ollama does not support multimodal PDF embedding. "
                "Set EMBEDDING_PROVIDER=jina or EMBEDDING_PROVIDER=gemini."
            )
