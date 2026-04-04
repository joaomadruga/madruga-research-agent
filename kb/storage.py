import json
import re
from datetime import datetime, timezone
from pathlib import Path

from core.logger import get_logger
from core.schemas import ArticleMetadata

logger = get_logger(__name__)

KB_PATH = Path.home() / "Desktop" / "research-agent" / "knowledge_base"
INDEX_PATH = KB_PATH / "index.json"
RAW_PATH = KB_PATH / "raw"
WIKI_PATH = KB_PATH / "wiki"


def _ensure_dirs() -> None:
    RAW_PATH.mkdir(parents=True, exist_ok=True)
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


def write_raw(slug: str, content: str) -> None:
    _ensure_dirs()
    (RAW_PATH / f"{slug}.md").write_text(content)
    logger.debug("Wrote raw content for '%s'", slug)


def write_wiki(slug: str, content: str) -> None:
    _ensure_dirs()
    (WIKI_PATH / f"{slug}.md").write_text(content)
    logger.debug("Wrote wiki note for '%s'", slug)


def read_wiki(slug: str) -> str:
    return (WIKI_PATH / f"{slug}.md").read_text()


def read_raw(slug: str) -> str:
    return (RAW_PATH / f"{slug}.md").read_text()


def delete_article(slug: str) -> None:
    raw_file = RAW_PATH / f"{slug}.md"
    wiki_file = WIKI_PATH / f"{slug}.md"
    if raw_file.exists():
        raw_file.unlink()
    if wiki_file.exists():
        wiki_file.unlink()
    index = load_index()
    index.pop(slug, None)
    save_index(index)
    logger.info("Deleted article '%s'", slug)


def add_to_index(metadata: ArticleMetadata) -> None:
    index = load_index()
    index[metadata.slug] = metadata.model_dump()
    save_index(index)
    logger.info("Indexed article '%s'", metadata.slug)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
