# TaleWeaver: Interactive Story Forge & Storybook Engine

TaleWeaver is a multi-agent interactive story-crafting game and storybook compiler powered by **LangGraph** and **Model Context Protocol (MCP)**.

## Key Features
- **Multi-Agent Orchestration:** Specialized agents for World Building, Character Design, Story Writing, Editorial Quality Control, and Visual Illustration.
- **Human-in-the-Loop:** Interactive approval gateways for Premise, Character Dossiers, and branching story decisions.
- **MCP Subsystems:** Local SQLite-backed Lorebook and Filesystem Publisher servers.
- **State Persistence:** Resumable story sessions powered by LangGraph SQLite checkpointing.
- **Quota-Safe:** Intelligent call pacing and strictly capped critique loops designed for free-tier LLM APIs.
