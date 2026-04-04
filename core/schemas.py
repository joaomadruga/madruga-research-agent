from pydantic import BaseModel


class ArticleMetadata(BaseModel):
    title: str
    slug: str
    source: str
    tags: list[str]
    created_at: str
    file_hash: str | None = None


class SearchResult(BaseModel):
    slug: str
    title: str
    excerpt: str


class DeepDiveResult(BaseModel):
    metadata: ArticleMetadata
    wiki: str
    raw: str
