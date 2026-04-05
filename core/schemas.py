from pydantic import BaseModel


class ArticleMetadata(BaseModel):
    title: str
    slug: str
    source: str
    tags: list[str]
    created_at: str
    file_hash: str | None = None
