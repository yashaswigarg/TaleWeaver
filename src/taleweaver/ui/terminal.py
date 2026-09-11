"""Rich terminal UI formatting components for TaleWeaver."""

from __future__ import annotations

from typing import Any, Dict, List
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text

console = Console()


def print_banner() -> None:
    """Displays the TaleWeaver title banner."""
    banner_text = Text()
    banner_text.append("╔═══════════════════════════════════════════════════════════════════════╗\n", style="bold cyan")
    banner_text.append("║                           TALEWEAVER                                  ║\n", style="bold magenta")
    banner_text.append("║           Interactive Multi-Agent Story Forge & Book Engine           ║\n", style="bold yellow")
    banner_text.append("║            Powered by LangGraph, FastMCP & Local SQLite Memory        ║\n", style="italic blue")
    banner_text.append("╚═══════════════════════════════════════════════════════════════════════╝", style="bold cyan")
    console.print(banner_text)


def display_world_card(data: Dict[str, Any]) -> None:
    """Renders the generated world lore in a formatted Rich panel."""
    storyline = data.get("storyline", "")
    storyline_section = f"\n### 🎯 Player's Guiding Storyline\n*{storyline}*\n" if storyline else ""

    content = f"""# {data.get('title', 'Unknown Title')}
**Genre:** {data.get('genre', 'N/A')} | **Tone:** {data.get('tone', 'N/A')}
{storyline_section}
### 🌍 Setting
{data.get('setting', '')}

### ⚡ World Rules & Physics/Magic/Society
{data.get('rules', '')}

### ⚔️ Looming Stakes & Core Conflict
{data.get('conflict', '')}
"""
    console.print(
        Panel(
            Markdown(content),
            title="[bold yellow]✨ World Architecture Dossier[/bold yellow]",
            border_style="cyan",
            padding=(1, 2),
        )
    )


def display_characters_table(characters: List[Dict[str, Any]]) -> None:
    """Renders character dossiers in a formatted table."""
    table = Table(
        title="👥 Active Dramatis Personae (Character Roster)",
        show_header=True,
        header_style="bold magenta",
        border_style="bright_blue",
    )
    table.add_column("Role", style="bold cyan", width=14)
    table.add_column("Name & Archetype", style="bold white", width=24)
    table.add_column("Traits", style="italic yellow", width=22)
    table.add_column("Signature Inventory", style="green", width=24)
    table.add_column("Backstory Snippet", style="white")

    for c in characters:
        role = c.get("role", "").upper()
        name_arch = f"{c.get('name', '')}\n[dim]({c.get('archetype', '')})[/dim]"
        traits = ", ".join(c.get("traits", []))
        inv = ", ".join(c.get("inventory", [])) or "None"
        backstory = c.get("backstory", "")
        if len(backstory) > 120:
            backstory = backstory[:117] + "..."
        table.add_row(role, name_arch, traits, inv, backstory)

    console.print(table)


def display_chapter(data: Dict[str, Any]) -> None:
    """Renders a formatted storybook page for an approved chapter."""
    ch_num = data.get("chapter_number", 1)
    title = data.get("title", "Untitled Chapter")
    content = data.get("content", "")
    cliffhanger = data.get("cliffhanger", "")
    prompt = data.get("visual_prompt", "")
    is_finale = data.get("is_finale", False)

    header_tag = "🎉 GRAND FINALE" if is_finale else f"Chapter {ch_num}"
    footer_tag = "**🏆 Resolution:**" if is_finale else "**⚡ Crisis / Cliffhanger:**"

    page_md = f"""# {header_tag}: {title}

{content}

---
{footer_tag} *{cliffhanger}*
"""
    console.print(
        Panel(
            Markdown(page_md),
            title=f"[bold green]📖 StoryBook Page — {header_tag}[/bold green]",
            border_style="gold1" if is_finale else "green",
            padding=(1, 2),
        )
    )

    if prompt:
        console.print(
            Panel(
                f"[italic cyan]\"{prompt}\"[/italic cyan]",
                title="[bold magenta]🎨 Art Director's Scene Visual Prompt[/bold magenta]",
                border_style="magenta",
                padding=(0, 2),
            )
        )


def display_choices(choices: List[Dict[str, Any]], is_finale: bool = False) -> str:
    """Presents branching story choices and returns player selection."""
    if is_finale or not choices:
        console.print("\n[bold gold1]🎉 The chronicle has reached its climactic resolution![/bold gold1]")
        Prompt.ask("[bold green]Press Enter to finalize and compile your StoryBook[/bold green]", default="")
        return "quit"

    console.print("\n[bold yellow]🧭 Choose the Protagonist's Next Course of Action:[/bold yellow]")
    for c in choices:
        c_id = c.get("id", 1)
        text = c.get("text", "")
        hint = c.get("consequence_hint")
        hint_str = f" [dim yellow](Hint: {hint})[/dim yellow]" if hint else ""
        console.print(f"  [bold cyan][{c_id}][/bold cyan] {text}{hint_str}")

    console.print("  [dim][Type 1, 2, 3, a custom action, or 'quit' to finalize book][/dim]")
    choice = Prompt.ask("\n[bold green]Your Command[/bold green]", default="1")
    return choice
