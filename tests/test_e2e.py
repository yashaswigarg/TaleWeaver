"""End-to-end integration test simulating a complete interactive TaleWeaver session."""

import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command

from taleweaver.graph.workflow import TaleWeaverGraph
from taleweaver.mcp_servers.lore_server import LorebookDB
from taleweaver.mcp_servers.publisher_server import PublisherEngine
from taleweaver.state import (
    ChapterDraft,
    CharacterProfile,
    EditorCritique,
    IllustrationPrompt,
    StoryChoice,
    StoryState,
    WorldLore,
)


def test_full_session_simulation():
    """Simulates:
    1. World Generation -> HitL interrupt -> User approves.
    2. Character Generation -> HitL interrupt -> User approves.
    3. Scribe Drafts Chapter 1 -> Editor Approves -> Illustrator Prompts -> Publisher saves.
    4. Player selects Choice 2 -> Graph registers decision.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        db_path = tmp_path / "test_lore.db"
        book_path = tmp_path / "StoryBook.md"
        chk_conn = sqlite3.connect(":memory:", check_same_thread=False)

        # Instantiate graph runner
        graph_runner = TaleWeaverGraph(checkpointer=SqliteSaver(chk_conn))

        # Mock agents to run fast offline verification without consuming API tokens
        mock_world = WorldLore(
            title="The Clockwork Labyrinth",
            genre="Steampunk Mystery",
            setting_description="A subterranean maze of brass cogs and steam ducts.",
            magic_or_tech_rules="Steam conduits power the locking mechanisms; gear oil prevents freezing.",
            primary_conflict="The Master Chronometer is counting down to total system purge.",
            tone="Atmospheric and suspenseful",
        )
        graph_runner.architect.generate_world = MagicMock(return_value=mock_world)

        mock_chars = [
            CharacterProfile(
                name="Thaddeus Gear",
                role="protagonist",
                archetype="Clockwork Engineer",
                traits=["Ingenious", "Methodical"],
                backstory="Designed the labyrinth's primary escapement before it locked him in.",
                inventory=["Brass Wrench", "Pressure Gauge"],
            ),
            CharacterProfile(
                name="Lyra Sparks",
                role="companion",
                archetype="Electrician",
                traits=["Quick-witted", "Reckless"],
                backstory="Former apprentice to the Guildmaster.",
                inventory=["Arc Torch", "Insulated Gloves"],
            ),
        ]
        graph_runner.character_designer.generate_roster = MagicMock(return_value=mock_chars)

        mock_draft = ChapterDraft(
            chapter_number=1,
            title="The Steam Valve Groans",
            content="Thaddeus tightened his brass respirator as steam hissed through the iron grate...",
            cliffhanger="A massive brass gear shifted overhead, blocking the only return passage.",
            choices=[
                StoryChoice(id=1, text="Force the auxiliary steam release valve", consequence_hint="Burns risk"),
                StoryChoice(id=2, text="Crawl through the lubricant drainage pipe", consequence_hint="Claustrophobic"),
                StoryChoice(id=3, text="Short-circuit the escapement wheel with the arc torch", consequence_hint="Unpredictable"),
            ],
        )
        graph_runner.scribe.draft_chapter = MagicMock(return_value=mock_draft)

        mock_critique = EditorCritique(
            approved=True,
            score=9,
            critique="Atmospheric description and great stakes.",
            required_fixes=[],
        )
        graph_runner.editor.review_chapter = MagicMock(return_value=mock_critique)

        mock_prompt = IllustrationPrompt(
            chapter_number=1,
            scene_title="The Escapement Jam",
            visual_prompt="Two explorers silhouetted against glowing amber steam inside colossal brass gearworks.",
            art_style="Steampunk concept art, volumetric steam lighting",
        )
        graph_runner.illustrator.create_illustration_prompt = MagicMock(return_value=mock_prompt)

        # Thread configuration
        config = {"configurable": {"thread_id": "simulated_game_001"}}

        # 1. Start game
        initial_state: StoryState = {
            "title": "The Clockwork Labyrinth",
            "genre": "Steampunk Mystery",
            "world_lore": None,
            "world_approved": False,
            "characters": [],
            "characters_approved": False,
            "character_feedback": None,
            "current_chapter_num": 1,
            "rolling_summary": "",
            "active_draft": None,
            "editor_critique": None,
            "revision_count": 0,
            "current_illustration": None,
            "published_chapters": [],
            "player_decision": None,
            "game_over": False,
            "status_message": "Init",
        }

        # First invoke halts at world_review interrupt
        graph_runner.app.invoke(initial_state, config=config)
        snap1 = graph_runner.app.get_state(config)
        assert snap1.tasks[0].interrupts[0].value["stage"] == "world_review"

        # 2. Player approves world premise
        graph_runner.app.invoke(Command(resume="approve"), config=config)
        snap2 = graph_runner.app.get_state(config)
        assert snap2.tasks[0].interrupts[0].value["stage"] == "character_review"
        assert len(snap2.tasks[0].interrupts[0].value["characters"]) == 2

        # 3. Player approves character roster
        graph_runner.app.invoke(Command(resume="approve"), config=config)
        snap3 = graph_runner.app.get_state(config)
        assert snap3.tasks[0].interrupts[0].value["stage"] == "story_choice"
        assert snap3.tasks[0].interrupts[0].value["title"] == "The Steam Valve Groans"
        assert len(snap3.tasks[0].interrupts[0].value["choices"]) == 3

        # 4. Player selects choice 2 ("Crawl through the lubricant drainage pipe")
        graph_runner.app.invoke(Command(resume="Crawl through the lubricant drainage pipe"), config=config)
        snap4 = graph_runner.app.get_state(config)

        # Graph seamlessly drafted and published Chapter 2, pausing at the Chapter 2 choice interrupt!
        assert len(snap4.values["published_chapters"]) == 2
        assert snap4.tasks[0].interrupts[0].value["stage"] == "story_choice"
        assert snap4.values["player_decision"] == "Crawl through the lubricant drainage pipe"
