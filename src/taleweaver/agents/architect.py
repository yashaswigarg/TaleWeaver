"""The World-Smith (Architect) Agent for TaleWeaver.

Builds deep, coherent world lore, rules, and primary conflict from the story title and genre,
and registers the canonical world rules in the Lorebook MCP server.
"""

from __future__ import annotations

from typing import Optional
from langchain_core.prompts import ChatPromptTemplate
from taleweaver.config import get_llm, limiter
from taleweaver.mcp_servers.lore_server import db as lore_db
from taleweaver.state import WorldLore

ARCHITECT_SYSTEM_PROMPT = """You are the World-Smith, master architect of fictional universes.
Your role is to construct an immersive, original, and deeply atmospheric world based on a Title and Genre.

Guidelines:
1. Ground the world with distinct physical or magical laws that create natural stakes.
2. Establish a gripping primary conflict that threatens or challenges the inhabitants.
3. Define an evocative tone that guides subsequent narrative prose.
4. Avoid generic tropes; introduce memorable, tactile setting details."""

ARCHITECT_USER_TEMPLATE = """Please build the foundational world lore for the following story:
Title: {title}
Genre: {genre}
User Guidance/Vision: {vision}"""


class ArchitectAgent:
    """Agent responsible for initial world-building and premise establishment."""

    def __init__(self, model_name: Optional[str] = None):
        self.llm = get_llm(temperature=0.7, model=model_name)
        self.structured_llm = self.llm.with_structured_output(WorldLore)
        self.prompt = ChatPromptTemplate.from_messages(
            [
                ("system", ARCHITECT_SYSTEM_PROMPT),
                ("user", ARCHITECT_USER_TEMPLATE),
            ]
        )

    def generate_world(self, title: str, genre: str, vision: str = "") -> WorldLore:
        """Generates WorldLore and persists it into the Lorebook database."""
        limiter.wait()
        chain = self.prompt | self.structured_llm
        world_lore: WorldLore = chain.invoke(
            {
                "title": title,
                "genre": genre,
                "vision": vision or "Create a captivating, high-stakes starting point.",
            }
        )

        # Register in Lorebook MCP database
        lore_db.store_world(
            setting=world_lore.setting_description,
            rules=world_lore.magic_or_tech_rules,
            conflict=world_lore.primary_conflict,
            tone=world_lore.tone,
        )

        return world_lore
