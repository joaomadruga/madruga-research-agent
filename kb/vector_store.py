import os

import psycopg2

from core.logger import get_logger
from kb.embeddings import DIMENSIONS

logger = get_logger(__name__)

_CREATE_EXTENSION = "CREATE EXTENSION IF NOT EXISTS vector;"

_CREATE_TABLE = f"""
CREATE TABLE IF NOT EXISTS article_embeddings (
    slug TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    embedding vector({DIMENSIONS}) NOT NULL
);
"""

_CREATE_INDEX = """
CREATE INDEX IF NOT EXISTS article_embeddings_embedding_idx
ON article_embeddings USING hnsw (embedding vector_cosine_ops);
"""


def _connect() -> psycopg2.extensions.connection:
    return psycopg2.connect(os.environ["DATABASE_URL"])


def init_db() -> None:
    with _connect() as conn, conn.cursor() as cur:
        cur.execute(_CREATE_EXTENSION)
        cur.execute(_CREATE_TABLE)
        cur.execute(_CREATE_INDEX)
    logger.info("Vector store ready (dims=%d)", DIMENSIONS)


def _to_pgvector(embedding: list[float]) -> str:
    return "[" + ",".join(str(x) for x in embedding) + "]"


def upsert(slug: str, title: str, embedding: list[float]) -> None:
    with _connect() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO article_embeddings (slug, title, embedding)
            VALUES (%s, %s, %s::vector)
            ON CONFLICT (slug) DO UPDATE
                SET title = EXCLUDED.title,
                    embedding = EXCLUDED.embedding
            """,
            (slug, title, _to_pgvector(embedding)),
        )
    logger.debug("Upserted embedding for '%s'", slug)


def search(query_embedding: list[float], top_k: int = 5) -> list[str]:
    with _connect() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT slug
            FROM article_embeddings
            ORDER BY embedding <=> %s::vector
            LIMIT %s
            """,
            (_to_pgvector(query_embedding), top_k),
        )
        results = [row[0] for row in cur.fetchall()]
    logger.debug("Vector search returned %d results", len(results))
    return results


def delete(slug: str) -> None:
    with _connect() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM article_embeddings WHERE slug = %s", (slug,))
    logger.debug("Deleted embedding for '%s'", slug)
