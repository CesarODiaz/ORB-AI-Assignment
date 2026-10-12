"""JSON files, one conversation each, written atomically."""

import json
import os
import tempfile
from pathlib import Path

from orb_agent.config import DEFAULT_DATA_DIR


class ConversationStore:
    def __init__(self, directory: Path | None = None):
        self.directory = Path(directory or DEFAULT_DATA_DIR)
        self.directory.mkdir(parents=True, exist_ok=True)

    def path_for(self, conversation_id: str) -> Path:
        safe = "".join(ch for ch in conversation_id if ch.isalnum())
        if safe != conversation_id or not safe:
            raise KeyError(conversation_id)
        return self.directory / f"{safe}.json"

    def save(self, record: dict) -> None:
        path = self.path_for(record["id"])
        payload = json.dumps(record, ensure_ascii=False, indent=2)
        descriptor, temporary = tempfile.mkstemp(dir=self.directory, suffix=".tmp")
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                handle.write(payload)
            os.replace(temporary, path)
        except Exception:
            if os.path.exists(temporary):
                os.unlink(temporary)
            raise

    def load(self, conversation_id: str) -> dict:
        path = self.path_for(conversation_id)
        if not path.exists():
            raise KeyError(conversation_id)
        return json.loads(path.read_text(encoding="utf-8"))

    def list_conversations(self) -> list[dict]:
        rows = []
        for path in self.directory.glob("*.json"):
            try:
                record = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            intake = record.get("intake") or {}
            messages = record.get("messages") or []
            preview = ""
            for message in reversed(messages):
                if message.get("role") == "user":
                    preview = message.get("content", "")[:80]
                    break
            rows.append(
                {
                    "id": record.get("id"),
                    "ticket_id": record.get("ticket_id"),
                    "status": record.get("status"),
                    "updated_at": record.get("updated_at"),
                    "customer_name": intake.get("customer_name"),
                    "preview": preview,
                }
            )
        rows.sort(key=lambda row: row.get("updated_at") or "", reverse=True)
        return rows
