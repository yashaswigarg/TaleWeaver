"""The Grand Arbiter (Editor) Agent for TaleWeaver.

Evaluates narrative drafts for tone fidelity, pacing, continuity with character inventory,
and quality of branching decision points.
"""

from __future__ import annotations

from typing import Optional
from langchain_core.prompts import ChatPromptTemplate
from taleweaver.config import get_llm, limiter
from taleweaver.state import ChapterDraft, EditorCritique, WorldLore

EDITOR_SYSTEM_PROMPT = """You are the Grand Arbiter, an exacting literary editor, game designer, and LLM-as-a-Judge evaluator.
Your duty is to critically review the Scribe's draft chapter across quantitative dimensions.

Evaluation Rubric (Score each from 1.0 to 10.0):
1. Pacing Score: Is there sufficient sensory detail and dynamic momentum without dragging?
2. Lore Consistency Score: Are character voices, inventory state, and world rules strictly adhered to?
3. Character Voice Score: Are dialogues distinct, expressive, and aligned with character archetypes?
4. Composite Score: Weighted average of the three dimensions.

Scoring & Verdict:
- Overall Score: Integer 1-10.
- If composite_score >= 7.0, set approved = True.
- If composite_score < 7.0, set approved = False, and provide 1-3 concrete, concise required_fixes.
Be constructive, rigorous, direct, and concise."""

EDITOR_USER_TEMPLATE = """Story Context:
Title: {title}
Genre: {genre}
Expected Tone: {tone}

Draft to Review (Chapter {chapter_num}: {chapter_title}):
Content:
{content}

Cliffhanger:
{cliffhanger}

Proposed Choices:
{choices}

Please provide your critique, score, and decision."""


class EditorAgent:
    """Agent responsible for critique, consistency checking, and quality gating."""

    def __init__(self, model_name: Optional[str] = None):
        self.llm = get_llm(temperature=0.3, model=model_name)
        self.structured_llm = self.llm.with_structured_output(EditorCritique)
        self.prompt = ChatPromptTemplate.from_messages(
            [
                ("system", EDITOR_SYSTEM_PROMPT),
                ("user", EDITOR_USER_TEMPLATE),
            ]
        )

    def review_chapter(self, world_lore: Optional[WorldLore], draft: ChapterDraft) -> EditorCritique:
        """Reviews the draft and emits structured evaluation with fixes if rejected."""
        limiter.wait()

        choices_str = "\n".join(
            f"{c.id}. {c.text} (Hint: {c.consequence_hint or 'None'})" for c in draft.choices
        )

        chain = self.prompt | self.structured_llm
        critique: EditorCritique = chain.invoke(
            {
                "title": world_lore.title if world_lore else "TaleWeaver",
                "genre": world_lore.genre if world_lore else "Fiction",
                "tone": world_lore.tone if world_lore else "Engaging",
                "chapter_num": draft.chapter_number,
                "chapter_title": draft.title,
                "content": draft.content,
                "cliffhanger": draft.cliffhanger,
                "choices": choices_str,
            }
        )

        return critique
