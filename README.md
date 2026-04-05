# Research Agent

A personal knowledge base that compounds over time. Drop PDFs into `papers/`, add URLs, ask questions — the LLM maintains a structured wiki of interlinked markdown files that gets richer with every source you add.

## How it works

```
papers/*.pdf  ──►  ingest  ──►  knowledge_base/sources/  (raw text, immutable)
URL / manual  ──►  store   ──►                            (same)
                                        │
                              agent reads source
                                        │
                              writes wiki pages ──►  knowledge_base/wiki/
                                        │                 sources/, concepts/, entities/
                              you ask a question          index.md, log.md
                                        │
                              agent reads wiki pages ──►  synthesized answer
```

- **Raw sources** are stored in `knowledge_base/sources/` — the LLM reads them, never modifies them
- **The wiki** lives in `knowledge_base/wiki/` — entirely LLM-maintained markdown
- **On every startup**, `papers/` is synced — only new or changed files are ingested (SHA-256 hash check)

## Requirements

- [uv](https://docs.astral.sh/uv/)
- An LLM provider: [Anthropic](https://console.anthropic.com), [Ollama](https://ollama.com), or OpenAI

## Setup

**1. Configure `.env`**

```bash
cp .env.example .env
```

Edit `.env` to set your provider and API key. Defaults to Anthropic.

**2. Install dependencies**

```bash
uv sync
```

## Running

```bash
uv run python main.py
```

On first run, all PDFs in `papers/` are ingested automatically. Subsequent runs only process new or modified files.

### CLI commands

| Command  | Action                                                   |
|----------|----------------------------------------------------------|
| `/list`  | Show all sources in the knowledge base                   |
| `/lint`  | Health-check the wiki (orphans, stale claims, gaps)      |
| `/clear` | Clear conversation history (knowledge base is kept)      |
| `/exit`  | Quit                                                     |

Everything else is free-form:

```
you> what papers do you have about reasoning?
you> ingest react
you> how does ReAct compare to Plan and Solve?
you> add this article: https://example.com/paper
```

## Adding content

**PDFs** — drop them into `papers/` and restart. Ingested automatically.

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

```env
LLM_PROVIDER=anthropic   # anthropic | ollama | openai
MODEL=claude-sonnet-4-6
ANTHROPIC_API_KEY=your-key-here
```

## Claude Code integration (MCP)

The agent exposes its tools as an MCP server so Claude Code can read and write your knowledge base directly from any session.

**Register once:**

```bash
claude mcp add research-agent uv -- --directory /path/to/research-agent run python mcp_server.py
```

**Verify:**

```bash
claude mcp list
```

**Available tools in Claude Code:**

- `store_source` — save raw content to the knowledge base
- `read_source` — read the raw text of a stored source
- `list_sources` — browse the index, optionally filtered by tag
- `read_wiki_page` — read a wiki page (e.g. `index`, `concepts/chain-of-thought`)
- `write_wiki_page` — create or overwrite a wiki page
- `list_wiki_pages` — list all wiki pages
- `fetch_and_add_url` — fetch a URL and store it as a source
- `add_local_file` — ingest a local PDF or text file

## Wiki schema

See [`WIKI.md`](WIKI.md) for the wiki directory structure, page formats, frontmatter conventions, and how `index.md` / `log.md` are maintained.

## Project structure

```
research-agent/
├── main.py              # CLI entry point (REPL)
├── mcp_server.py        # MCP server for Claude Code integration
├── ingest_papers.py     # PDF sync logic (called on startup)
├── WIKI.md              # Wiki schema and conventions
├── papers/              # Drop PDFs here
├── knowledge_base/
│   ├── index.json       # Source metadata registry
│   ├── sources/         # Raw ingested content (immutable)
│   └── wiki/            # LLM-maintained wiki pages
├── core/
│   ├── logger.py
│   └── schemas.py
├── kb/
│   └── storage.py       # File I/O and index management
├── llm/
│   ├── provider.py      # LLM factory (anthropic / ollama / openai)
│   └── agent.py         # Tool-call loop
├── ingestion/
│   ├── web.py           # URL scraping
│   └── pdf.py           # PDF and local file reading
└── tools/
    └── kb_tools.py      # LangChain tool definitions
```

## Known limitations

- **Conversation history is in-memory** — lost on restart. The knowledge base itself is the persistence layer.
