from pathlib import Path

from pypdf import PdfReader

from core.logger import get_logger

logger = get_logger(__name__)


def read_pdf(path: str) -> str:
    file_path = Path(path).expanduser()
    logger.info("Reading PDF: %s", file_path.name)
    reader = PdfReader(file_path)
    text = "\n\n".join(page.extract_text() or "" for page in reader.pages)
    logger.debug("Extracted %d chars from %d pages", len(text), len(reader.pages))
    return text


def read_local_file(path: str) -> str:
    file_path = Path(path).expanduser()
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    if file_path.suffix.lower() == ".pdf":
        return read_pdf(path)
    return file_path.read_text()
