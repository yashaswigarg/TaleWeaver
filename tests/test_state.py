"""Unit tests for TaleWeaver state schemas and configuration."""

import time
from taleweaver.config import RateLimiter, settings
from taleweaver.state import (
    ChapterDraft,
    ChapterRecord,
    CharacterProfile,
    EditorCritique,
    IllustrationPrompt,
    StoryChoice,
    StoryState,
    WorldLore,
)


def test_character_profile_creation():
    """Verify character profile attributes and defaults."""
    hero = CharacterProfile(
        name="Kaelen Frost",
        role="protagonist",
        archetype="Chronos Scholar",
        traits=["Methodical", "Curious", "Haunted by the past"],
        backstory="Uncovered a broken time spindle in the ruins of Aethelgard.",
        inventory=["Brass Chronometer", "Cipher Notebook"],
    )
    assert hero.name == "Kaelen Frost"
    assert hero.role == "protagonist"
    assert "Brass Chronometer" in hero.inventory
    assert hero.status == "Healthy and ready"


def test_world_lore_creation():
    """Verify world lore schema validation."""
    lore = WorldLore(
        title="Echoes of the Sunken Spire",
        genre="Dark Fantasy / Steampunk",
        setting_description="Submerged Victorian towers lit by bioluminescent leviathans.",
        magic_or_tech_rules="Aetheric steam fuels all clockwork; diving suits require runic seals.",
        primary_conflict="The Leviathan King is stirring beneath the city foundations.",
        tone="Atmospheric, tense, and mystery-driven",
    )
    assert lore.title == "Echoes of the Sunken Spire"
    assert "Steampunk" in lore.genre


def test_chapter_draft_with_choices():
    """Verify chapter draft and branching choices."""
    choice1 = StoryChoice(id=1, text="Venture into the Flooded Vault", consequence_hint="High danger")
    choice2 = StoryChoice(id=2, text="Consult the Archivist upstairs", consequence_hint="Safer information")

    draft = ChapterDraft(
        chapter_number=1,
        title="The First Bell Tolled",
        content="Water lapped against the iron portcullis as Kaelen adjusted his brass respirator...",
        cliffhanger="A low vibration resonated from the depths, cracking the foundation stones.",
        choices=[choice1, choice2],
    )
    assert draft.chapter_number == 1
    assert len(draft.choices) == 2
    assert draft.choices[0].id == 1


def test_editor_critique_validation():
    """Verify editor critique structure."""
    critique = EditorCritique(
        approved=False,
        score=6,
        critique="The pacing lagged slightly during the vault investigation.",
        required_fixes=["Tighten the dialogue between Kaelen and the archivist"],
    )
    assert not critique.approved
    assert critique.score == 6
    assert len(critique.required_fixes) == 1


def test_illustration_prompt_validation():
    """Verify art prompt generation schema."""
    prompt = IllustrationPrompt(
        chapter_number=1,
        scene_title="The Flooded Portcullis",
        visual_prompt="A lone scholar standing before a massive submerged iron gate, amber gas lanterns, dark water reflections.",
        art_style="Oil painting, Rembrandt lighting, dark romanticism",
    )
    assert prompt.chapter_number == 1
    assert "submerged iron gate" in prompt.visual_prompt


def test_story_state_initialization():
    """Verify LangGraph StoryState dictionary contracts."""
    state: StoryState = {
        "title": "Echoes of the Sunken Spire",
        "genre": "Dark Fantasy",
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
        "status_message": "Initialized",
    }
    assert state["current_chapter_num"] == 1
    assert state["revision_count"] == 0
    assert not state["world_approved"]


def test_rate_limiter_pacing():
    """Verify that the rate limiter throttles calls when interval has not elapsed."""
    limiter = RateLimiter(min_interval=0.1)  # small test interval
    t0 = time.time()
    limiter.wait()
    limiter.wait()
    elapsed = time.time() - t0
    assert elapsed >= 0.1
