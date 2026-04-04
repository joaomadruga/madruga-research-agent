"""
MCP server exposing the research knowledge base to Claude Code.
Registered in ~/.claude/settings.json — Claude Code starts this automatically.
"""

from dotenv import load_dotenv

load_dotenv()

from mcp.server.fastmcp import FastMCP

import kb.embeddings as embeddings
import kb.storage as storage
import kb.vector_store as vector_store
from core.logger import get_logger
from core.schemas import ArticleMetadata, DeepDiveResult, SearchResult
from ingestion.pdf import read_local_file
from ingestion.web import fetch_url
from kb.vector_store import init_db
from llm.provider import get_llm

logger = get_logger(__name__)

mcp = FastMCP("research-agent")

init_db()

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
    response = llm.invoke(_WIKI_COMPILATION_PROMPT.format(content=content[:40_000]))
    return response.content


@mcp.tool()
def search_knowledge_base(query: str, top_k: int = 5) -> list[dict]:
    """Search the research knowledge base using semantic similarity."""
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
        results.append(SearchResult(slug=slug, title=index[slug]["title"], excerpt=excerpt).model_dump())
    return results


@mcp.tool()
def deep_dive_article(slug: str) -> dict:
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


@mcp.tool()
def list_articles(tag: str | None = None) -> list[dict]:
    """List all articles in the knowledge base, optionally filtered by tag."""
    index = storage.load_index()
    entries = list(index.values())
    if tag:
        entries = [e for e in entries if tag.lower() in [t.lower() for t in e["tags"]]]
    return entries


@mcp.tool()
def add_article(title: str, content: str, source: str, tags: list[str]) -> str:
    """Add a new article to the research knowledge base."""
    slug = storage.slugify(title)
    index = storage.load_index()
    if slug in index:
        slug = f"{slug}-{storage.now_iso()[:10]}"
    storage.write_raw(slug, content)
    wiki_note = _compile_wiki_note(content)
    storage.write_wiki(slug, wiki_note)
    metadata = ArticleMetadata(
        title=title, slug=slug, source=source, tags=tags, created_at=storage.now_iso()
    )
    storage.add_to_index(metadata)
    embedding = embeddings.embed_text(f"{title}\n\n{wiki_note}")
    vector_store.upsert(slug, title, embedding)
    logger.info("Article '%s' added via MCP", slug)
    return f"Article '{title}' added with slug '{slug}'."


@mcp.tool()
def delete_article(slug: str) -> str:
    """Delete an article from the research knowledge base."""
    index = storage.load_index()
    if slug not in index:
        return f"No article found with slug '{slug}'."
    title = index[slug]["title"]
    storage.delete_article(slug)
    vector_store.delete(slug)
    return f"Deleted '{title}'."


@mcp.tool()
def fetch_and_add_url(url: str, tags: list[str] | None = None) -> str:
    """Fetch a URL and add it to the research knowledge base."""
    content = fetch_url(url)
    title = url.split("/")[-1].replace("-", " ").replace("_", " ").title() or url
    return add_article(title=title, content=content, source=url, tags=tags or ["web"])


@mcp.tool()
def add_local_file(path: str, title: str, tags: list[str] | None = None) -> str:
    """Read a local file (PDF or text) and add it to the research knowledge base."""
    content = read_local_file(path)
    return add_article(title=title, content=content, source=path, tags=tags or ["file"])


if __name__ == "__main__":
    mcp.run()
