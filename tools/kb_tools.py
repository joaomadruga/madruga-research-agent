import os
from typing import Annotated

from langchain_core.tools import tool
from tavily import TavilyClient

import kb.embeddings as embeddings
import kb.storage as storage
import kb.vector_store as vector_store
from core.logger import get_logger
from core.schemas import ArticleMetadata, DeepDiveResult, SearchResult
from ingestion.web import fetch_url as _fetch_url
from llm.provider import get_llm

logger = get_logger(__name__)

_WIKI_COMPILATION_PROMPT = """\
You are a research assistant. Summarize the following article into a structured markdown note.

Use exactly these sections:
## Summary
(2-3 sentence overview)

## Key Points
(bullet list of the most important ideas)

## Implications
(why this matters, what it connects to)

## Tags
(comma-separated list of relevant topics/concepts)

Article content:
---
{content}
---
"""


def _compile_wiki_note(content: str) -> str:
    llm = get_llm()
    prompt = _WIKI_COMPILATION_PROMPT.format(content=content[:40_000])
    logger.info("Compiling wiki note...")
    response = llm.invoke(prompt)
    return response.content


@tool
def add_article(
    title: Annotated[str, "Title of the article"],
    content: Annotated[str, "Full text content of the article"],
    source: Annotated[str, "URL or file path or 'manual'"],
    tags: Annotated[list[str], "List of topic tags"],
    file_hash: Annotated[str | None, "SHA-256 hash of the source file, if any"] = None,
) -> str:
    """Add a new article to the knowledge base. Compiles a wiki note automatically."""
    slug = storage.slugify(title)
    index = storage.load_index()

    if slug in index and file_hash is None:
        slug = f"{slug}-{storage.now_iso()[:10]}"

    storage.write_raw(slug, content)
    wiki_note = _compile_wiki_note(content)
    storage.write_wiki(slug, wiki_note)

    metadata = ArticleMetadata(
        title=title,
        slug=slug,
        source=source,
        tags=tags,
        created_at=storage.now_iso(),
        file_hash=file_hash,
    )
    storage.add_to_index(metadata)

    if source.endswith(".pdf"):
        embedding = embeddings.embed_pdf(source)
    else:
        embedding = embeddings.embed_text(f"{title}\n\n{wiki_note}")
    vector_store.upsert(slug, title, embedding)

    logger.info("Article '%s' added (slug: %s)", title, slug)
    return f"Article '{title}' added with slug '{slug}'."


@tool
def get_article(slug: Annotated[str, "Slug of the article"]) -> str:
    """Read the wiki summary of a single article."""
    index = storage.load_index()
    if slug not in index:
        return f"No article found with slug '{slug}'."
    return storage.read_wiki(slug)


@tool
def list_articles(
    tag: Annotated[str | None, "Filter by tag (optional)"] = None,
) -> list[dict]:
    """List all articles in the knowledge base, optionally filtered by tag."""
    index = storage.load_index()
    entries = list(index.values())
    if tag:
        entries = [e for e in entries if tag.lower() in [t.lower() for t in e["tags"]]]
    return entries


@tool
def delete_article(slug: Annotated[str, "Slug of the article to delete"]) -> str:
    """Delete an article from the knowledge base."""
    index = storage.load_index()
    if slug not in index:
        return f"No article found with slug '{slug}'."
    title = index[slug]["title"]
    storage.delete_article(slug)
    vector_store.delete(slug)
    return f"Deleted article '{title}' (slug: '{slug}')."


@tool
def update_article_tags(
    slug: Annotated[str, "Slug of the article"],
    tags: Annotated[list[str], "New list of tags"],
) -> str:
    """Replace the tags on an existing article."""
    index = storage.load_index()
    if slug not in index:
        return f"No article found with slug '{slug}'."
    index[slug]["tags"] = tags
    storage.save_index(index)
    return f"Tags updated for '{slug}'."


@tool
def search_knowledge_base(
    query: Annotated[str, "Search query or question"],
    top_k: Annotated[int, "Number of results to return"] = 5,
) -> list[dict]:
    """Search the knowledge base using semantic similarity. Returns the most relevant articles."""
    index = storage.load_index()
    if not index:
        return []

    query_embedding = embeddings.embed_text(query)
    slugs = vector_store.search(query_embedding, top_k=top_k)

    results = []
    for slug in slugs:
        if slug not in index:
            continue
        try:
            content = storage.read_wiki(slug)
        except FileNotFoundError:
            continue
        excerpt = content[:500].replace("\n", " ").strip()
        results.append(
            SearchResult(slug=slug, title=index[slug]["title"], excerpt=excerpt).model_dump()
        )

    return results


@tool
def deep_dive_article(
    slug: Annotated[str, "Slug of the article to load into context"],
) -> dict:
    """Load the full content of one article (raw + wiki) into context for deep analysis."""
    index = storage.load_index()
    if slug not in index:
        return {"error": f"No article found with slug '{slug}'."}

    metadata = ArticleMetadata(**index[slug])
    try:
        wiki = storage.read_wiki(slug)
    except FileNotFoundError:
        wiki = "(wiki note not found)"
    try:
        raw = storage.read_raw(slug)
    except FileNotFoundError:
        raw = "(raw content not found)"

    return DeepDiveResult(metadata=metadata, wiki=wiki, raw=raw).model_dump()


@tool
def fetch_url(url: Annotated[str, "URL to fetch and extract text from"]) -> str:
    """Fetch a web article and return its plain text content."""
    return _fetch_url(url)


@tool
def search_web(
    query: Annotated[str, "Search query"],
    max_results: Annotated[int, "Maximum number of results to return"] = 5,
) -> list[dict] | str:
    """Search the web for articles. Requires TAVILY_API_KEY in environment."""
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return "No TAVILY_API_KEY set. Please provide a URL directly and I will fetch it."

    client = TavilyClient(api_key=api_key)
    response = client.search(query, max_results=max_results)
    return [
        {"title": r["title"], "url": r["url"], "excerpt": r.get("content", "")[:300]}
        for r in response.get("results", [])
    ]


def get_tool_list() -> list:
    return [
        add_article,
        get_article,
        list_articles,
        delete_article,
        update_article_tags,
        search_knowledge_base,
        deep_dive_article,
        fetch_url,
        search_web,
    ]
