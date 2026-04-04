import requests
from bs4 import BeautifulSoup

from core.logger import get_logger

logger = get_logger(__name__)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


def fetch_url(url: str) -> str:
    logger.info("Fetching URL: %s", url)
    response = requests.get(url, headers=_HEADERS, timeout=15)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()

    for selector in ["article", "main", '[role="main"]']:
        container = soup.select_one(selector)
        if container:
            text = container.get_text(separator="\n", strip=True)
            logger.debug("Extracted %d chars from <%s>", len(text), selector)
            return text

    text = soup.body.get_text(separator="\n", strip=True) if soup.body else ""
    logger.debug("Extracted %d chars from <body>", len(text))
    return text
