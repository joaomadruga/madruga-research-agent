from langchain_core.messages import BaseMessage, HumanMessage, ToolMessage

from core.logger import get_logger
from llm.provider import get_llm
from tools.kb_tools import get_tool_list

logger = get_logger(__name__)

_SYSTEM_PROMPT = """\
You are a research assistant with access to a local knowledge base of articles and papers.

MANDATORY BEHAVIOR — no exceptions:
- Your FIRST action for ANY question or topic must be to call search_knowledge_base. Do this before writing a single word of response.
- If the user names a specific paper or article, call search_knowledge_base with that name, then call deep_dive_article on the slug of the best match.
- Never ask for clarification. Always attempt a tool call first.
- When adding a URL: call fetch_url, then add_article.
- Format responses as markdown. Be concise.
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
