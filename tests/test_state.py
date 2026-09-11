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
    """Verify world lore schema validation and custom storyline."""
    lore = WorldLore(
        title="Mona in Kyoto",
        genre="Comedy / Slice-of-Life",
        storyline="Mona lives in a traditional countryside village, visiting Tokyo with family.",
        setting_description="Quiet cedar hills, tea fields, wooden verandahs, and lively market stalls.",
        magic_or_tech_rules="Realistic modern Japan with quaint village customs.",
        primary_conflict="Mona keeps causing harmless comedic misunderstandings in her family.",
        tone="Lighthearted, whimsical, and funny",
    )
    assert lore.title == "Mona in Kyoto"
    assert "Tokyo" in lore.storyline
    assert "Comedy" in lore.genre


def test_chapter_draft_with_choices_and_inventory_events():
    """Verify chapter draft, inventory changes, and finale flags."""
    from taleweaver.state import InventoryEvent
    choice1 = StoryChoice(id=1, text="Venture into the Flooded Vault", consequence_hint="High danger")
    choice2 = StoryChoice(id=2, text="Consult the Archivist upstairs", consequence_hint="Safer information")

    inv_event = InventoryEvent(character_name="Mona", item="Matcha Candy", action="add")

    draft = ChapterDraft(
        chapter_number=1,
        title="The First Bell Tolled",
        content="Water lapped against the iron portcullis as Kaelen adjusted his brass respirator...",
        cliffhanger="A low vibration resonated from the depths, cracking the foundation stones.",
        is_finale=False,
        inventory_events=[inv_event],
        choices=[choice1, choice2],
    )
    assert draft.chapter_number == 1
    assert len(draft.choices) == 2
    assert len(draft.inventory_events) == 1
    assert draft.inventory_events[0].item == "Matcha Candy"
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
