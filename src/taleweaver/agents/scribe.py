"""The Scribe Agent for TaleWeaver.

Drafts immersive story chapters, integrates player storyline guidance, character inventories,
and branching decision points towards an epic narrative climax.
"""

from __future__ import annotations

from typing import List, Optional
from langchain_core.prompts import ChatPromptTemplate
from taleweaver.config import get_llm, limiter
from taleweaver.mcp_servers.lore_server import db as lore_db
from taleweaver.state import ChapterDraft, CharacterProfile, WorldLore

SCRIBE_SYSTEM_PROMPT = """You are the Scribe, master of prose, sensory atmosphere, and dynamic interactive storytelling.
Your mission is to write a thrilling, sensory-rich chapter for the storybook.

Rules for Storytelling:
1. Show, Don't Tell: Use physical textures, lighting, sounds, dialogue, and visceral action.
2. Continuity: Faithfully respect character inventories, physical statuses, previous player choices, and user's overarching storyline.
3. Length: Write 300-500 words of evocative, high-caliber prose.
4. Pacing & Finale:
   - If this is NOT the final chapter, end at a gripping cliffhanger and provide THREE divergent choices for the player.
   - If this IS the final chapter, bring the core storyline and conflicts to a satisfying, memorable conclusion. Set is_finale=True and leave choices empty.
5. Inventory Events:
   - If characters gain, lose, or use significant items, record them in inventory_events so the Lorebook tracks them!"""

SCRIBE_USER_TEMPLATE = """Story Context:
Title: {title} | Genre: {genre} | Tone: {tone}
Chapter: {chapter_num} of {target_chapters} (Is Final Chapter: {is_final_chapter})

Desired Storyline / Context:
{storyline}

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

Write Chapter {chapter_num} with an evocative title, vivid narrative prose, cliffhanger, inventory events (if any), and branching choices (unless finale)."""


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
        storyline: Optional[str] = None,
        target_chapters: int = 5,
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
        is_final = chapter_num >= target_chapters

        storyline_text = (
            storyline
            or (world_lore.storyline if world_lore else "")
            or "A grand adventure unfolding with high stakes."
        )

        chain = self.prompt | self.structured_llm
        draft: ChapterDraft = chain.invoke(
            {
                "title": world_lore.title if world_lore else "TaleWeaver Chronicles",
                "genre": world_lore.genre if world_lore else "Adventure",
                "tone": world_lore.tone if world_lore else "Atmospheric",
                "chapter_num": chapter_num,
                "target_chapters": target_chapters,
                "is_final_chapter": "YES (Write Grand Finale)" if is_final else "NO",
                "storyline": storyline_text,
                "lore_context": lore_context,
                "character_context": character_context,
                "rolling_summary": rolling_summary or "The journey begins here.",
                "previous_choice": prev_choice_text,
                "editor_fixes": fixes_text,
            }
        )

        return draft
