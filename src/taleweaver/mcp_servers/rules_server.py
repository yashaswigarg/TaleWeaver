"""World Physics and Narrative Consistency MCP Server for TaleWeaver.

Provides tools for inventory validation, deterministic attribute skill checks,
and world clock state tracking.
"""

from __future__ import annotations

import random
from typing import Any, Dict
from mcp.server.mcpserver import MCPServer
from taleweaver.mcp_servers.lore_server import db as lore_db


class RulesEngine:
    """Manages world mechanics, inventory action validation, and skill checks."""

    def __init__(self):
        self._world_hour = 8  # Starts at 08:00 (Morning)

    def validate_action(
        self,
        character_name: str,
        required_item: str,
        action_description: str,
    ) -> Dict[str, Any]:
        """Validate if character possesses the necessary item to perform an action."""
        chars = lore_db.list_characters()
        target_char = None
        for char in chars:
            if char.get("name", "").lower() == character_name.lower():
                target_char = char
                break

        if not target_char:
            return {
                "valid": False,
                "reason": f"Character '{character_name}' is not registered in active party lore.",
                "has_item": False,
            }

        inventory = [item.lower() for item in target_char.get("inventory", [])]
        req_clean = required_item.lower().strip()

        # Fuzzy check: match full item or substring (e.g. "key" in "rusty iron key")
        has_item = any(req_clean in item or item in req_clean for item in inventory)

        if not has_item and req_clean not in ["none", ""]:
            return {
                "valid": False,
                "reason": f"{character_name} does not have '{required_item}' in inventory. Current items: {target_char.get('inventory')}.",
                "has_item": False,
            }

        return {
            "valid": True,
            "reason": f"Inventory check passed: {character_name} holds required equipment.",
            "has_item": True,
            "current_inventory": target_char.get("inventory"),
        }

    def resolve_skill_check(
        self,
        character_name: str,
        attribute: str,
        difficulty_dc: int = 12,
    ) -> Dict[str, Any]:
        """Roll a d20 skill check with attribute modifiers against a Target Difficulty Class (DC)."""
        chars = lore_db.list_characters()
        target_char = next((c for c in chars if c.get("name", "").lower() == character_name.lower()), None)

        modifier = 0
        if target_char:
            archetype = target_char.get("archetype", "").lower()
            attr = attribute.lower()
            if any(k in archetype for k in ["warrior", "knight", "soldier"]) and attr in ["strength", "athletics", "combat"]:
                modifier = 3
            elif any(k in archetype for k in ["rogue", "thief", "scoundrel", "hunter"]) and attr in ["agility", "stealth", "sleight"]:
                modifier = 3
            elif any(k in archetype for k in ["mage", "wizard", "scholar", "cleric"]) and attr in ["intelligence", "arcana", "lore"]:
                modifier = 3
            elif any(k in archetype for k in ["bard", "merchant", "noble"]) and attr in ["charisma", "persuasion", "deception"]:
                modifier = 3

        d20 = random.randint(1, 20)
        total = d20 + modifier
        success = total >= difficulty_dc

        tier = "Critical Failure" if d20 == 1 else "Critical Success" if d20 == 20 else "Success" if success else "Failure"

        return {
            "character": character_name,
            "attribute": attribute,
            "d20_roll": d20,
            "modifier": modifier,
            "total_score": total,
            "difficulty_dc": difficulty_dc,
            "success": success,
            "outcome_tier": tier,
        }

    def advance_time(self, hours: int = 4) -> Dict[str, Any]:
        """Advance the world clock and return current time of day."""
        self._world_hour = (self._world_hour + hours) % 24
        hour = self._world_hour

        if 5 <= hour < 8:
            phase = "Dawn"
            lighting = "Soft twilight breaking across the horizon"
        elif 8 <= hour < 17:
            phase = "Daylight"
            lighting = "Bright overhead sunlight"
        elif 17 <= hour < 20:
            phase = "Dusk"
            lighting = "Deep amber sunset casting long shadows"
        elif 20 <= hour < 23:
            phase = "Nightfall"
            lighting = "Starry night enveloped in shadows"
        else:
            phase = "Witching Hour"
            lighting = "Pitch black darkness, illuminated only by moonlight"

        return {
            "current_hour_24": hour,
            "time_string": f"{hour:02d}:00",
            "phase": phase,
            "environmental_lighting": lighting,
        }


rules = RulesEngine()

# Initialize FastMCP 2.x server
server = MCPServer("taleweaver-rules-server")


@server.tool(name="validate_inventory_action", description="Check if a character has the required item in inventory to execute a story action.")
def mcp_validate_action(character_name: str, required_item: str, action_description: str) -> Dict[str, Any]:
    return rules.validate_action(character_name, required_item, action_description)


@server.tool(name="resolve_skill_check", description="Roll a d20 skill check against a difficulty class (DC) with character archetype modifiers.")
def mcp_skill_check(character_name: str, attribute: str, difficulty_dc: int = 12) -> Dict[str, Any]:
    return rules.resolve_skill_check(character_name, attribute, difficulty_dc)


@server.tool(name="advance_world_clock", description="Advance the narrative world clock to track dawn/day/dusk/night environmental states.")
def mcp_advance_time(hours: int = 4) -> Dict[str, Any]:
    return rules.advance_time(hours)
