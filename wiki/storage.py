import json
import re
from datetime import datetime, timezone
from pathlib import Path

from core.logger import get_logger
from core.schemas import ArticleMetadata

logger = get_logger(__name__)

KB_PATH = Path.home() / "Desktop" / "research-agent" / "knowledge_base"
INDEX_PATH = KB_PATH / "index.json"
SOURCES_PATH = KB_PATH / "sources"
WIKI_PATH = KB_PATH / "wiki"


def _ensure_dirs() -> None:
    SOURCES_PATH.mkdir(parents=True, exist_ok=True)
    WIKI_PATH.mkdir(parents=True, exist_ok=True)


def slugify(title: str) -> str:
    slug = title.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug[:80]


def load_index() -> dict[str, dict]:
    if not INDEX_PATH.exists():
        return {}
    return json.loads(INDEX_PATH.read_text())


def save_index(index: dict[str, dict]) -> None:
    _ensure_dirs()
    INDEX_PATH.write_text(json.dumps(index, indent=2))


def write_source(slug: str, content: str) -> None:
    _ensure_dirs()
    (SOURCES_PATH / f"{slug}.md").write_text(content)
    logger.debug("Wrote source content for '%s'", slug)


def read_source(slug: str) -> str:
    return (SOURCES_PATH / f"{slug}.md").read_text()


def write_wiki_page(rel_path: str, content: str) -> None:
    """Write a wiki page at wiki/{rel_path}.md, creating parent dirs as needed."""
    _ensure_dirs()
    page_path = WIKI_PATH / f"{rel_path}.md"
    page_path.parent.mkdir(parents=True, exist_ok=True)
    page_path.write_text(content)
    logger.debug("Wrote wiki page '%s'", rel_path)


def read_wiki_page(rel_path: str) -> str:
    """Read wiki/{rel_path}.md."""
    return (WIKI_PATH / f"{rel_path}.md").read_text()


def list_wiki_pages() -> list[str]:
    """Return all wiki page paths relative to wiki/ (without .md extension)."""
    if not WIKI_PATH.exists():
        return []
    return [
        str(p.relative_to(WIKI_PATH)).removesuffix(".md")
        for p in sorted(WIKI_PATH.rglob("*.md"))
    ]


def delete_source(slug: str) -> None:
    source_file = SOURCES_PATH / f"{slug}.md"
    if source_file.exists():
        source_file.unlink()
    index = load_index()
    index.pop(slug, None)
    save_index(index)
    logger.info("Deleted source '%s'", slug)


def add_to_index(metadata: ArticleMetadata) -> None:
    index = load_index()
    index[metadata.slug] = metadata.model_dump()
    save_index(index)
    logger.info("Indexed source '%s'", metadata.slug)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
