# Research Agent

## What this is

This is not a RAG system. It does not retrieve document chunks at query time and re-derive answers from scratch. Instead, the LLM incrementally builds and maintains a **persistent wiki** — a structured, interlinked collection of markdown files that sits between you and the raw sources.

When a new source is added, the LLM reads it and integrates it into the existing wiki: writing a summary page, updating concept and entity pages, noting connections and contradictions, keeping the synthesis current. The wiki compounds over time. Cross-references are already there. Contradictions have already been flagged. The synthesis already reflects everything that has been read.

**The human** curates sources, asks questions, and directs the analysis.
**The LLM** does everything else — summarizing, cross-referencing, filing, bookkeeping.

---

## Architecture

```
knowledge_base/
├── index.json          # Source registry — hash-based dedup, do not edit manually
├── sources/            # Raw extracted text — immutable, LLM reads but never writes
│   └── react.md
└── wiki/               # LLM-owned — create, update, delete freely
    ├── index.md        # Master catalog of every wiki page
    ├── log.md          # Append-only research log
    ├── sources/        # One summary page per ingested source
    ├── concepts/       # Concept pages (e.g. chain-of-thought, tool-use, RLHF)
    ├── entities/       # Entity pages (models, labs, people)
    └── ...             # Any structure that fits — you decide
```

**Raw sources are immutable.** The LLM reads them, never modifies them.
**The wiki is entirely LLM-owned.** Create pages, update them, reorganize freely.
**index.md and log.md must always be kept current.**

---

## Tools

| Tool | Purpose |
|------|---------|
| `search_wiki(query)` | BM25 search over all wiki pages via qmd — use this first |
| `read_wiki_page(path)` | Read a wiki page (e.g. `"index"`, `"concepts/tool-use"`) |
| `write_wiki_page(path, content)` | Create or overwrite a wiki page |
| `list_wiki_pages()` | List all pages in wiki/ |
| `read_source(slug)` | Read a raw source |
| `describe_pdf_visuals(slug)` | Vision LLM descriptions of all figures/diagrams in a PDF |
| `store_source(...)` | Save raw content + register in index |
| `list_sources(tag?)` | List registered sources |
| `fetch_url(url)` | Scrape a web page |
| `search_web(query)` | Tavily web search (requires TAVILY_API_KEY) |

**Search is powered by qmd** — a local BM25/vector search engine for markdown. After writing new wiki pages, remind the user to run `qmd embed` to update vector embeddings.

---

## Operations

### Ingest — when asked to process, add, or ingest a source

1. Call `read_source(slug)` to read the raw text
2. If the source is a PDF, call `describe_pdf_visuals(slug)` to get vision LLM descriptions of all embedded figures and diagrams
3. Write `wiki/sources/{slug}.md` with:
   - `## Summary` — 2-3 sentence overview
   - `## Key Points` — bullet list of core ideas
   - `## Implications` — why it matters, what it challenges
   - `## Connections` — links to concept/entity pages (create them if they don't exist yet)
   - `## Figures` — visual descriptions from `describe_pdf_visuals` (PDF sources only)
4. Create or update every concept/entity page this source touches
5. Update `wiki/index.md` — add entries for new pages, update descriptions for changed ones
6. Append to `wiki/log.md`: `## [YYYY-MM-DD] ingest | {title}`

A single source may touch 10–15 wiki pages. That is expected and correct.

### Query — when answering a question

1. Call `search_wiki(query)` to find relevant pages
2. Call `read_wiki_page(path)` on the top results
3. Synthesize an answer with citations linking to wiki pages
4. If the answer is a valuable synthesis (a comparison, an analysis, a discovered connection), offer to file it as a new wiki page — good answers should not disappear into chat history

If `search_wiki` returns nothing, fall back to `read_wiki_page("index")` and navigate from there.

### Lint — when asked to health-check the wiki

1. Read `wiki/index.md` to see all pages
2. Report:
   - Orphan pages — pages with no inbound links from other pages
   - Stale claims — assertions contradicted by newer sources
   - Missing concept pages — concepts mentioned in multiple source pages but lacking their own page
   - Data gaps — questions that could be answered by a targeted web search
3. Suggest new sources or investigations worth pursuing
4. Append to `wiki/log.md`: `## [YYYY-MM-DD] lint | {summary of findings}`

---

## Wiki conventions

### index.md format

```markdown
## Sources
- [ReAct](sources/react.md) — synergizing reasoning and acting in language models
- [Chain-of-Thought](sources/chain-of-thought.md) — prompting for multi-step reasoning

## Concepts
- [Tool Use](concepts/tool-use.md) — LLMs calling external tools and APIs
- [Chain-of-Thought](concepts/chain-of-thought.md) — step-by-step reasoning traces
```

### log.md format

Append-only. Each entry starts with `## [YYYY-MM-DD]` for easy grepping:

```markdown
## [2026-04-05] ingest | ReAct: Synergizing Reasoning and Acting
## [2026-04-05] query | comparison of ReAct vs CoT → filed as comparisons/react-vs-cot
## [2026-04-06] lint | 3 orphan pages, added tool-use concept page
```

### Page frontmatter

```yaml
---
title: Page Title
tags: [tag1, tag2]
sources: [react, chain-of-thought]
updated: 2026-04-05
---
```

### Cross-references

Use standard markdown links relative to the wiki root:

```markdown
See also: [Chain-of-Thought](../concepts/chain-of-thought.md)
```

---

## Adding a new source

**PDFs in `papers/`** are auto-stored on startup — text is extracted and registered in `index.json`. The wiki is not updated automatically. To integrate a new paper into the wiki, say: *"process the X paper"*.

**Web articles**: say *"add [url]"* — the agent fetches, stores, and integrates it.

**After ingesting and writing new wiki pages**, run:
```bash
qmd embed
```
This updates qmd's search index so new pages are findable.

---

## What not to do

- Do not modify files in `knowledge_base/sources/` — raw sources are immutable
- Do not edit `knowledge_base/index.json` manually — it is managed by `store_source`
- Do not add embedding infrastructure, vector databases, or RAG pipelines — the wiki + qmd search is the retrieval layer
- Do not auto-generate wiki content on ingestion without user involvement — the human should stay in the loop on what gets emphasized
