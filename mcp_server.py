"""
MCP server exposing the research knowledge base to Claude Code.
Registered in ~/.claude/settings.json — Claude Code starts this automatically.
"""

from dotenv import load_dotenv

load_dotenv()

from mcp.server.fastmcp import FastMCP

import wiki.storage as storage
from core.logger import get_logger
from core.schemas import ArticleMetadata
from parsers.pdf import read_local_file
from parsers.web import fetch_url as _fetch_url

logger = get_logger(__name__)

mcp = FastMCP("research-agent")


@mcp.tool()
def store_source(title: str, content: str, source: str, tags: list[str]) -> str:
    """Save raw source content and register it in the index."""
    slug = storage.slugify(title)
    index = storage.load_index()
    if slug in index:
        slug = f"{slug}-{storage.now_iso()[:10]}"
    storage.write_source(slug, content)
    metadata = ArticleMetadata(
        title=title, slug=slug, source=source, tags=tags, created_at=storage.now_iso()
    )
    storage.add_to_index(metadata)
    return f"Source '{title}' stored with slug '{slug}'."


@mcp.tool()
def read_source(slug: str) -> str:
    """Read the raw text of a stored source."""
    index = storage.load_index()
    if slug not in index:
        return f"No source found with slug '{slug}'."
    return storage.read_source(slug)


@mcp.tool()
def list_sources(tag: str | None = None) -> list[dict]:
    """List all stored sources, optionally filtered by tag."""
    index = storage.load_index()
    entries = list(index.values())
    if tag:
        entries = [e for e in entries if tag.lower() in [t.lower() for t in e["tags"]]]
    return entries


@mcp.tool()
def read_wiki_page(path: str) -> str:
    """Read a wiki page (e.g. 'index', 'concepts/chain-of-thought', 'sources/react')."""
    try:
        return storage.read_wiki_page(path)
    except FileNotFoundError:
        return f"No wiki page found at '{path}'."


@mcp.tool()
def write_wiki_page(path: str, content: str) -> str:
    """Create or overwrite a wiki page."""
    storage.write_wiki_page(path, content)
    return f"Wiki page '{path}' written."


@mcp.tool()
def list_wiki_pages() -> list[str]:
    """List all wiki pages (paths relative to wiki/, without .md extension)."""
    pages = storage.list_wiki_pages()
    return pages if pages else ["(wiki is empty)"]


@mcp.tool()
def fetch_and_add_url(url: str, tags: list[str] | None = None) -> str:
    """Fetch a URL and store it as a source in the knowledge base."""
    content = _fetch_url(url)
    title = url.split("/")[-1].replace("-", " ").replace("_", " ").title() or url
    return store_source(title=title, content=content, source=url, tags=tags or ["web"])


@mcp.tool()
def add_local_file(path: str, title: str, tags: list[str] | None = None) -> str:
    """Read a local file (PDF or text) and store it as a source."""
    content = read_local_file(path)
    return store_source(title=title, content=content, source=path, tags=tags or ["file"])


if __name__ == "__main__":
    mcp.run()
