import base64
import os
import subprocess
from typing import Annotated

from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from tavily import TavilyClient

import wiki.storage as storage
from core.logger import get_logger
from core.schemas import ArticleMetadata
from parsers.pdf import extract_pdf_images
from parsers.web import fetch_url as _fetch_url
from agent.provider import get_llm

logger = get_logger(__name__)


@tool
def store_source(
    title: Annotated[str, "Title of the article or paper"],
    content: Annotated[str, "Full text content"],
    source: Annotated[str, "URL or file path or 'manual'"],
    tags: Annotated[list[str], "List of topic tags"],
    file_hash: Annotated[str | None, "SHA-256 hash of the source file, if any"] = None,
) -> str:
    """Save raw source content and register it in the index. Does not create wiki pages."""
    slug = storage.slugify(title)
    index = storage.load_index()

    if slug in index and file_hash is None:
        slug = f"{slug}-{storage.now_iso()[:10]}"

    storage.write_source(slug, content)

    metadata = ArticleMetadata(
        title=title,
        slug=slug,
        source=source,
        tags=tags,
        created_at=storage.now_iso(),
        file_hash=file_hash,
    )
    storage.add_to_index(metadata)

    logger.info("Source '%s' stored (slug: %s)", title, slug)
    return f"Source '{title}' stored with slug '{slug}'."


@tool
def read_source(
    slug: Annotated[str, "Slug of the source"],
) -> str:
    """Read the raw text of a stored source."""
    index = storage.load_index()
    if slug not in index:
        return f"No source found with slug '{slug}'."
    return storage.read_source(slug)


@tool
def list_sources(
    tag: Annotated[str | None, "Filter by tag (optional)"] = None,
) -> list[dict]:
    """List all stored sources, optionally filtered by tag."""
    index = storage.load_index()
    entries = list(index.values())
    if tag:
        entries = [e for e in entries if tag.lower() in [t.lower() for t in e["tags"]]]
    return entries


@tool
def delete_source(
    slug: Annotated[str, "Slug of the source to delete"],
) -> str:
    """Delete a source and its wiki/sources page from the knowledge base."""
    index = storage.load_index()
    if slug not in index:
        return f"No source found with slug '{slug}'."
    title = index[slug]["title"]
    storage.delete_source(slug)
    return f"Deleted source '{title}' (slug: '{slug}')."


@tool
def read_wiki_page(
    path: Annotated[str, "Wiki page path relative to wiki/ (e.g. 'index', 'concepts/chain-of-thought', 'sources/react')"],
) -> str:
    """Read a wiki page. Use 'index' to see all pages and navigate the wiki."""
    try:
        return storage.read_wiki_page(path)
    except FileNotFoundError:
        return f"No wiki page found at '{path}'. Call list_wiki_pages to see what exists."


@tool
def write_wiki_page(
    path: Annotated[str, "Wiki page path relative to wiki/ (e.g. 'concepts/tool-use', 'sources/react')"],
    content: Annotated[str, "Full markdown content for this page"],
) -> str:
    """Create or overwrite a wiki page. Use this to build and maintain the wiki."""
    storage.write_wiki_page(path, content)
    return f"Wiki page '{path}' written."


@tool
def list_wiki_pages() -> list[str]:
    """List all wiki pages. Returns paths relative to wiki/ (without .md extension)."""
    pages = storage.list_wiki_pages()
    if not pages:
        return ["(wiki is empty — no pages yet)"]
    return pages


@tool
def describe_pdf_visuals(
    slug: Annotated[str, "Slug of the PDF source to analyze"],
) -> str:
    """Describe all figures and diagrams in a PDF source using vision LLM.
    Only processes pages that actually contain images — skips text-only pages.
    Call this alongside read_source() when ingesting a paper."""
    index = storage.load_index()
    if slug not in index:
        return f"No source found with slug '{slug}'."

    source_path = index[slug]["source"]
    if not source_path.endswith(".pdf"):
        return "Source is not a PDF."

    images = extract_pdf_images(source_path)
    if not images:
        return "No embedded images found in this PDF."

    llm = get_llm()
    descriptions = []

    for page_num, page_text, img_bytes in images:
        b64 = base64.standard_b64encode(img_bytes).decode()
        prompt = (
            f"You are analyzing a figure from a research paper.\n\n"
            f"Page {page_num} text:\n{page_text}\n\n"
            f"Describe what this figure shows, referencing the surrounding text for context. "
            f"Include: what type of visual it is (chart, diagram, table, architecture, etc.), "
            f"what it demonstrates, and any key values or labels."
        )
        message = HumanMessage(content=[
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
        ])
        response = llm.invoke([message])
        description = response.content.strip()
        if description and "no visual content" not in description.lower():
            descriptions.append(f"## Figure (page {page_num})\n\n{description}")

    if not descriptions:
        return "No meaningful visual content found."

    return "\n\n".join(descriptions)


@tool
def search_wiki(
    query: Annotated[str, "Search query to find relevant wiki pages"],
    limit: Annotated[int, "Maximum number of results to return"] = 5,
) -> str:
    """Search the wiki using qmd hybrid search (BM25 + semantic vector). Returns relevant page paths and excerpts.
    Use this before read_wiki_page to find which pages are relevant to a question."""
    # Hybrid search: combines lex (BM25 keyword) and vec (semantic vector) for best recall
    structured_query = f"lex:{query}\nvec:{query}"
    result = subprocess.run(
        ["qmd", "query", structured_query, "--json", "-n", str(limit)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return f"qmd search unavailable: {result.stderr.strip()}. Fall back to read_wiki_page('index')."
    return result.stdout or "No results found."


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
        store_source,
        read_source,
        describe_pdf_visuals,
        list_sources,
        delete_source,
        search_wiki,
        read_wiki_page,
        write_wiki_page,
        list_wiki_pages,
        fetch_url,
        search_web,
    ]
