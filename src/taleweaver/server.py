"""FastAPI Web Server and Interactive Console for TaleWeaver.

Provides REST endpoints for story management, timeline time-travel inspection,
branching, and interactive web visualization.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from taleweaver.graph.workflow import create_game_graph, get_story_timeline, fork_story_branch
from taleweaver.mcp_servers.lore_server import db as lore_db
from taleweaver.mcp_servers.rules_server import rules as rules_engine
from taleweaver.config import LOREBOOK_DB_PATH

app = FastAPI(title="TaleWeaver Interactive Engine API")
graph_app = create_game_graph()


class BranchRequest(BaseModel):
    checkpoint_id: str
    new_thread_id: Optional[str] = None


class ActionCheckRequest(BaseModel):
    character_name: str
    required_item: str
    action_description: str


class SkillCheckRequest(BaseModel):
    character_name: str
    attribute: str
    difficulty_dc: int = 12


@app.get("/api/health")
def health() -> Dict[str, str]:
    return {"status": "healthy", "service": "taleweaver-agentic-engine"}


@app.get("/api/lore")
def get_lore() -> Dict[str, Any]:
    world = lore_db.get_world()
    characters = lore_db.list_characters()
    return {
        "world": world,
        "characters": characters,
        "party_size": len(characters),
    }


@app.get("/api/story/{thread_id}/timeline")
def story_timeline(thread_id: str) -> List[Dict[str, Any]]:
    return get_story_timeline(graph_app, thread_id)


@app.post("/api/story/{thread_id}/branch")
def branch_story_checkpoint(thread_id: str, req: BranchRequest) -> Dict[str, Any]:
    try:
        res = fork_story_branch(
            graph_app,
            source_thread_id=thread_id,
            checkpoint_id=req.checkpoint_id,
            new_branch_thread_id=req.new_thread_id,
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/rules/check-action")
def check_action(req: ActionCheckRequest) -> Dict[str, Any]:
    return rules_engine.validate_action(
        character_name=req.character_name,
        required_item=req.required_item,
        action_description=req.action_description,
    )


@app.post("/api/rules/skill-check")
def skill_check(req: SkillCheckRequest) -> Dict[str, Any]:
    return rules_engine.resolve_skill_check(
        character_name=req.character_name,
        attribute=req.attribute,
        difficulty_dc=req.difficulty_dc,
    )


@app.get("/", response_class=HTMLResponse)
def index_console() -> str:
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TaleWeaver: Multi-Agent Story Forge</title>
    <link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@600;700&family=Plus+Jakarta+Sans:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-primary: #0b0f19;
            --bg-card: rgba(18, 24, 40, 0.85);
            --border: rgba(255, 255, 255, 0.08);
            --gold: #d4af37;
            --purple: #8b5cf6;
            --accent: #6366f1;
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: 'Plus Jakarta Sans', sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }
        header {
            background: rgba(15, 23, 42, 0.95);
            border-bottom: 1px solid var(--border);
            padding: 1rem 2.5rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            backdrop-filter: blur(12px);
        }
        .brand {
            font-family: 'Cinzel', serif;
            font-size: 1.5rem;
            color: var(--gold);
            letter-spacing: 0.05em;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        .badge {
            background: rgba(139, 92, 246, 0.2);
            color: #c4b5fd;
            border: 1px solid rgba(139, 92, 246, 0.4);
            padding: 0.25rem 0.6rem;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 600;
        }
        main {
            max-width: 1200px;
            width: 100%;
            margin: 2rem auto;
            padding: 0 1.5rem;
            display: grid;
            grid-template-columns: 1fr 360px;
            gap: 2rem;
        }
        .card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1.5rem;
            box-shadow: 0 15px 30px -10px rgba(0, 0, 0, 0.5);
        }
        h2, h3 { font-family: 'Cinzel', serif; color: var(--gold); margin-bottom: 1rem; }
        .node-track {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 2rem;
            position: relative;
        }
        .node-track::before {
            content: '';
            position: absolute;
            top: 50%;
            left: 5%;
            right: 5%;
            height: 2px;
            background: var(--border);
            z-index: 1;
        }
        .node-step {
            position: relative;
            z-index: 2;
            background: #1e293b;
            border: 2px solid var(--purple);
            color: #cbd5e1;
            padding: 0.5rem 0.85rem;
            border-radius: 8px;
            font-size: 0.8rem;
            font-weight: 600;
            text-align: center;
        }
        .node-step.active {
            border-color: var(--gold);
            background: rgba(212, 175, 55, 0.15);
            color: var(--gold);
            box-shadow: 0 0 15px rgba(212, 175, 55, 0.3);
        }
        .btn-action {
            background: var(--accent);
            color: white;
            border: none;
            padding: 0.6rem 1.2rem;
            border-radius: 6px;
            cursor: pointer;
            font-weight: 600;
            transition: all 0.2s;
        }
        .btn-action:hover { opacity: 0.9; transform: translateY(-1px); }
        .char-item {
            background: #1e293b;
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 0.75rem;
            margin-bottom: 0.75rem;
        }
        .char-name { font-weight: 600; color: #f1f5f9; font-size: 0.95rem; }
        .char-role { font-size: 0.75rem; color: var(--gold); text-transform: uppercase; }
        .inventory-tag {
            display: inline-block;
            background: rgba(255, 255, 255, 0.08);
            padding: 0.15rem 0.4rem;
            border-radius: 4px;
            font-size: 0.7rem;
            margin-top: 0.4rem;
            margin-right: 0.3rem;
        }
    </style>
</head>
<body>
    <header>
        <div class="brand">⚔️ TaleWeaver</div>
        <div><span class="badge">LangGraph + FastMCP + HitL Engine</span></div>
    </header>

    <main>
        <div>
            <div class="card" style="margin-bottom: 1.5rem;">
                <h2>LangGraph Orchestration Pipeline</h2>
                <div class="node-track">
                    <div class="node-step">World Smith</div>
                    <div class="node-step">Character Designer</div>
                    <div class="node-step active">Scribe & Editor</div>
                    <div class="node-step">Illustrator</div>
                    <div class="node-step">HitL Choice</div>
                </div>
                <p style="color: var(--text-secondary); font-size: 0.9rem;">
                    Checkpointed via <code>SqliteSaver</code>. Supports dynamic cyclic editorial reflection, multi-stage human approvals, and narrative timeline branching.
                </p>
            </div>

            <div class="card">
                <h2>Time-Travel & Multiverse Checkpoints</h2>
                <p style="color: var(--text-secondary); font-size: 0.85rem; margin-bottom: 1rem;">
                    LangGraph state history allows rewinding any active storyline to an earlier chapter and branching down alternate outcomes.
                </p>
                <div id="timeline-box" style="font-size: 0.85rem; color: var(--text-secondary);">
                    Enter an active Thread ID below to inspect checkpoints or fork:
                    <div style="display: flex; gap: 0.5rem; margin-top: 0.5rem;">
                        <input id="thread-id-input" type="text" placeholder="e.g. story_thread_1" style="background:#1e293b; color:white; border:1px solid var(--border); padding:0.5rem; border-radius:6px; flex:1;" />
                        <button class="btn-action" onclick="fetchTimeline()">Load Timeline</button>
                    </div>
                </div>
                <div id="timeline-list" style="margin-top: 1rem;"></div>
            </div>
        </div>

        <div>
            <div class="card" style="margin-bottom: 1.5rem;">
                <h3>Active Party Lore</h3>
                <div id="party-list">Loading party dossier...</div>
            </div>

            <div class="card">
                <h3>MCP World Consistency</h3>
                <div style="font-size: 0.85rem; color: var(--text-secondary);">
                    3 Integrated FastMCP Servers:
                    <ul style="margin: 0.75rem 0 0 1.25rem; line-height: 1.8;">
                        <li><strong>Lore Server:</strong> SQLite Canon Lore</li>
                        <li><strong>Rules Server:</strong> Inventory & Skill DC Checks</li>
                        <li><strong>Publisher Server:</strong> HTML/MD eBook Forge</li>
                    </ul>
                </div>
            </div>
        </div>
    </main>

    <script>
        async function loadLore() {
            try {
                const res = await fetch('/api/lore');
                const data = await res.json();
                const container = document.getElementById('party-list');
                if (data.characters && data.characters.length > 0) {
                    container.innerHTML = data.characters.map(c => `
                        <div class="char-item">
                            <div class="char-name">${c.name}</div>
                            <div class="char-role">${c.role} (${c.archetype})</div>
                            <div style="font-size: 0.75rem; color: #94a3b8; margin-top: 0.25rem;">Status: ${c.status}</div>
                            <div>${(c.inventory || []).map(i => `<span class="inventory-tag">${i}</span>`).join('')}</div>
                        </div>
                    `).join('');
                } else {
                    container.innerHTML = '<div style="color: var(--text-secondary); font-size: 0.85rem;">No active party loaded. Start a game to generate dossiers.</div>';
                }
            } catch (e) {}
        }

        async function fetchTimeline() {
            const tid = document.getElementById('thread-id-input').value.trim();
            if (!tid) return;
            try {
                const res = await fetch(`/api/story/${tid}/timeline`);
                const checkpoints = await res.json();
                const list = document.getElementById('timeline-list');
                if (checkpoints.length === 0) {
                    list.innerHTML = '<div style="color: var(--text-secondary);">No checkpoints found for this thread.</div>';
                    return;
                }
                list.innerHTML = checkpoints.map(cp => `
                    <div style="background:#1e293b; padding:0.75rem; border-radius:6px; margin-bottom:0.5rem; border:1px solid var(--border);">
                        <div style="font-weight:600; color:var(--gold);">Chapter ${cp.chapter_number}: ${cp.title}</div>
                        <div style="font-size:0.75rem; color:#94a3b8;">Checkpoint: ${cp.checkpoint_id.substring(0, 16)}...</div>
                        <div style="font-size:0.8rem; margin-top:0.25rem;">${cp.summary}</div>
                    </div>
                `).join('');
            } catch (e) {
                alert('Failed to load timeline: ' + e.message);
            }
        }

        loadLore();
    </script>
</body>
</html>
"""
