"""Client interface and LangChain tool adapters for TaleWeaver's MCP servers."""

from __future__ import annotations

from typing import List
from langchain_core.tools import BaseTool, tool

from taleweaver.mcp_servers.lore_server import db as lore_db
from taleweaver.mcp_servers.publisher_server import publisher as publisher_engine


@tool
def query_lore(topic: str = "all") -> str:
    """Query the Lorebook database for canon world lore, active characters, inventory, and plot milestones."""
    return lore_db.query_lore(topic)


@tool
def update_character_status(name: str, status: str) -> str:
    """Update a character's current state (e.g. 'Wounded', 'Carrying the artifact', 'Fled into the mist')."""
    return lore_db.update_status(name, status)


@tool
def record_inventory_change(character_name: str, item: str, action: str) -> str:
    """Record an item addition or removal from a character's inventory (action: 'add' or 'remove')."""
    return lore_db.modify_inventory(character_name, item, action)


@tool
def record_chapter_milestone(chapter_num: int, event_summary: str) -> str:
    """Record a major plot milestone or permanent choice consequence into canon lore."""
    return lore_db.record_milestone(chapter_num, event_summary)


@tool
def publish_story_chapter(
    chapter_num: int,
    title: str,
    content: str,
    visual_prompt: str,
    chosen_action: str = "",
) -> str:
    """Save the final accepted chapter and visual prompt into the storybook database."""
    return publisher_engine.save_chapter(
        chapter_num=chapter_num,
        title=title,
        content=content,
        visual_prompt=visual_prompt,
        chosen_action=chosen_action,
    )


@tool
def compile_entire_storybook(story_title: str, genre: str) -> str:
    """Compile all saved chapters into the master StoryBook.md markdown file."""
    return publisher_engine.compile_book(story_title=story_title, genre=genre)


def get_all_mcp_tools() -> List[BaseTool]:
    """Returns the complete list of LangChain-compatible MCP tools for agent execution."""
    return [
        query_lore,
        update_character_status,
        record_inventory_change,
        record_chapter_milestone,
        publish_story_chapter,
        compile_entire_storybook,
    ]
