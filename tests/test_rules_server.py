import pytest
from taleweaver.mcp_servers.rules_server import rules
from taleweaver.mcp_servers.lore_server import db as lore_db
from taleweaver.state import CharacterProfile


def test_rules_skill_check():
    res = rules.resolve_skill_check("Aria", "Athletics", difficulty_dc=10)
    assert "d20_roll" in res
    assert 1 <= res["d20_roll"] <= 20
    assert "total_score" in res
    assert "success" in res
    assert isinstance(res["success"], bool)


def test_rules_inventory_validation():
    # Register a character with an item
    lore_db.upsert_character(
        name="Kaelen",
        role="protagonist",
        archetype="Mage",
        traits=["observant"],
        backstory="A wandering scholar.",
        inventory=["Crystal Wand", "Ancient Spellbook"],
    )

    # Valid check (has item)
    valid_res = rules.validate_action("Kaelen", "Crystal Wand", "Cast a protective barrier")
    assert valid_res["valid"] is True
    assert valid_res["has_item"] is True

    # Invalid check (missing item)
    invalid_res = rules.validate_action("Kaelen", "Adamantine Key", "Unlock the iron gate")
    assert invalid_res["valid"] is False
    assert invalid_res["has_item"] is False


def test_rules_advance_time():
    t1 = rules.advance_time(4)
    assert "phase" in t1
    assert "time_string" in t1
    assert t1["phase"] in ["Dawn", "Daylight", "Dusk", "Nightfall", "Witching Hour"]
