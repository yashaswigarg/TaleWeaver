"""Unit tests for TaleWeaver's LangGraph graph construction and routing policies."""

import sqlite3
from unittest.mock import MagicMock
from langgraph.checkpoint.sqlite import SqliteSaver
from taleweaver.graph.workflow import TaleWeaverGraph
from taleweaver.state import (
    ChapterDraft,
    EditorCritique,
    StoryChoice,
    StoryState,
    WorldLore,
)


def test_graph_node_registration():
    """Verify all 8 nodes and compilation structure in TaleWeaverGraph."""
    graph_runner = TaleWeaverGraph()
    app = graph_runner.app
    nodes = app.nodes
    expected_nodes = [
        "world_smith",
        "character_designer",
        "scribe_draft",
        "editor_review",
        "illustrator",
        "publisher",
        "player_decision",
        "compile_book",
    ]
    for node_name in expected_nodes:
        assert node_name in nodes


def test_editor_routing_policy_quota_safe():
    """Verify strictly capped loop behavior:
    1. Approved critique -> routes to illustrator.
    2. Rejected critique with remaining attempts -> routes to scribe_draft.
    3. Rejected critique with max revisions reached -> routes to illustrator (quota safety).
    """
    graph_runner = TaleWeaverGraph()

    # Case 1: Approved
    state_approved: StoryState = {
        "editor_critique": EditorCritique(
            approved=True, score=9, critique="Superb pacing", required_fixes=[]
        ),
        "revision_count": 0,
    }
    assert graph_runner._route_after_editor(state_approved) == "illustrator"

    # Case 2: Rejected with 0 revisions completed (retry once allowed)
    state_retry: StoryState = {
        "editor_critique": EditorCritique(
            approved=False, score=5, critique="Needs more tension", required_fixes=["Add shadow sounds"]
        ),
        "revision_count": 0,
    }
    assert graph_runner._route_after_editor(state_retry) == "scribe_draft"

    # Case 3: Rejected but already revised once (revision_count >= 1 -> break cycle)
    state_max_revisions: StoryState = {
        "editor_critique": EditorCritique(
            approved=False, score=6, critique="Still slightly slow", required_fixes=[]
        ),
        "revision_count": 1,
    }
    assert graph_runner._route_after_editor(state_max_revisions) == "illustrator"


def test_player_decision_routing_policy():
    """Verify decision routing advances to next chapter or compiles book on game over."""
    graph_runner = TaleWeaverGraph()

    # Continue story
    state_active: StoryState = {"game_over": False}
    assert graph_runner._route_after_decision(state_active) == "scribe_draft"

    # Conclude story
    state_over: StoryState = {"game_over": True}
    assert graph_runner._route_after_decision(state_over) == "compile_book"


def test_graph_interrupt_flow():
    """Verify graph execution pauses at HitL interrupt checkpoints with SqliteSaver."""
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    checkpointer = SqliteSaver(conn)
    graph_runner = TaleWeaverGraph(checkpointer=checkpointer)

    # Mock the architect agent so we don't make real external calls in this fast unit test
    mock_world = WorldLore(
        title="Chronicles of the Iron Sky",
        genre="Dieselpunk",
        setting_description="Smoky airships and brass towers.",
        magic_or_tech_rules="Diesel-powered magnetic engines.",
        primary_conflict="Sky pirates blockading trade routes.",
        tone="Gritty and fast-paced",
    )
    graph_runner.architect.generate_world = MagicMock(return_value=mock_world)

    config = {"configurable": {"thread_id": "test_thread_1"}}
    initial_input: StoryState = {
        "title": "Chronicles of the Iron Sky",
        "genre": "Dieselpunk",
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
        "status_message": "Started",
    }

    # First invoke should stop at HitL interrupt 1 (world_review)
    result = graph_runner.app.invoke(initial_input, config=config)

    # Inspect state checkpoint in memory
    state_snapshot = graph_runner.app.get_state(config)
    assert len(state_snapshot.tasks) > 0
    interrupts = state_snapshot.tasks[0].interrupts
    assert len(interrupts) > 0
    assert interrupts[0].value["stage"] == "world_review"
    assert interrupts[0].value["title"] == "Chronicles of the Iron Sky"
