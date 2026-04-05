import sys

from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

load_dotenv()

from ingest_papers import sync_papers
from wiki.storage import load_index
from agent.agent import Agent

console = Console()


def _print_article_list() -> None:
    index = load_index()
    if not index:
        console.print("[dim]Knowledge base is empty.[/dim]")
        return
    lines = []
    for meta in index.values():
        tags = ", ".join(meta["tags"]) if meta["tags"] else "—"
        lines.append(f"- **{meta['title']}** `{meta['slug']}` | tags: {tags}")
    console.print(Markdown("\n".join(lines)))


def main() -> None:
    console.print(
        Panel(
            "[bold cyan]Research Agent[/bold cyan]\n"
            "[dim]Your personal knowledge base assistant[/dim]\n\n"
            "Commands: [bold]/list[/bold] · [bold]/lint[/bold] · [bold]/clear[/bold] · [bold]/exit[/bold]",
            border_style="cyan",
        )
    )

    sync_papers()
    agent = Agent()

    while True:
        try:
            user_input = console.input("[bold green]you>[/bold green] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Goodbye.[/dim]")
            sys.exit(0)

        if not user_input:
            continue

        if user_input == "/exit":
            console.print("[dim]Goodbye.[/dim]")
            sys.exit(0)

        if user_input == "/list":
            _print_article_list()
            continue

        if user_input == "/lint":
            try:
                response = agent.chat("lint the wiki")
                console.print(Markdown(response))
            except Exception as exc:
                console.print(f"[red]Error:[/red] {exc}")
            continue

        if user_input == "/clear":
            agent.clear_history()
            console.print("[dim]Conversation history cleared.[/dim]")
            continue

        try:
            response = agent.chat(user_input)
            console.print(Markdown(response))
        except Exception as exc:
            console.print(f"[red]Error:[/red] {exc}")


if __name__ == "__main__":
    main()
