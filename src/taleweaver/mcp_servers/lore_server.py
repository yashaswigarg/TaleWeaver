"""Lorebook MCP Server backed by SQLite for TaleWeaver.

Provides tools to record and query canonical story world lore, character dossiers,
inventory changes, and key plot events.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

from mcp.server.mcpserver import MCPServer
from taleweaver.config import LOREBOOK_DB_PATH


class LorebookDB:
    """Manages the local SQLite database for story lore and state persistence."""

    def __init__(self, db_path: Optional[Path | str] = None):
        self.db_path = str(db_path or LOREBOOK_DB_PATH)
        self._init_db()

    @contextmanager
    def _connection(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self) -> None:
        """Create tables if they don't exist."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS world_lore (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    setting TEXT,
                    rules TEXT,
                    conflict TEXT,
                    tone TEXT,
                    storyline TEXT,
                    updated_at TEXT
                )
                """
            )
            # Add storyline column if upgrading existing DB
            try:
                cursor.execute("ALTER TABLE world_lore ADD COLUMN storyline TEXT")
            except sqlite3.OperationalError:
                pass
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS characters (
                    name TEXT PRIMARY KEY,
                    role TEXT,
                    archetype TEXT,
                    traits TEXT,
                    backstory TEXT,
                    inventory TEXT,
                    status TEXT,
                    updated_at TEXT
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS inventory_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    character_name TEXT,
                    item TEXT,
                    action TEXT,
                    timestamp TEXT
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS story_milestones (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chapter_num INTEGER,
                    event_summary TEXT,
                    timestamp TEXT
                )
                """
            )
            conn.commit()

    def store_world(self, setting: str, rules: str, conflict: str, tone: str, storyline: str = "") -> str:
        with self._connection() as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            cursor.execute(
                """
                INSERT INTO world_lore (id, setting, rules, conflict, tone, storyline, updated_at)
                VALUES (1, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    setting=excluded.setting,
                    rules=excluded.rules,
                    conflict=excluded.conflict,
                    tone=excluded.tone,
                    storyline=excluded.storyline,
                    updated_at=excluded.updated_at
                """,
                (setting, rules, conflict, tone, storyline, now),
            )
            conn.commit()
        return "World lore successfully preserved in Lorebook."

    def upsert_character(
        self,
        name: str,
        role: str,
        archetype: str,
        traits: List[str] | str,
        backstory: str,
        inventory: List[str] | str,
        status: str = "Healthy",
    ) -> str:
        traits_json = json.dumps(
            traits if isinstance(traits, list) else [t.strip() for t in traits.split(",") if t.strip()]
        )
        inventory_json = json.dumps(
            inventory if isinstance(inventory, list) else [i.strip() for i in inventory.split(",") if i.strip()]
        )
        now = datetime.now().isoformat()

        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO characters (name, role, archetype, traits, backstory, inventory, status, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    role=excluded.role,
                    archetype=excluded.archetype,
                    traits=excluded.traits,
                    backstory=excluded.backstory,
                    inventory=excluded.inventory,
                    status=excluded.status,
                    updated_at=excluded.updated_at
                """,
                (name, role, archetype, traits_json, backstory, inventory_json, status, now),
            )
            conn.commit()
        return f"Character '{name}' registered/updated in Lorebook."

    def update_status(self, name: str, new_status: str) -> str:
        with self._connection() as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            cursor.execute(
                "UPDATE characters SET status = ?, updated_at = ? WHERE name = ?",
                (new_status, now, name),
            )
            if cursor.rowcount == 0:
                return f"Character '{name}' not found."
            conn.commit()
        return f"Updated status of '{name}' to: {new_status}"

    def modify_inventory(self, character_name: str, item: str, action: str) -> str:
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT inventory FROM characters WHERE name = ?", (character_name,))
            row = cursor.fetchone()
            if not row:
                return f"Character '{character_name}' not found."

            inv: List[str] = json.loads(row["inventory"]) if row["inventory"] else []
            action_lower = action.lower().strip()

            if action_lower in ("add", "gain", "acquire"):
                if item not in inv:
                    inv.append(item)
            elif action_lower in ("remove", "lose", "use", "discard"):
                inv = [i for i in inv if i.lower() != item.lower()]

            now = datetime.now().isoformat()
            cursor.execute(
                "UPDATE characters SET inventory = ?, updated_at = ? WHERE name = ?",
                (json.dumps(inv), now, character_name),
            )
            cursor.execute(
                "INSERT INTO inventory_log (character_name, item, action, timestamp) VALUES (?, ?, ?, ?)",
                (character_name, item, action, now),
            )
            conn.commit()
        return f"Inventory for '{character_name}' updated. Current items: {', '.join(inv) or 'None'}"

    def record_milestone(self, chapter_num: int, event_summary: str) -> str:
        with self._connection() as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            cursor.execute(
                "INSERT INTO story_milestones (chapter_num, event_summary, timestamp) VALUES (?, ?, ?)",
                (chapter_num, event_summary, now),
            )
            conn.commit()
        return f"Milestone for Chapter {chapter_num} recorded."

    def get_character(self, name: str) -> Optional[Dict[str, Any]]:
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM characters WHERE LOWER(name) = LOWER(?)", (name,))
            row = cursor.fetchone()
            if not row:
                return None
            return {
                "name": row["name"],
                "role": row["role"],
                "archetype": row["archetype"],
                "traits": json.loads(row["traits"]),
                "backstory": row["backstory"],
                "inventory": json.loads(row["inventory"]),
                "status": row["status"],
            }

    def list_characters(self) -> List[Dict[str, Any]]:
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM characters ORDER BY role")
            rows = cursor.fetchall()
            return [
                {
                    "name": r["name"],
                    "role": r["role"],
                    "archetype": r["archetype"],
                    "traits": json.loads(r["traits"]),
                    "backstory": r["backstory"],
                    "inventory": json.loads(r["inventory"]),
                    "status": r["status"],
                }
                for r in rows
            ]

    def get_world(self) -> Optional[Dict[str, Any]]:
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM world_lore WHERE id = 1")
            row = cursor.fetchone()
            if not row:
                return None
            return {
                "setting": row["setting"],
                "rules": row["rules"],
                "conflict": row["conflict"],
                "tone": row["tone"],
                "storyline": row["storyline"] if "storyline" in row.keys() else "",
                "updated_at": row["updated_at"],
            }

    def query_lore(self, topic: str) -> str:
        """Search world lore, characters, and milestones for context."""
        topic_lower = topic.lower().strip()
        results: List[str] = []

        with self._connection() as conn:
            cursor = conn.cursor()

            # World lore
            cursor.execute("SELECT * FROM world_lore WHERE id = 1")
            w = cursor.fetchone()
            if w:
                storyline_text = f"\n- Core Storyline / Premise: {w['storyline']}" if w["storyline"] else ""
                results.append(
                    f"WORLD LORE:\n- Setting: {w['setting']}\n- Rules: {w['rules']}\n- Stakes: {w['conflict']}\n- Tone: {w['tone']}{storyline_text}"
                )

            # Character matches
            cursor.execute("SELECT * FROM characters")
            chars = cursor.fetchall()
            matching_chars = [
                c
                for c in chars
                if topic_lower in c["name"].lower()
                or topic_lower in c["role"].lower()
                or topic_lower in c["archetype"].lower()
                or topic_lower in c["traits"].lower()
            ]
            if matching_chars:
                results.append("CHARACTERS RELEVANT TO QUERY:")
                for c in matching_chars:
                    results.append(
                        f"• {c['name']} ({c['role']}, {c['archetype']}) | Status: {c['status']} | Items: {c['inventory']}"
                    )
            elif not topic_lower or topic_lower in ("all", "characters", "people"):
                results.append("ACTIVE ROSTER:")
                for c in chars:
                    results.append(
                        f"• {c['name']} ({c['role']}) - Status: {c['status']} - Inventory: {c['inventory']}"
                    )

            # Milestones
            cursor.execute("SELECT * FROM story_milestones ORDER BY chapter_num DESC LIMIT 5")
            milestones = cursor.fetchall()
            if milestones:
                results.append("RECENT STORY MILESTONES:")
                for m in reversed(milestones):
                    results.append(f"Chapter {m['chapter_num']}: {m['event_summary']}")

        return "\n\n".join(results) if results else f"No specific lore found for query: '{topic}'"


# Default database instance
db = LorebookDB()

# FastMCP Server definition
server = MCPServer("taleweaver_lore_server")


@server.tool()
def store_world_lore(setting: str, rules: str, conflict: str, tone: str, storyline: str = "") -> str:
    """Store or update the canonical story setting, physical/magical laws, conflict, tone, and storyline."""
    return db.store_world(setting, rules, conflict, tone, storyline)


@server.tool()
def register_character(
    name: str,
    role: str,
    archetype: str,
    traits: str,
    backstory: str,
    inventory: str,
    status: str = "Healthy",
) -> str:
    """Register or overwrite a character profile in the Lorebook."""
    return db.upsert_character(name, role, archetype, traits, backstory, inventory, status)


@server.tool()
def update_character_status(name: str, status: str) -> str:
    """Update a character's current state (e.g. 'Wounded in arm', 'Carrying cursed amulet')."""
    return db.update_status(name, status)


@server.tool()
def record_inventory_change(character_name: str, item: str, action: str) -> str:
    """Record an item being acquired or lost by a character (action: 'add' or 'remove')."""
    return db.modify_inventory(character_name, item, action)


@server.tool()
def record_chapter_milestone(chapter_num: int, event_summary: str) -> str:
    """Record a major plot event or canonical outcome for future chapter consistency."""
    return db.record_milestone(chapter_num, event_summary)


@server.tool()
def query_lore(topic: str = "all") -> str:
    """Query the Lorebook database for world rules, characters, items, or recent events."""
    return db.query_lore(topic)


@server.tool()
def get_character_profile(name: str) -> str:
    """Retrieve full profile, traits, backstory, and inventory for a specific character."""
    profile = db.get_character(name)
    if not profile:
        return f"Character '{name}' not found in Lorebook."
    return json.dumps(profile, indent=2)


if __name__ == "__main__":
    server.run(transport="stdio")
