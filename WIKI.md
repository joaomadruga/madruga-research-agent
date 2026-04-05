# Wiki Schema

This file documents the conventions for the knowledge base wiki at `knowledge_base/wiki/`.

## Directory structure

```
knowledge_base/wiki/
├── index.md        # Master catalog — updated on every ingest
├── log.md          # Append-only research log
├── sources/        # One page per ingested source
├── concepts/       # Concept pages (e.g. chain-of-thought, tool-use, RLHF)
├── entities/       # Entity pages (e.g. openai, deepmind, specific models)
└── ...             # Any structure that fits the domain
```

## Page frontmatter

Every wiki page should start with YAML frontmatter:

```yaml
---
title: Page Title
tags: [tag1, tag2]
sources: [react, chain-of-thought]   # slugs of sources that inform this page
updated: 2026-04-05
---
```

## index.md format

One entry per page, grouped by category:

```markdown
## Sources
- [ReAct](sources/react.md) — synergizing reasoning and acting in language models
- [Chain-of-Thought](sources/chain-of-thought.md) — prompting for multi-step reasoning

## Concepts
- [Tool Use](concepts/tool-use.md) — LLMs calling external tools and APIs
```

## log.md format

Append-only. Each entry on its own `##` heading for easy grepping:

```markdown
## [2026-04-05] ingest | ReAct: Synergizing Reasoning and Acting
## [2026-04-05] query | comparison of ReAct vs Chain-of-Thought → filed as comparisons/react-vs-cot
## [2026-04-06] lint | flagged 3 orphan pages, added missing cross-refs
```

## Cross-reference convention

Use standard markdown links relative to the wiki root:

```markdown
See also: [Chain-of-Thought](../concepts/chain-of-thought.md)
```

## Source pages (wiki/sources/)

Structured summary of a single ingested source:

```markdown
## Summary
(2-3 sentences)

## Key Points
- ...

## Implications
(why this matters)

## Connections
- [Chain-of-Thought](../concepts/chain-of-thought.md) — builds on this
- [Tool Use](../concepts/tool-use.md) — ReAct extends CoT with tool calls
```

## Concept pages (wiki/concepts/)

Free-form synthesis page for a recurring idea:

```markdown
## Overview
(what this concept is)

## Key Papers
- [ReAct](../sources/react.md)
- [MRKL](../sources/mrkl.md)

## Open Questions
- ...
```
