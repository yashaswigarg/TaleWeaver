import pytest
from fastapi.testclient import TestClient
from taleweaver.server import app
from taleweaver.graph.workflow import get_story_timeline, fork_story_branch, create_game_graph


client = TestClient(app)


def test_server_health():
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"


def test_server_lore_endpoint():
    res = client.get("/api/lore")
    assert res.status_code == 200
    data = res.json()
    assert "party_size" in data
    assert "characters" in data


def test_server_index_html():
    res = client.get("/")
    assert res.status_code == 200
    assert "TaleWeaver" in res.text
    assert "LangGraph" in res.text


def test_rules_check_endpoints():
    action_res = client.post(
        "/api/rules/check-action",
        json={
            "character_name": "Kaelen",
            "required_item": "Crystal Wand",
            "action_description": "Cast barrier",
        }
    )
    assert action_res.status_code == 200
    assert "valid" in action_res.json()

    skill_res = client.post(
        "/api/rules/skill-check",
        json={
            "character_name": "Kaelen",
            "attribute": "Intelligence",
            "difficulty_dc": 10,
        }
    )
    assert skill_res.status_code == 200
    assert "d20_roll" in skill_res.json()


def test_story_timeline_empty_thread():
    graph = create_game_graph(":memory:")
    timeline = get_story_timeline(graph, "non_existent_thread")
    assert isinstance(timeline, list)
    assert len(timeline) == 0
