# It is really hard to keep up with all the articles context in my brain so i'm splitting the responsability with an agent. Everything bellow is claude generated:

# Research Agent

A local, provider-agnostic research knowledge base powered by LLMs. Drop PDFs into `papers/`, ask questions, and get semantically-searched answers — all running on your machine.

## How it works

```
papers/*.pdf  ──►  ingest (pypdf)  ──►  wiki note (LLM)  ──►  embedding  ──►  pgvector
                                                                                    │
you> what do I know about chain of thought?  ──►  embed query  ──►  cosine search ─┘
                                                                         │
                                                              LLM answers from top-k wikis
```

- **Raw content** is stored in `knowledge_base/raw/`
- **Compiled summaries** (wiki notes) are stored in `knowledge_base/wiki/`
- **Embeddings** live in PostgreSQL with pgvector
- **On every startup**, the `papers/` folder is synced — only new or changed files are re-ingested (SHA-256 hash check)

## Requirements

- [uv](https://docs.astral.sh/uv/)
- [Ollama](https://ollama.com) — for local LLM and embeddings
- [Docker](https://www.docker.com) — for PostgreSQL + pgvector

## Setup

**1. Pull models**

```bash
ollama pull Gemma3:12b        # or any model you prefer
ollama pull nomic-embed-text  # embedding model
```

**2. Start the database**

```bash
docker compose up -d
```

Postgres runs on port `5433` (to avoid conflicts with existing installations).

| Field    | Value            |
|----------|------------------|
| Host     | localhost:5433   |
| Database | research_agent   |
| User     | research         |
| Password | research         |

**3. Configure `.env`**

```bash
cp .env.example .env
```

Edit `.env` to match your setup. Defaults work out of the box for Ollama.

**4. Install dependencies**

```bash
uv sync
```

## Running

```bash
uv run python main.py
```

On first run, all PDFs in `papers/` are ingested automatically. Subsequent runs only process new or modified files.

### CLI commands

| Command  | Action                              |
|----------|-------------------------------------|
| `/list`  | Show all articles in the knowledge base |
| `/clear` | Clear conversation history (KB is kept) |
| `/exit`  | Quit                                |

Everything else is free-form — just talk to it:

```
you> what papers do you have about reasoning?
you> deep dive into react
you> how does ReAct compare to Plan and Solve?
you> add this article: https://example.com/paper
```

## Adding content

**PDFs** — drop them into `papers/` and restart. They'll be ingested automatically.

**URLs** — ask the agent directly:
```
you> add this article: https://...
```

**Manual** — tell the agent:
```
you> add a note titled "My Research Notes" with content: ...
```

## Provider configuration

All providers are switched via `.env` — no code changes needed.

### LLM

```env
LLM_PROVIDER=ollama        # ollama | anthropic | openai
MODEL=Gemma3:12b
OLLAMA_BASE_URL=http://localhost:11434
```

### Embeddings

```env
EMBEDDING_PROVIDER=ollama  # ollama | gemini
EMBEDDING_MODEL=nomic-embed-text
```

> **Note:** Changing embedding providers requires dropping the `article_embeddings` table and re-ingesting, since vector dimensions differ between models.

Supported embedding models and their dimensions:

| Model                        | Provider | Dimensions |
|------------------------------|----------|------------|
| `nomic-embed-text`           | ollama   | 768        |
| `mxbai-embed-large`          | ollama   | 1024       |
| `gemini-embedding-2-preview` | gemini   | 3072       |

## Claude Code integration (MCP)

The agent exposes its tools as an MCP server so Claude Code can query your knowledge base directly from any session.

**Register once:**

```bash
claude mcp add research-agent uv -- --directory /path/to/research-agent run python mcp_server.py
```

**Verify:**

```bash
claude mcp list
```

Make sure Ollama and Docker are running before opening Claude Code — the MCP server connects to both at startup.

**Available tools in Claude Code:**

- `search_knowledge_base` — semantic search over all articles
- `deep_dive_article` — load full raw + wiki content into context
- `list_articles` — browse the index
- `add_article` — add content manually
- `fetch_and_add_url` — fetch a URL and add it
- `add_local_file` — ingest a local PDF or text file
- `delete_article` — remove an article

## Project structure

```
research-agent/
├── main.py              # CLI entry point (REPL)
├── mcp_server.py        # MCP server for Claude Code integration
├── ingest_papers.py     # PDF sync logic (called on startup)
├── papers/              # Drop PDFs here
├── knowledge_base/
│   ├── index.json       # Article metadata registry
│   ├── raw/             # Original ingested content
│   └── wiki/            # LLM-compiled structured summaries
├── core/
│   ├── logger.py        # Structured logging via RichHandler
│   └── schemas.py       # Pydantic models
├── kb/
│   ├── storage.py       # File I/O and index management
│   ├── embeddings.py    # Gemini / Ollama embedding client
│   └── vector_store.py  # pgvector operations
├── llm/
│   ├── provider.py      # LLM factory (anthropic / ollama / openai)
│   └── agent.py         # Tool-call loop (LangChain)
├── ingestion/
│   ├── web.py           # URL scraping
│   └── pdf.py           # PDF and local file reading
└── tools/
    └── kb_tools.py      # LangChain tool definitions
```

## Known limitations

- **PDF images are ignored** — figures, charts, and diagrams in papers are not embedded. Only text is extracted via `pypdf`.
- **Conversation history is in-memory** — lost on restart. The knowledge base itself is the persistence layer.
- **No authentication** — the Postgres instance has no TLS or strong credentials, intended for local use only.
