"""Unit tests for TaleWeaver's MCP servers and tool adapters."""

import os
import tempfile
from pathlib import Path
from taleweaver.mcp_servers.lore_server import LorebookDB
from taleweaver.mcp_servers.publisher_server import PublisherEngine
from taleweaver.mcp_servers.client import get_all_mcp_tools


def test_lorebook_db_lifecycle():
    """Verify storing world, characters, inventory changes, and querying in Lorebook."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_lore.db"
        db = LorebookDB(db_path=db_path)

        # 1. Store world lore
        res = db.store_world(
            setting="Sky islands connected by copper chain bridges",
            rules="Gravity fluctuations occur during solar eclipses",
            conflict="The chain links are rusting, threatening world collapse",
            tone="High-flying, perilous adventure",
        )
        assert "successfully preserved" in res

        # 2. Register character
        res_char = db.upsert_character(
            name="Aria Windstrider",
            role="protagonist",
            archetype="Bridge Rigger",
            traits=["Agile", "Fearless of heights"],
            backstory="Survived a bridge severance as an apprentice.",
            inventory=["Grappling Harpoon", "Copper Goggles"],
            status="Healthy",
        )
        assert "registered" in res_char

        # 3. Query character
        char = db.get_character("Aria Windstrider")
        assert char is not None
        assert char["archetype"] == "Bridge Rigger"
        assert "Grappling Harpoon" in char["inventory"]

        # 4. Modify inventory
        res_inv = db.modify_inventory("Aria Windstrider", "Runic Carabiner", "add")
        assert "Runic Carabiner" in res_inv
        char_updated = db.get_character("Aria Windstrider")
        assert "Runic Carabiner" in char_updated["inventory"]

        # 5. Update status
        db.update_status("Aria Windstrider", "Exhausted after scaling the East Span")
        char_status = db.get_character("Aria Windstrider")
        assert "Exhausted" in char_status["status"]

        # 6. Record milestone
        res_mile = db.record_milestone(1, "Aria repaired the mooring clamp before the gale hit.")
        assert "recorded" in res_mile

        # 7. Query lore
        lore_text = db.query_lore("Aria")
        assert "Bridge Rigger" in lore_text
        assert "Sky islands" in lore_text


def test_publisher_engine_lifecycle():
    """Verify chapter persistence and master StoryBook compilation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        out_dir = Path(tmpdir)
        book_path = out_dir / "Test_StoryBook.md"
        pub = PublisherEngine(output_dir=out_dir, book_path=book_path)

        # 1. Save chapter 1
        res1 = pub.save_chapter(
            chapter_num=1,
            title="The Creaking Chain",
            content="Wind whistled through the rusty links as Aria secured her harness...",
            visual_prompt="A lone climber silhouetted against a setting sun on an enormous sky chain.",
            chosen_action="Leap toward the auxiliary winch",
        )
        assert "Chapter 1" in res1

        # 2. Save chapter 2
        res2 = pub.save_chapter(
            chapter_num=2,
            title="Sparks in the Fog",
            content="The auxiliary winch groaned under the strain, throwing orange sparks into the mist...",
            visual_prompt="Gear teeth grinding together with fiery sparks amidst dense clouds.",
            chosen_action=None,
        )
        assert "Chapter 2" in res2

        # 3. Load chapters
        chapters = pub.load_chapters()
        assert len(chapters) == 2
        assert chapters[0]["chapter_num"] == 1
        assert chapters[1]["chapter_num"] == 2

        # 4. Compile book
        compile_res = pub.compile_book(story_title="Chains of the Sky", genre="Aetherpunk")
        assert "successfully compiled with 2 chapters" in compile_res
        assert book_path.exists()
        html_file = out_dir / "StoryBook.html"
        assert html_file.exists()
        html_text = html_file.read_text(encoding="utf-8")
        assert "<!DOCTYPE html>" in html_text
        assert "Chains of the Sky" in html_text
        assert "Chapter 1" in html_text

        content = pub.read_book()
        assert "# Chains of the Sky" in content
        assert "Chapter 1: The Creaking Chain" in content
        assert "Chapter 2: Sparks in the Fog" in content
        assert "Leap toward the auxiliary winch" in content


def test_mcp_client_tool_bindings():
    """Verify LangChain tool wrappers."""
    tools = get_all_mcp_tools()
    assert len(tools) == 6
    tool_names = [t.name for t in tools]
    assert "query_lore" in tool_names
    assert "update_character_status" in tool_names
    assert "record_inventory_change" in tool_names
    assert "publish_story_chapter" in tool_names
    assert "compile_entire_storybook" in tool_names
