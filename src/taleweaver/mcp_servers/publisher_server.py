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

        # Also generate standalone styled HTML eBook
        html_path = self.output_dir / "StoryBook.html"
        self._generate_html_book(story_title, genre, chapters, html_path)

        return f"Storybook successfully compiled with {len(chapters)} chapters at: {self.book_path} (HTML: {html_path})"

    def _generate_html_book(self, story_title: str, genre: str, chapters: List[Dict[str, Any]], html_path: Path) -> None:
        """Generates a responsive, publication-quality HTML edition of the StoryBook."""
        chapter_articles = []
        for ch in chapters:
            num = ch["chapter_num"]
            title = ch["title"]
            content_paragraphs = "".join(f"<p>{p.strip()}</p>" for p in ch["content"].split("\n\n") if p.strip())
            prompt_box = f"""
            <div class="art-card">
                <span class="art-badge">🎨 Art Director Concept</span>
                <p class="art-prompt">"{ch.get('visual_prompt', '')}"</p>
            </div>
            """ if ch.get("visual_prompt") else ""

            choice_box = f"""
            <div class="choice-card">
                <span class="choice-badge">🧭 Chosen Path</span>
                <p class="choice-text">"{ch.get('chosen_action', '')}"</p>
            </div>
            """ if ch.get("chosen_action") else ""

            chapter_articles.append(f"""
            <article class="chapter" id="chapter-{num}">
                <header class="chapter-header">
                    <span class="chapter-number">Chapter {num}</span>
                    <h2 class="chapter-title">{title}</h2>
                </header>
                {prompt_box}
                <div class="chapter-body">
                    {content_paragraphs}
                </div>
                {choice_box}
            </article>
            """)

        toc_items = "".join(
            f'<li><a href="#chapter-{c["chapter_num"]}"><span class="toc-num">{c["chapter_num"]:02d}.</span> {c["title"]}</a></li>'
            for c in chapters
        )

        html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{story_title} — TaleWeaver Chronicle</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@600;700;900&family=Crimson+Pro:ital,wght@0,400;0,600;1,400&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-color: #0f1117;
            --surface-color: #171b26;
            --card-bg: #1e2333;
            --border-color: #2b3248;
            --text-primary: #e6e8f0;
            --text-secondary: #9aa2bc;
            --accent-gold: #e5b95f;
            --accent-cyan: #4ecdc4;
            --accent-crimson: #ff6b6b;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            background-color: var(--bg-color);
            color: var(--text-primary);
            font-family: 'Crimson Pro', Georgia, serif;
            font-size: 1.25rem;
            line-height: 1.8;
            padding: 2rem 1rem;
        }}
        .container {{
            max-width: 820px;
            margin: 0 auto;
        }}
        header.book-header {{
            text-align: center;
            padding: 4rem 1rem 3rem;
            border-bottom: 2px solid var(--border-color);
            margin-bottom: 3rem;
        }}
        .book-title {{
            font-family: 'Cinzel', serif;
            font-size: 3rem;
            font-weight: 900;
            color: var(--accent-gold);
            letter-spacing: 2px;
            margin-bottom: 0.75rem;
        }}
        .book-meta {{
            font-family: 'Inter', sans-serif;
            font-size: 0.95rem;
            color: var(--text-secondary);
            letter-spacing: 1px;
            text-transform: uppercase;
        }}
        .toc-card {{
            background: var(--surface-color);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 2rem;
            margin-bottom: 3rem;
            box-shadow: 0 8px 24px rgba(0,0,0,0.3);
        }}
        .toc-card h3 {{
            font-family: 'Cinzel', serif;
            color: var(--accent-gold);
            margin-bottom: 1rem;
            font-size: 1.3rem;
        }}
        .toc-card ul {{
            list-style: none;
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 0.75rem;
        }}
        .toc-card a {{
            color: var(--accent-cyan);
            text-decoration: none;
            font-family: 'Inter', sans-serif;
            font-size: 1rem;
            transition: color 0.2s;
        }}
        .toc-card a:hover {{ color: var(--accent-gold); }}
        .toc-num {{ color: var(--text-secondary); margin-right: 0.4rem; font-weight: bold; }}
        article.chapter {{
            background: var(--surface-color);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 3rem 2.5rem;
            margin-bottom: 3rem;
            box-shadow: 0 10px 30px rgba(0,0,0,0.4);
        }}
        .chapter-header {{
            text-align: center;
            margin-bottom: 2rem;
            padding-bottom: 1.5rem;
            border-bottom: 1px solid var(--border-color);
        }}
        .chapter-number {{
            font-family: 'Inter', sans-serif;
            font-size: 0.85rem;
            font-weight: 700;
            color: var(--accent-gold);
            text-transform: uppercase;
            letter-spacing: 2px;
            display: block;
            margin-bottom: 0.5rem;
        }}
        .chapter-title {{
            font-family: 'Cinzel', serif;
            font-size: 2.2rem;
            color: var(--text-primary);
        }}
        .art-card {{
            background: rgba(78, 205, 196, 0.08);
            border-left: 4px solid var(--accent-cyan);
            border-radius: 0 8px 8px 0;
            padding: 1rem 1.25rem;
            margin-bottom: 2rem;
        }}
        .art-badge {{
            font-family: 'Inter', sans-serif;
            font-size: 0.75rem;
            font-weight: 700;
            color: var(--accent-cyan);
            text-transform: uppercase;
            letter-spacing: 1px;
            display: block;
            margin-bottom: 0.4rem;
        }}
        .art-prompt {{
            font-style: italic;
            font-size: 1.05rem;
            color: var(--text-secondary);
        }}
        .chapter-body p {{
            margin-bottom: 1.5rem;
            text-indent: 1.5rem;
        }}
        .chapter-body p:first-of-type {{
            text-indent: 0;
        }}
        .chapter-body p:first-of-type::first-letter {{
            font-family: 'Cinzel', serif;
            font-size: 3.5rem;
            float: left;
            line-height: 0.8;
            margin-right: 0.75rem;
            color: var(--accent-gold);
        }}
        .choice-card {{
            background: rgba(229, 185, 95, 0.08);
            border-left: 4px solid var(--accent-gold);
            border-radius: 0 8px 8px 0;
            padding: 1rem 1.25rem;
            margin-top: 2rem;
        }}
        .choice-badge {{
            font-family: 'Inter', sans-serif;
            font-size: 0.75rem;
            font-weight: 700;
            color: var(--accent-gold);
            text-transform: uppercase;
            letter-spacing: 1px;
            display: block;
            margin-bottom: 0.4rem;
        }}
        .choice-text {{
            font-family: 'Inter', sans-serif;
            font-size: 1rem;
            color: var(--text-primary);
        }}
        footer {{
            text-align: center;
            padding: 3rem 1rem;
            color: var(--text-secondary);
            font-family: 'Inter', sans-serif;
            font-size: 0.9rem;
            border-top: 1px solid var(--border-color);
        }}
    </style>
</head>
<body>
    <div class="container">
        <header class="book-header">
            <h1 class="book-title">{story_title}</h1>
            <p class="book-meta">Genre: {genre} &bull; Chronicled via TaleWeaver</p>
        </header>

        <section class="toc-card">
            <h3>Table of Contents</h3>
            <ul>{toc_items}</ul>
        </section>

        <main>
            {"".join(chapter_articles)}
        </main>

        <footer>
            <p>Chronicle synthesized by TaleWeaver Agentic Engine &bull; Stored locally with Model Context Protocol</p>
        </footer>
    </div>
</body>
</html>"""
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_template)

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
