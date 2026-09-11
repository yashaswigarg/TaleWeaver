"""End-to-end integration test simulating interactive TaleWeaver sessions."""

import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command

from taleweaver.graph.workflow import TaleWeaverGraph
from taleweaver.state import (
    ChapterDraft,
    CharacterProfile,
    EditorCritique,
    IllustrationPrompt,
    InventoryEvent,
    StoryChoice,
    StoryState,
    WorldLore,
)


def test_full_session_simulation():
    """Simulates:
    1. World Generation -> HitL interrupt -> User approves.
    2. Character Generation -> HitL interrupt -> User approves.
    3. Scribe Drafts Chapter 1 -> Editor Approves -> Illustrator Prompts -> Publisher saves.
    4. Player selects Choice 2 -> Graph advances to Chapter 2 choice.
    """
    chk_conn = sqlite3.connect(":memory:", check_same_thread=False)
    graph_runner = TaleWeaverGraph(checkpointer=SqliteSaver(chk_conn))

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

    config = {"configurable": {"thread_id": "simulated_game_001"}}

    initial_state: StoryState = {
        "title": "The Clockwork Labyrinth",
        "genre": "Steampunk Mystery",
        "storyline": "Escape before the chronometer resets the maze.",
        "target_chapters": 3,
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

    # Graph drafted Chapter 2 and halted at Chapter 2 choice interrupt
    assert len(snap4.values["published_chapters"]) == 2
    assert snap4.tasks[0].interrupts[0].value["stage"] == "story_choice"
    assert snap4.values["player_decision"] == "Crawl through the lubricant drainage pipe"


def test_mona_in_kyoto_custom_storyline_flow():
    """Verify custom premise/storyline integration (e.g. Mona in Kyoto comedy)."""
    chk_conn = sqlite3.connect(":memory:", check_same_thread=False)
    graph_runner = TaleWeaverGraph(checkpointer=SqliteSaver(chk_conn))

    storyline = (
        "Mona lives in a traditional countryside village in Kyoto, with her traditional house, "
        "fields, market, and later takes an exciting family vacation to Tokyo city."
    )

    mock_world = WorldLore(
        title="Mona in Kyoto",
        genre="Comedy / Slice of Life",
        storyline=storyline,
        setting_description="Quiet cedar hills, tea fields, and a bustling Tokyo metropolis.",
        magic_or_tech_rules="Modern everyday life with funny cultural clashes.",
        primary_conflict="Mona's mischievous ideas turning peaceful village routines into family comedy.",
        tone="Warm, cheerful, and humorous",
    )
    graph_runner.architect.generate_world = MagicMock(return_value=mock_world)

    config = {"configurable": {"thread_id": "mona_session_001"}}
    state: StoryState = {
        "title": "Mona in Kyoto",
        "genre": "Comedy / Slice of Life",
        "storyline": storyline,
        "target_chapters": 2,
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

    graph_runner.app.invoke(state, config=config)
    snap = graph_runner.app.get_state(config)
    assert snap.tasks[0].interrupts[0].value["stage"] == "world_review"
    assert "Tokyo" in snap.tasks[0].interrupts[0].value["storyline"]
    assert "Mona" in snap.tasks[0].interrupts[0].value["title"]
