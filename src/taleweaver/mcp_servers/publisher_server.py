"""Publisher MCP Server for TaleWeaver.

Manages saving individual chapter texts, generating visual prompt logs, and compiling
a beautifully styled, persistent Markdown storybook in the data/ directory.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp.server.mcpserver import MCPServer
from taleweaver.config import DATA_DIR, STORYBOOK_MD_PATH


class PublisherEngine:
    """Handles file-system operations for storybook publishing and chapter storage."""

    def __init__(self, output_dir: Optional[Path | str] = None, book_path: Optional[Path | str] = None):
        self.output_dir = Path(output_dir or DATA_DIR)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.chapters_dir = self.output_dir / "chapters"
        self.chapters_dir.mkdir(parents=True, exist_ok=True)
        self.book_path = Path(book_path or STORYBOOK_MD_PATH)

    def save_chapter(
        self,
        chapter_num: int,
        title: str,
        content: str,
        visual_prompt: str,
        chosen_action: Optional[str] = None,
    ) -> str:
        """Persist individual chapter markdown and metadata JSON."""
        chapter_data = {
            "chapter_num": chapter_num,
            "title": title,
            "content": content,
            "visual_prompt": visual_prompt,
            "chosen_action": chosen_action,
            "published_at": datetime.now().isoformat(),
        }

        json_file = self.chapters_dir / f"chapter_{chapter_num:02d}.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(chapter_data, f, indent=2, ensure_ascii=False)

        return f"Chapter {chapter_num} ('{title}') successfully saved to disk."

    def load_chapters(self) -> List[Dict[str, Any]]:
        """Load all saved chapters in numerical order."""
        chapters = []
        for file in sorted(self.chapters_dir.glob("chapter_*.json")):
            try:
                with open(file, "r", encoding="utf-8") as f:
                    chapters.append(json.load(f))
            except Exception:
                continue
        return sorted(chapters, key=lambda c: c.get("chapter_num", 0))

    def compile_book(self, story_title: str, genre: str, author_note: str = "") -> str:
        """Assembles all saved chapters into the master StoryBook.md."""
        chapters = self.load_chapters()
        if not chapters:
            return "No chapters found to compile."

        lines = [
            f"# {story_title.strip()}",
            f"\n**Genre:** {genre.strip()} | **Generated via:** TaleWeaver Agentic Engine",
            f"**Last Updated:** {datetime.now().strftime('%B %d, %Y - %H:%M')}",
            "\n---\n",
            "## Table of Contents",
        ]

        for ch in chapters:
            num = ch["chapter_num"]
            title = ch["title"]
            lines.append(f"- [Chapter {num}: {title}](#chapter-{num}-{title.lower().replace(' ', '-')})")

        lines.append("\n---\n")

        for ch in chapters:
            num = ch["chapter_num"]
            title = ch["title"]
            content = ch["content"]
            prompt = ch.get("visual_prompt", "")
            action = ch.get("chosen_action", "")

            lines.append(f"## Chapter {num}: {title}\n")

            if prompt:
                lines.append(
                    f"> 🎨 **Scene Illustration Concept:**\n> *\"{prompt.strip()}\"*\n"
                )

            lines.append(f"{content.strip()}\n")

            if action:
                lines.append(
                    f"> 🧭 **Player Choice:**\n> *\"{action.strip()}\"*\n"
                )

            lines.append("\n---\n")

        compiled_text = "\n".join(lines)
        with open(self.book_path, "w", encoding="utf-8") as f:
            f.write(compiled_text)

        return f"Storybook successfully compiled with {len(chapters)} chapters at: {self.book_path}"

    def read_book(self) -> str:
        if not self.book_path.exists():
            return "StoryBook.md has not been generated yet."
        with open(self.book_path, "r", encoding="utf-8") as f:
            return f.read()


# Default publisher instance
publisher = PublisherEngine()

# FastMCP Server definition
server = MCPServer("taleweaver_publisher_server")


@server.tool()
def publish_chapter(
    chapter_num: int,
    title: str,
    content: str,
    visual_prompt: str,
    chosen_action: str = "",
) -> str:
    """Save an approved chapter with illustration prompt and player choice to disk."""
    return publisher.save_chapter(
        chapter_num=chapter_num,
        title=title,
        content=content,
        visual_prompt=visual_prompt,
        chosen_action=chosen_action or None,
    )


@server.tool()
def compile_storybook(story_title: str, genre: str, author_note: str = "") -> str:
    """Compile all currently saved chapters into the unified StoryBook.md."""
    return publisher.compile_book(story_title=story_title, genre=genre, author_note=author_note)


@server.tool()
def read_storybook() -> str:
    """Read the full content of the compiled StoryBook.md."""
    return publisher.read_book()


if __name__ == "__main__":
    server.run(transport="stdio")
