"""The Scribe Agent for TaleWeaver.

Drafts immersive story chapters, integrates previous player choices and rolling lore summaries,
and ends on high-stakes cliffhangers with 3 divergent options for the player.
"""

from __future__ import annotations

from typing import List, Optional
from langchain_core.prompts import ChatPromptTemplate
from taleweaver.config import get_llm, limiter
from taleweaver.mcp_servers.lore_server import db as lore_db
from taleweaver.state import ChapterDraft, CharacterProfile, WorldLore

SCRIBE_SYSTEM_PROMPT = """You are the Scribe, master of prose, suspense, and dynamic interactive storytelling.
Your mission is to write a thrilling, sensory-rich chapter for the storybook.

Rules for Storytelling:
1. Show, Don't Tell: Use physical textures, lighting, sounds, and visceral action.
2. Continuity: Faithfully respect character inventories, physical statuses, and previous choices.
3. Length: Write 300-500 words of evocative, high-caliber prose.
4. The Climax / Decision Point: Conclude the chapter at a pivotal fork in the road or sudden revelation.
5. Branching Choices: Provide exactly THREE divergent, intriguing choices for the player.
   - Choice 1: A bold, aggressive, or high-risk path.
   - Choice 2: A stealthy, analytical, or diplomatic path.
   - Choice 3: An unconventional, risky, or arcane path using an item/environment."""

SCRIBE_USER_TEMPLATE = """Story Context:
Title: {title} | Genre: {genre} | Tone: {tone}
Current Chapter Number: {chapter_num}

Canon World Lore:
{lore_context}

Active Characters & Status:
{character_context}

Story So Far (Rolling Summary):
{rolling_summary}

Player's Decision From Previous Chapter:
{previous_choice}

Required Fixes from Editor (if this is a revision pass):
{editor_fixes}

Write Chapter {chapter_num} with a compelling title, rich narrative, cliffhanger, and 3 choices."""


class ScribeAgent:
    """Agent responsible for writing and revising chapter prose."""

    def __init__(self, model_name: Optional[str] = None):
        self.llm = get_llm(temperature=0.75, model=model_name)
        self.structured_llm = self.llm.with_structured_output(ChapterDraft)
        self.prompt = ChatPromptTemplate.from_messages(
            [
                ("system", SCRIBE_SYSTEM_PROMPT),
                ("user", SCRIBE_USER_TEMPLATE),
            ]
        )

    def draft_chapter(
        self,
        chapter_num: int,
        world_lore: Optional[WorldLore],
        characters: List[CharacterProfile],
        rolling_summary: str,
        previous_choice: Optional[str] = None,
        editor_fixes: Optional[List[str]] = None,
    ) -> ChapterDraft:
        """Drafts or revises a chapter draft."""
        limiter.wait()

        # Query dynamic lore from Lorebook MCP
        lore_context = lore_db.query_lore("all")

        # Format characters
        char_lines = []
        for c in characters:
            char_lines.append(
                f"- {c.name} ({c.role}, {c.archetype}): Status='{c.status}', Inventory={c.inventory}"
            )
        character_context = "\n".join(char_lines) if char_lines else "None specified."

        fixes_text = "\n".join(f"- {f}" for f in editor_fixes) if editor_fixes else "None (Initial Draft)."
        prev_choice_text = previous_choice or "Opening of the adventure (Chapter 1 introduction)."

        chain = self.prompt | self.structured_llm
        draft: ChapterDraft = chain.invoke(
            {
                "title": world_lore.title if world_lore else "TaleWeaver Chronicles",
                "genre": world_lore.genre if world_lore else "Adventure",
                "tone": world_lore.tone if world_lore else "Atmospheric",
                "chapter_num": chapter_num,
                "lore_context": lore_context,
                "character_context": character_context,
                "rolling_summary": rolling_summary or "The journey begins here.",
                "previous_choice": prev_choice_text,
                "editor_fixes": fixes_text,
            }
        )

        return draft
