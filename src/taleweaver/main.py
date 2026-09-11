"""Main game loop and CLI driver for TaleWeaver."""

from __future__ import annotations

import sys
import uuid
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, IntPrompt, Prompt
from langgraph.types import Command

from taleweaver.config import DATA_DIR, STORYBOOK_MD_PATH, settings
from taleweaver.graph.workflow import create_game_graph
from taleweaver.state import StoryState
from taleweaver.ui.terminal import (
    console,
    display_chapter,
    display_characters_table,
    display_choices,
    display_world_card,
    print_banner,
)


def run_game(
    title: Optional[str] = None,
    genre: Optional[str] = None,
    storyline: Optional[str] = None,
    target_chapters: Optional[int] = None,
    thread_id: Optional[str] = None,
) -> None:
    """Executes an interactive TaleWeaver story creation game."""
    print_banner()

    # Verify API key
    if not settings.api_key:
        console.print(
            Panel(
                "[bold red]Error: No API key detected![/bold red]\n"
                "Please configure [bold yellow]GEMINI_API_KEY[/bold yellow] in your [bold cyan].env[/bold cyan] file.",
                border_style="red",
            )
        )
        return

    # Setup session thread
    session_id = thread_id or f"session_{uuid.uuid4().hex[:8]}"
    config = {"configurable": {"thread_id": session_id}}

    console.print(f"[dim]Game Session ID: [cyan]{session_id}[/cyan][/dim]\n")

    # Interactive prompts if not pre-supplied
    if not title:
        console.print("[bold yellow]📜 Let us forge your new chronicle:[/bold yellow]")
        title = Prompt.ask("Enter Story Title", default="Mona in Kyoto")
    if not genre:
        genre = Prompt.ask("Enter Genre(s)", default="Comedy / Slice-of-Life")
    if storyline is None:
        console.print("[dim italic]Tip: You can describe your specific plot ideas, desired locations, or narrative arc below.[/dim italic]")
        storyline = Prompt.ask(
            "Enter Storyline / Custom Premise (Optional)",
            default="Mona lives in a traditional countryside village with her house, school, fields, and market, later taking an exciting trip to Tokyo with her family.",
        )
    if target_chapters is None:
        target_chapters = IntPrompt.ask("Target Chapter Length (Pacing)", default=4)

    console.print(
        f"\n[bold green]Igniting Agents for:[/bold green] [bold white]{title}[/bold white] ([italic]{genre}[/italic])"
        f" | Target: {target_chapters} Chapters\n"
    )

    app = create_game_graph()

    # Initial state payload
    initial_payload: StoryState = {
        "title": title,
        "genre": genre,
        "storyline": storyline.strip() if storyline else "",
        "target_chapters": target_chapters,
        "world_lore": None,
        "world_approved": False,
        "characters": [],
        "characters_approved": False,
        "character_feedback": None,
        "current_chapter_num": 1,
        "rolling_summary": "",
        "active_draft": None,
        "editor_critique": None,
        "revision_count": 0,
        "current_illustration": None,
        "published_chapters": [],
        "player_decision": None,
        "game_over": False,
        "status_message": "Session initialized.",
    }

    # Start or resume graph execution
    with console.status("[bold cyan]The World-Smith is architecting the realm...[/bold cyan]", spinner="dots"):
        app.invoke(initial_payload, config=config)

    # Main HitL interaction loop
    while True:
        state_snapshot = app.get_state(config)

        # Check if the graph has finished
        if not state_snapshot.tasks:
            break

        interrupts = state_snapshot.tasks[0].interrupts
        if not interrupts:
            break

        interrupt_data = interrupts[0].value
        stage = interrupt_data.get("stage")

        # Stage 1: World Approval HitL
        if stage == "world_review":
            display_world_card(interrupt_data)
            console.print("\n[bold cyan]HitL Gateway 1:[/bold cyan] Review the world's setting, laws, and primary conflict.")
            approve = Confirm.ask("Do you approve this world premise?", default=True)
            if approve:
                resume_val = "approve"
            else:
                resume_val = Prompt.ask("Enter your tweaks or modifications for the world")

            with console.status("[bold cyan]Registering world in Lorebook MCP and summoning Character Designer...[/bold cyan]", spinner="dots"):
                app.invoke(Command(resume=resume_val), config=config)

        # Stage 2: Character Review & Modification HitL
        elif stage == "character_review":
            characters = interrupt_data.get("characters", [])
            display_characters_table(characters)
            console.print("\n[bold cyan]HitL Gateway 2:[/bold cyan] Inspect the generated character dossiers.")
            approve = Confirm.ask("Do you approve this character roster?", default=True)
            if approve:
                resume_val = "approve"
            else:
                resume_val = Prompt.ask("Enter desired character adjustments (e.g. 'Add Mona\\'s pet Shiba Inu', 'Change brother to a prankster')")

            with console.status("[bold cyan]Enrolling characters into Lorebook MCP and dispatching the Scribe...[/bold cyan]", spinner="dots"):
                app.invoke(Command(resume=resume_val), config=config)

        # Stage 3: Storybook Page & Player Choice HitL
        elif stage == "story_choice":
            display_chapter(interrupt_data)
            choices = interrupt_data.get("choices", [])
            is_finale = interrupt_data.get("is_finale", False)

            player_choice = display_choices(choices, is_finale=is_finale)

            if is_finale or player_choice.strip().lower() in ("quit", "exit", "end"):
                console.print("\n[yellow]Concluding story and compiling final master storybook...[/yellow]")
                with console.status("[bold green]Compiling StoryBook.md and StoryBook.html via Publisher MCP...[/bold green]", spinner="dots"):
                    app.invoke(Command(resume="quit"), config=config)
                break

            # Map single digit choice to text if numerical
            chosen_text = player_choice
            try:
                choice_idx = int(player_choice.strip())
                for c in choices:
                    if c.get("id") == choice_idx:
                        chosen_text = c.get("text", player_choice)
                        break
            except ValueError:
                pass

            with console.status("[bold cyan]The Scribe and Grand Arbiter are weaving your decision into the next Chapter...[/bold cyan]", spinner="dots"):
                app.invoke(Command(resume=chosen_text), config=config)

    # Game over / Completion Summary
    html_book_path = DATA_DIR / "StoryBook.html"
    console.print("\n" + "═" * 72)
    console.print(
        Panel(
            f"[bold green]✨ CHRONICLE COMPLETED & PUBLISHED! ✨[/bold green]\n\n"
            f"📖 **Markdown Book:** [bold cyan]{STORYBOOK_MD_PATH}[/bold cyan]\n"
            f"🌐 **Interactive HTML Book:** [bold magenta]{html_book_path}[/bold magenta]\n"
            f"🗃️ **Lorebook Database:** [bold yellow]{DATA_DIR / 'lorebook.db'}[/bold yellow]\n\n"
            "Open [bold underline]data/StoryBook.html[/bold underline] in your browser to view your beautifully styled, illustrated eBook!",
            border_style="bright_green",
            padding=(1, 2),
        )
    )


def main() -> None:
    """CLI entrypoint."""
    try:
        run_game()
    except KeyboardInterrupt:
        console.print("\n[yellow]TaleWeaver session paused. Your checkpoint state is safely preserved.[/yellow]")
        sys.exit(0)


if __name__ == "__main__":
    main()
