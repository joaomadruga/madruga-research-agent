from pathlib import Path

import fitz  # pymupdf
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


def extract_pdf_images(path: str) -> list[tuple[int, str, bytes]]:
    """Extract all embedded images from a PDF with their page text context.

    Returns (page_number, page_text, image_bytes) triples.
    Skips images smaller than 100x100px (icons, decorations).
    """
    file_path = Path(path).expanduser()
    doc = fitz.open(str(file_path))
    results = []
    for page_index, page in enumerate(doc):
        page_text = page.get_text()
        for img in page.get_images():
            xref = img[0]
            img_data = doc.extract_image(xref)
            w, h = img_data["width"], img_data["height"]
            if w >= 100 and h >= 100:
                results.append((page_index + 1, page_text, img_data["image"]))
    doc.close()
    logger.debug("Extracted %d image(s) from '%s'", len(results), file_path.name)
    return results


def read_local_file(path: str) -> str:
    file_path = Path(path).expanduser()
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    if file_path.suffix.lower() == ".pdf":
        return read_pdf(path)
    return file_path.read_text()
