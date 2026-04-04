"""
Syncs the papers/ folder into the knowledge base.
Called automatically on startup — only processes new or changed files.
Can also be run standalone: uv run python ingest_papers.py
"""

import hashlib
from pathlib import Path

from core.logger import get_logger
from ingestion.pdf import read_pdf
from kb.storage import load_index, slugify
from tools.kb_tools import add_article

logger = get_logger(__name__)

PAPERS_DIR = Path(__file__).parent / "papers"


def _hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sync_papers() -> None:
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

    logger.info("Ingesting %d new/changed paper(s)...", len(pending))

    failed = []
    for pdf, slug, file_hash in pending:
        try:
            content = read_pdf(str(pdf))
            title = pdf.stem.replace("_", " ").title()
            add_article.invoke({
                "title": title,
                "content": content,
                "source": str(pdf),
                "tags": ["paper"],
                "file_hash": file_hash,
            })
        except Exception as exc:
            logger.error("Failed to ingest '%s': %s", pdf.name, exc)
            failed.append(pdf.name)

    if failed:
        logger.error("Failed to ingest: %s", ", ".join(failed))
    else:
        logger.info("All %d papers ingested successfully", len(pending))


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()

    from kb.vector_store import init_db

    init_db()
    sync_papers()
