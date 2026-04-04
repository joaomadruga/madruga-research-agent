import io
from pathlib import Path

import fitz  # pymupdf
from PIL import Image
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


def render_pdf_pages(path: str, dpi: int = 150) -> list[Image.Image]:
    """Render each PDF page as a PIL Image for multimodal embedding."""
    file_path = Path(path).expanduser()
    doc = fitz.open(str(file_path))
    pages = []
    matrix = fitz.Matrix(dpi / 72, dpi / 72)
    for page in doc:
        pix = page.get_pixmap(matrix=matrix)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        pages.append(img)
    doc.close()
    logger.debug("Rendered %d page(s) from '%s' at %d DPI", len(pages), file_path.name, dpi)
    return pages


def split_pdf_chunks(path: str, chunk_size: int = 6) -> list[bytes]:
    """Split a PDF into byte chunks of up to chunk_size pages each."""
    file_path = Path(path).expanduser()
    source_doc = fitz.open(str(file_path))
    total_pages = len(source_doc)
    chunks = []

    for start in range(0, total_pages, chunk_size):
        end = min(start + chunk_size, total_pages)
        chunk_doc = fitz.open()
        chunk_doc.insert_pdf(source_doc, from_page=start, to_page=end - 1)
        buf = io.BytesIO()
        chunk_doc.save(buf)
        chunks.append(buf.getvalue())
        chunk_doc.close()

    source_doc.close()
    logger.debug("Split '%s' into %d chunk(s) of up to %d pages", file_path.name, len(chunks), chunk_size)
    return chunks


def read_local_file(path: str) -> str:
    file_path = Path(path).expanduser()
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    if file_path.suffix.lower() == ".pdf":
        return read_pdf(path)
    return file_path.read_text()
