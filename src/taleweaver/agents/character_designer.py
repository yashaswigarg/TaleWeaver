"""The Character Designer Agent for TaleWeaver.

Generates evocative character rosters (Protagonist, Companion, Antagonist) tailored
to the World Lore, and updates profiles based on player feedback before Chapter 1 begins.
"""

from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from taleweaver.config import get_llm, limiter
from taleweaver.mcp_servers.lore_server import db as lore_db
from taleweaver.state import CharacterProfile, WorldLore


class CharacterRoster(BaseModel):
    """Collection of core dramatic characters for the story."""

    characters: List[CharacterProfile] = Field(
        description="List of 3-4 distinct characters (Protagonist, Companion, Antagonist, and Mentor)"
    )


CHARACTER_SYSTEM_PROMPT = """You are the Lead Character Designer and Dramatist.
Your goal is to forge memorable, multi-layered characters with clear motivations, distinct voices,
and meaningful inventory items that fit the world's setting and rules.

Roster Structure:
1. Exactly ONE Protagonist (the player character)
2. At least ONE Companion or Ally (complementary skillset)
3. Exactly ONE Antagonist or Looming Rival
4. Optionally ONE Mentor or Enigmatic Neutral Figure

Make their backstories directly tie into the world's primary conflict and setting rules."""

CHARACTER_USER_TEMPLATE = """World Lore Context:
Title: {title}
Genre: {genre}
Setting: {setting}
Rules: {rules}
Primary Conflict: {conflict}
Tone: {tone}

Player Feedback / Requests (if any):
{feedback}

Please create/update the character roster adhering to the instructions."""


class CharacterDesignerAgent:
    """Agent responsible for crafting and refining character dossiers."""

    def __init__(self, model_name: Optional[str] = None):
        self.llm = get_llm(temperature=0.7, model=model_name)
        self.structured_llm = self.llm.with_structured_output(CharacterRoster)
        self.prompt = ChatPromptTemplate.from_messages(
            [
                ("system", CHARACTER_SYSTEM_PROMPT),
                ("user", CHARACTER_USER_TEMPLATE),
            ]
        )

    def generate_roster(
        self,
        world_lore: WorldLore,
        player_feedback: Optional[str] = None,
    ) -> List[CharacterProfile]:
        """Generates or updates the character roster and syncs with Lorebook."""
        limiter.wait()
        chain = self.prompt | self.structured_llm
        result: CharacterRoster = chain.invoke(
            {
                "title": world_lore.title,
                "genre": world_lore.genre,
                "setting": world_lore.setting_description,
                "rules": world_lore.magic_or_tech_rules,
                "conflict": world_lore.primary_conflict,
                "tone": world_lore.tone,
                "feedback": player_feedback or "Generate a fresh, balanced roster.",
            }
        )

        # Sync characters into Lorebook MCP database
        for char in result.characters:
            lore_db.upsert_character(
                name=char.name,
                role=char.role,
                archetype=char.archetype,
                traits=char.traits,
                backstory=char.backstory,
                inventory=char.inventory,
                status=char.status,
            )

        return result.characters
