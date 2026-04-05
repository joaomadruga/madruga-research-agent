"""
Syncs the papers/ folder into the knowledge base.
Called automatically on startup — only processes new or changed files.
Can also be run standalone: uv run python ingest_papers.py
"""

from dotenv import load_dotenv

load_dotenv()

import hashlib
from pathlib import Path

from core.logger import get_logger
from parsers.pdf import read_pdf
from wiki.storage import KB_PATH, add_to_index, load_index, now_iso, slugify, write_source
from core.schemas import ArticleMetadata

logger = get_logger(__name__)

PAPERS_DIR = Path(__file__).parent / "papers"
WIKI_PATH = KB_PATH / "wiki"


def _hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _init_wiki() -> None:
    """Create wiki/index.md and wiki/log.md if they don't exist."""
    WIKI_PATH.mkdir(parents=True, exist_ok=True)
    index_path = WIKI_PATH / "index.md"
    log_path = WIKI_PATH / "log.md"
    if not index_path.exists():
        index_path.write_text("# Wiki Index\n\n*No pages yet. Ask the agent to process a source.*\n")
        logger.info("Created wiki/index.md")
    if not log_path.exists():
        log_path.write_text("# Research Log\n\n")
        logger.info("Created wiki/log.md")


def sync_papers() -> None:
    _init_wiki()

    pdfs = sorted(PAPERS_DIR.glob("*.pdf"))
    if not pdfs:
        return

    index = load_index()

    pending = []
    for pdf in pdfs:
        slug = slugify(pdf.stem.replace("_", " ").title())
        current_hash = _hash_file(pdf)
        stored = index.get(slug, {})
        if stored.get("file_hash") == current_hash:
            continue
        pending.append((pdf, slug, current_hash))

    if not pending:
        logger.info("papers/ — %d files, nothing changed", len(pdfs))
        return

    logger.info("Storing %d new/changed paper(s)...", len(pending))

    failed = []
    for pdf, slug, file_hash in pending:
        try:
            content = read_pdf(str(pdf))
            title = pdf.stem.replace("_", " ").title()
            write_source(slug, content)
            metadata = ArticleMetadata(
                title=title,
                slug=slug,
                source=str(pdf),
                tags=["paper"],
                created_at=now_iso(),
                file_hash=file_hash,
            )
            add_to_index(metadata)
            logger.info("Stored '%s'", title)
        except Exception as exc:
            logger.error("Failed to store '%s': %s", pdf.name, exc)
            failed.append(pdf.name)

    if failed:
        logger.error("Failed to store: %s", ", ".join(failed))
    else:
        logger.info("All %d papers stored. Use the agent to process them into the wiki.", len(pending))


if __name__ == "__main__":
    sync_papers()
