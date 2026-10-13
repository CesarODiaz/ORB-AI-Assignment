"""Wire the local model, the knowledge base, and the JSON store."""

import os
from pathlib import Path

from orb_agent.agent import Agent
from orb_agent.config import DEFAULT_DATA_DIR
from orb_agent.knowledge import KnowledgeBase
from orb_agent.llm_setup import load_llm_config
from orb_agent.ollama_client import OllamaClient
from orb_agent.storage import ConversationStore


def build_agent(
    model: str | None = None,
    host: str | None = None,
    data_dir: Path | None = None,
) -> Agent:
    saved = load_llm_config()
    chosen_model = model or os.environ.get("OLLAMA_MODEL") or saved["model"]
    chosen_host = host or os.environ.get("OLLAMA_HOST") or saved["host"]
    client = OllamaClient(host=chosen_host, model=chosen_model)
    store = ConversationStore(data_dir or DEFAULT_DATA_DIR)
    return Agent(client, store, KnowledgeBase.load(), model_name=chosen_model)
