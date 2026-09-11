"""The Visual Illustrator (Art Director) Agent for TaleWeaver.

Analyzes approved chapters to compose evocative, high-detail image generation prompts
capturing the climax and atmosphere of each scene.
"""

from __future__ import annotations

from typing import Optional
from langchain_core.prompts import ChatPromptTemplate
from taleweaver.config import get_llm, limiter
from taleweaver.state import ChapterDraft, IllustrationPrompt, WorldLore

ILLUSTRATOR_SYSTEM_PROMPT = """You are the Art Director and Master Illustrator.
Your job is to read an approved story chapter and design a stunning concept art visual prompt.

Prompt Crafting Rules:
1. Identify the single most cinematic, dramatic moment in the chapter.
2. Specify lighting (e.g. volumetric god-rays, rim light, bioluminescence, candle-lit chiaroscuro).
3. Specify camera composition (e.g. low-angle wide shot, extreme close-up, Dutch angle).
4. Describe key subjects, clothing textures, environment atmosphere, and color palette.
5. Provide a recommended artistic medium/style that reflects the genre."""

ILLUSTRATOR_USER_TEMPLATE = """Story Context:
Title: {title} | Genre: {genre} | Tone: {tone}
Chapter {chapter_num}: {chapter_title}

Chapter Narrative:
{content}

Key Scene / Cliffhanger:
{cliffhanger}

Design an iconic visual illustration prompt for this chapter."""


class IllustratorAgent:
    """Agent responsible for crafting scene visual prompts for the storybook."""

    def __init__(self, model_name: Optional[str] = None):
        self.llm = get_llm(temperature=0.7, model=model_name)
        self.structured_llm = self.llm.with_structured_output(IllustrationPrompt)
        self.prompt = ChatPromptTemplate.from_messages(
            [
                ("system", ILLUSTRATOR_SYSTEM_PROMPT),
                ("user", ILLUSTRATOR_USER_TEMPLATE),
            ]
        )

    def create_illustration_prompt(
        self, world_lore: Optional[WorldLore], draft: ChapterDraft
    ) -> IllustrationPrompt:
        """Generates an art concept prompt for the chapter."""
        limiter.wait()
        chain = self.prompt | self.structured_llm
        illustration: IllustrationPrompt = chain.invoke(
            {
                "title": world_lore.title if world_lore else "TaleWeaver",
                "genre": world_lore.genre if world_lore else "Story",
                "tone": world_lore.tone if world_lore else "Atmospheric",
                "chapter_num": draft.chapter_number,
                "chapter_title": draft.title,
                "content": draft.content,
                "cliffhanger": draft.cliffhanger,
            }
        )
        return illustration
