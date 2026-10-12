"""Wire the local model, the knowledge base, and the JSON store."""

from pathlib import Path

from orb_agent.agent import Agent
from orb_agent.config import DEFAULT_DATA_DIR, DEFAULT_MODEL, OLLAMA_HOST
from orb_agent.knowledge import KnowledgeBase
from orb_agent.ollama_client import OllamaClient
from orb_agent.storage import ConversationStore


def build_agent(
    model: str = DEFAULT_MODEL,
    host: str = OLLAMA_HOST,
    data_dir: Path | None = None,
) -> Agent:
    client = OllamaClient(host=host, model=model)
    store = ConversationStore(data_dir or DEFAULT_DATA_DIR)
    return Agent(client, store, KnowledgeBase.load(), model_name=model)
