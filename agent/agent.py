from langchain_core.messages import BaseMessage, HumanMessage, ToolMessage

from core.logger import get_logger
from agent.provider import get_llm
from tools.kb_tools import get_tool_list

logger = get_logger(__name__)

_SYSTEM_PROMPT = """\
You are a research assistant that maintains a personal wiki — a directory of interlinked markdown files in knowledge_base/wiki/.

The wiki has two special files you must keep up to date:
- wiki/index.md — master catalog: one line per page, format: `- [Title](path.md) — one-sentence description`
- wiki/log.md — append-only record, format: `## [YYYY-MM-DD] operation | description`

Always start by calling read_wiki_page("index") to orient yourself before answering any question.

---

INGEST — when asked to process, ingest, or add a source:
1. Call read_source(slug) to read the raw text
2. Call write_wiki_page("sources/{slug}", ...) with a rich summary:
   - ## Summary (2-3 sentences)
   - ## Key Points (bullets)
   - ## Implications (why it matters)
   - ## Connections (links to related concept/entity pages — create them if they don't exist)
3. Create or update concept/entity pages touched by this source (e.g. wiki/concepts/chain-of-thought.md)
4. Update wiki/index.md to catalog the new/changed pages
5. Append to wiki/log.md: `## [today] ingest | {title}`

QUERY — when answering a question:
1. Call search_wiki(query) to find relevant wiki pages
2. Call read_wiki_page(path) on the top results
3. Synthesize an answer with citations linking to wiki pages
4. If the answer is a valuable synthesis, offer to file it as a new wiki page
If search_wiki returns no results, fall back to read_wiki_page("index") and navigate from there.

LINT — when asked to health-check the wiki:
1. Read wiki/index.md
2. Report: orphan pages (no inbound links), stale claims, missing cross-refs, concept gaps
3. Suggest new sources or investigations

---

Never ask for clarification — attempt a tool call first. Format responses as markdown.
"""


class Agent:
    def __init__(self) -> None:
        tool_list = get_tool_list()
        self._tool_map = {t.name: t for t in tool_list}
        self._llm = get_llm().bind_tools(tool_list)
        self._history: list[BaseMessage] = []
        logger.info("Agent ready with %d tools", len(tool_list))

    def chat(self, user_message: str) -> str:
        self._history.append(HumanMessage(content=user_message))

        while True:
            response = self._llm.invoke(
                [HumanMessage(content=_SYSTEM_PROMPT)] + self._history
            )
            self._history.append(response)

            if not response.tool_calls:
                return response.content

            tool_results = []
            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                logger.info("Tool call: %s", tool_name)
                tool_fn = self._tool_map[tool_name]
                result = tool_fn.invoke(tool_call["args"])
                tool_results.append(
                    ToolMessage(
                        content=str(result),
                        tool_call_id=tool_call["id"],
                    )
                )

            self._history.extend(tool_results)

    def clear_history(self) -> None:
        self._history = []
        logger.debug("Conversation history cleared")
