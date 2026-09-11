"""LangGraph orchestration workflow for TaleWeaver's multi-agent interactive engine."""

from __future__ import annotations

import sqlite3
from typing import Any, Dict, Literal, Optional

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from taleweaver.agents.architect import ArchitectAgent
from taleweaver.agents.character_designer import CharacterDesignerAgent
from taleweaver.agents.editor import EditorAgent
from taleweaver.agents.illustrator import IllustratorAgent
from taleweaver.agents.scribe import ScribeAgent
from taleweaver.config import CHECKPOINTS_DB_PATH, settings
from taleweaver.mcp_servers.lore_server import db as lore_db
from taleweaver.mcp_servers.publisher_server import publisher as publisher_engine
from taleweaver.state import ChapterRecord, EditorCritique, StoryState, WorldLore


class TaleWeaverGraph:
    """Coordinates agent execution, state transitions, loops, and human checkpoints."""

    def __init__(self, checkpointer: Optional[SqliteSaver] = None, model_name: Optional[str] = None):
        self.checkpointer = checkpointer
        self.architect = ArchitectAgent(model_name=model_name)
        self.character_designer = CharacterDesignerAgent(model_name=model_name)
        self.scribe = ScribeAgent(model_name=model_name)
        self.editor = EditorAgent(model_name=model_name)
        self.illustrator = IllustratorAgent(model_name=model_name)
        self.app = self._build_graph()

    def _node_world_smith(self, state: StoryState) -> Dict[str, Any]:
        """Generates or updates the world lore, then pauses for human review."""
        world_lore = state.get("world_lore")
        storyline = state.get("storyline") or ""

        if not world_lore:
            world_lore = self.architect.generate_world(
                title=state["title"],
                genre=state["genre"],
                storyline=storyline,
                vision=state.get("character_feedback") or "",
            )

        # HitL Gateway 1: World & Storyline Approval
        if not state.get("world_approved"):
            human_feedback = interrupt(
                {
                    "stage": "world_review",
                    "title": world_lore.title,
                    "genre": world_lore.genre,
                    "storyline": world_lore.storyline or storyline,
                    "setting": world_lore.setting_description,
                    "rules": world_lore.magic_or_tech_rules,
                    "conflict": world_lore.primary_conflict,
                    "tone": world_lore.tone,
                }
            )
            # If user provided guidance, adjust setting
            if human_feedback and isinstance(human_feedback, str) and human_feedback.strip().lower() not in ("approve", "ok", "yes", "continue", ""):
                world_lore.setting_description += f" [Player Note: {human_feedback}]"
                lore_db.store_world(
                    setting=world_lore.setting_description,
                    rules=world_lore.magic_or_tech_rules,
                    conflict=world_lore.primary_conflict,
                    tone=world_lore.tone,
                    storyline=world_lore.storyline or storyline,
                )

        return {"world_lore": world_lore, "world_approved": True, "status_message": "World approved."}

    def _node_character_designer(self, state: StoryState) -> Dict[str, Any]:
        """Generates the character roster, then pauses for human review."""
        world_lore = state["world_lore"]
        characters = state.get("characters") or []
        feedback = state.get("character_feedback")

        if not characters:
            characters = self.character_designer.generate_roster(world_lore=world_lore, player_feedback=feedback)

        # HitL Gateway 2: Character Review & Tweak
        if not state.get("characters_approved"):
            human_input = interrupt(
                {
                    "stage": "character_review",
                    "characters": [c.model_dump() for c in characters],
                }
            )
            if human_input and isinstance(human_input, str) and human_input.strip().lower() not in ("approve", "ok", "yes", "continue", ""):
                # Re-generate or tune roster with user notes
                characters = self.character_designer.generate_roster(
                    world_lore=world_lore,
                    player_feedback=human_input,
                )

        return {
            "characters": characters,
            "characters_approved": True,
            "status_message": "Characters approved and enrolled in Lorebook.",
        }

    def _node_scribe_draft(self, state: StoryState) -> Dict[str, Any]:
        """Writes a new chapter or executes a revision pass based on editor critique."""
        chapter_num = state.get("current_chapter_num", 1)
        critique = state.get("editor_critique")
        revision_count = state.get("revision_count", 0)
        target_chapters = state.get("target_chapters", 5)

        editor_fixes = None
        if critique and not critique.approved and revision_count > 0:
            editor_fixes = critique.required_fixes

        draft = self.scribe.draft_chapter(
            chapter_num=chapter_num,
            world_lore=state.get("world_lore"),
            characters=state.get("characters", []),
            rolling_summary=state.get("rolling_summary", ""),
            storyline=state.get("storyline"),
            target_chapters=target_chapters,
            previous_choice=state.get("player_decision"),
            editor_fixes=editor_fixes,
        )

        return {
            "active_draft": draft,
            "revision_count": revision_count,
            "status_message": f"Chapter {chapter_num} drafted by Scribe.",
        }

    def _node_editor_review(self, state: StoryState) -> Dict[str, Any]:
        """Evaluates chapter quality, pacing, and choice divergence."""
        draft = state["active_draft"]
        world_lore = state.get("world_lore")
        critique = self.editor.review_chapter(world_lore=world_lore, draft=draft)
        new_revision_count = state.get("revision_count", 0) + 1

        return {
            "editor_critique": critique,
            "revision_count": new_revision_count,
            "status_message": f"Editor review: {'Approved' if critique.approved else 'Revision requested'}.",
        }

    def _route_after_editor(self, state: StoryState) -> Literal["illustrator", "scribe_draft"]:
        """Enforces strictly capped revision loops to safeguard free API quota."""
        critique: Optional[EditorCritique] = state.get("editor_critique")
        revision_count = state.get("revision_count", 0)

        # If editor approves OR revision limit reached, proceed to illustrate
        if (critique and critique.approved) or revision_count >= settings.max_revisions:
            return "illustrator"
        return "scribe_draft"

    def _node_illustrator(self, state: StoryState) -> Dict[str, Any]:
        """Generates evocative visual prompt for the chapter."""
        draft = state["active_draft"]
        world_lore = state.get("world_lore")
        illustration = self.illustrator.create_illustration_prompt(world_lore=world_lore, draft=draft)
        return {
            "current_illustration": illustration,
            "status_message": "Visual prompt synthesized by Art Director.",
        }

    def _node_publisher(self, state: StoryState) -> Dict[str, Any]:
        """Publishes chapter to disk, logs milestone, updates rolling summary, and applies inventory changes."""
        draft = state["active_draft"]
        illustration = state["current_illustration"]
        chapter_num = draft.chapter_number
        action = state.get("player_decision") or "Journey began"

        # 1. MCP Publisher tool
        publisher_engine.save_chapter(
            chapter_num=chapter_num,
            title=draft.title,
            content=draft.content,
            visual_prompt=illustration.visual_prompt if illustration else "",
            chosen_action=action,
        )

        # 2. MCP Lorebook: Record chapter milestone
        milestone = f"Chapter {chapter_num} completed: {draft.title}. Outcome: {draft.cliffhanger}"
        lore_db.record_milestone(chapter_num=chapter_num, event_summary=milestone)

        # 3. MCP Lorebook: Apply inventory changes from narrative
        for inv_event in getattr(draft, "inventory_events", []):
            lore_db.modify_inventory(
                character_name=inv_event.character_name,
                item=inv_event.item,
                action=inv_event.action,
            )

        # 4. Compact rolling summary
        current_summary = state.get("rolling_summary", "")
        updated_summary = f"{current_summary}\n- Ch {chapter_num} ({draft.title}): {draft.cliffhanger}".strip()

        published_record = ChapterRecord(
            chapter_number=chapter_num,
            title=draft.title,
            content=draft.content,
            visual_prompt=illustration.visual_prompt if illustration else "",
            chosen_action=action,
            is_finale=getattr(draft, "is_finale", False),
        )

        published_list = list(state.get("published_chapters") or [])
        published_list.append(published_record)

        return {
            "rolling_summary": updated_summary,
            "published_chapters": published_list,
            "revision_count": 0,  # Reset revision counter for next chapter
            "status_message": f"Chapter {chapter_num} published.",
        }

    def _node_player_decision(self, state: StoryState) -> Dict[str, Any]:
        """HitL Gateway 3: Presents chapter and pauses for player's branching choice or finale acknowledgment."""
        draft = state["active_draft"]
        illustration = state.get("current_illustration")
        is_finale = getattr(draft, "is_finale", False) or (draft.chapter_number >= state.get("target_chapters", 5))

        # Interrupt for player action
        choice_input = interrupt(
            {
                "stage": "story_choice",
                "chapter_number": draft.chapter_number,
                "title": draft.title,
                "content": draft.content,
                "cliffhanger": draft.cliffhanger,
                "visual_prompt": illustration.visual_prompt if illustration else "",
                "is_finale": is_finale,
                "choices": [c.model_dump() for c in draft.choices],
            }
        )

        decision_str = str(choice_input) if choice_input is not None else "1"
        is_game_over = False
        if is_finale or decision_str.strip().lower() in ("exit", "quit", "end"):
            is_game_over = True

        return {
            "player_decision": decision_str,
            "current_chapter_num": draft.chapter_number + 1,
            "game_over": is_game_over,
            "status_message": f"Choice '{decision_str}' registered.",
        }

    def _route_after_decision(self, state: StoryState) -> Literal["compile_book", "scribe_draft"]:
        if state.get("game_over"):
            return "compile_book"
        return "scribe_draft"

    def _node_compile_book(self, state: StoryState) -> Dict[str, Any]:
        """Compiles master StoryBook.md and StoryBook.html using Publisher MCP."""
        res = publisher_engine.compile_book(
            story_title=state["title"],
            genre=state["genre"],
        )
        return {"status_message": res}

    def _build_graph(self):
        """Constructs and compiles the StateGraph workflow."""
        builder = StateGraph(StoryState)

        # Add all nodes
        builder.add_node("world_smith", self._node_world_smith)
        builder.add_node("character_designer", self._node_character_designer)
        builder.add_node("scribe_draft", self._node_scribe_draft)
        builder.add_node("editor_review", self._node_editor_review)
        builder.add_node("illustrator", self._node_illustrator)
        builder.add_node("publisher", self._node_publisher)
        builder.add_node("player_decision", self._node_player_decision)
        builder.add_node("compile_book", self._node_compile_book)

        # Connect linear and cyclical edges
        builder.add_edge(START, "world_smith")
        builder.add_edge("world_smith", "character_designer")
        builder.add_edge("character_designer", "scribe_draft")
        builder.add_edge("scribe_draft", "editor_review")

        # Cyclical feedback edge (Editor <-> Scribe)
        builder.add_conditional_edges(
            "editor_review",
            self._route_after_editor,
            {
                "illustrator": "illustrator",
                "scribe_draft": "scribe_draft",
            },
        )

        builder.add_edge("illustrator", "publisher")
        builder.add_edge("publisher", "player_decision")

        # Gameplay branching loop
        builder.add_conditional_edges(
            "player_decision",
            self._route_after_decision,
            {
                "scribe_draft": "scribe_draft",
                "compile_book": "compile_book",
            },
        )

        builder.add_edge("compile_book", END)

        return builder.compile(checkpointer=self.checkpointer)


def create_game_graph(db_path: Optional[str] = None) -> Any:
    """Factory function to instantiate the game graph with persistent SQLite checkpoints."""
    conn = sqlite3.connect(db_path or str(CHECKPOINTS_DB_PATH), check_same_thread=False)
    checkpointer = SqliteSaver(conn)
    return TaleWeaverGraph(checkpointer=checkpointer).app
