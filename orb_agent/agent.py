"""Conversation orchestration. Python owns the ticket; the model owns the wording."""

import threading
import uuid
from datetime import datetime, timezone

from orb_agent.extract import extract_fields
from orb_agent.flow import is_pure_confirmation, is_rejection
from orb_agent.language import detect_language
from orb_agent.ollama_client import LlmError
from orb_agent.prompts import system_prompt
from orb_agent.sentiment import combine_sentiment, lexicon_sentiment, sticky
from orb_agent.summary import (
    build_summary,
    closing_message,
    confirmation_block,
    next_question,
)
from orb_agent.knowledge import _STOP
from orb_agent.textutil import clip, tokens
from orb_agent.validation import apply_fields, empty_intake, missing_fields

GREETING = (
    "Hello, I'm Mara from ORB Atelier in Valencia. We restore lamps, furniture, and small upholstery. "
    "Tell me what needs restoring and, if you can, your name and an email or a phone number."
)
HISTORY_WINDOW = 6


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _shares(reply: str, snippet: str, minimum: int = 3) -> bool:
    useful = (tokens(reply) & tokens(snippet)) - _STOP
    return len(useful) >= minimum


class Agent:
    def __init__(self, client, store, knowledge, model_name: str = "llama3.2"):
        self.client = client
        self.store = store
        self.knowledge = knowledge
        self.model_name = model_name
        self._guard = threading.Lock()
        self._turns: dict[str, threading.Lock] = {}

    def _turn_lock(self, conversation_id: str) -> threading.Lock:
        with self._guard:
            lock = self._turns.get(conversation_id)
            if lock is None:
                lock = threading.Lock()
                self._turns[conversation_id] = lock
            return lock

    def start(self) -> dict:
        now = _now()
        conversation_id = uuid.uuid4().hex[:12]
        record = {
            "id": conversation_id,
            "ticket_id": "AT-" + conversation_id[:6].upper(),
            "created_at": now,
            "updated_at": now,
            "status": "collecting",
            "language": "en",
            "sentiment": "neutral",
            "awaiting_correction": False,
            "intake": empty_intake(),
            "messages": [{"role": "assistant", "content": GREETING, "at": now}],
            "citations": [],
            "errors": [],
            "missing": missing_fields(empty_intake()),
            "summary": "",
            "model": self.model_name,
        }
        record["summary"] = build_summary(record)
        self.store.save(record)
        return self.present(record)

    def list_conversations(self) -> list[dict]:
        return self.store.list_conversations()

    def get(self, conversation_id: str) -> dict:
        return self.present(self.store.load(conversation_id))

    def handle(self, conversation_id: str, text: str) -> dict:
        with self._turn_lock(conversation_id):
            return self._handle(conversation_id, text)

    def _handle(self, conversation_id: str, text: str) -> dict:
        record = self.store.load(conversation_id)
        message = " ".join((text or "").split())
        if not message:
            raise ValueError("empty message")
        message = message[:4000]
        now = _now()
        record["messages"].append({"role": "user", "content": message, "at": now})
        record["language"] = detect_language(message, record.get("language", "en"))
        lexicon = lexicon_sentiment(message)

        if record["status"] == "closed":
            return self._reply(record, self._closed_reply(record), lexicon, now)

        if (
            record["status"] == "review"
            and not record.get("awaiting_correction")
            and is_pure_confirmation(message)
        ):
            record["status"] = "closed"
            record["missing"] = []
            record["errors"] = []
            return self._reply(record, closing_message(record), lexicon, now)

        candidate = extract_fields(message)
        if record["status"] == "review" and is_rejection(message) and not candidate:
            record["awaiting_correction"] = True
            record["status"] = "collecting"
            reply = (
                "All right, I will not file it yet. Which detail should I change?"
                if record["language"] == "en"
                else "De acuerdo, no la cierro todavía. ¿Qué dato cambio?"
            )
            return self._reply(record, reply, lexicon, now)

        record["errors"] = apply_fields(record["intake"], candidate)
        record["missing"] = missing_fields(record["intake"])
        citations = self.knowledge.search(message, record["language"])
        reply, model_sentiment, used_model = self._compose(record, citations)
        if not used_model:
            reply = self._fallback(record, citations)

        record["missing"] = missing_fields(record["intake"])
        if record["errors"]:
            notice = next_question(record["missing"], record["language"], record["errors"])
            if record["errors"][0]["code"] in {"invalid_email", "invalid_phone"} and notice not in reply:
                reply = f"{reply}\n\n{notice}".strip()

        if record["missing"] and "?" not in reply:
            reply = f"{reply}\n\n{next_question(record['missing'], record['language'], record['errors'])}".strip()

        if not record["missing"] and "?" in reply:
            reply = "I have what I need." if record["language"] == "en" else "Ya tengo los datos."

        if citations and not _shares(reply, citations[0]["snippet"]):
            if citations[0]["score"] >= 3:
                reply = f"{reply}\n\n{citations[0]['snippet']}".strip()

        if not record["missing"]:
            record["status"] = "review"
            record["awaiting_correction"] = False
            reply = clip(reply, 700)
            reply = f"{reply}\n\n{confirmation_block(record)}".strip()
        else:
            record["status"] = "collecting"
            reply = clip(reply, 1200)

        record["citations"] = citations
        proposed = combine_sentiment(lexicon, model_sentiment)
        record["sentiment"] = sticky(record.get("sentiment"), proposed)
        return self._reply(record, reply, None, now, sentiment_already_set=True)

    def _compose(self, record: dict, citations: list[dict]) -> tuple[str, str | None, bool]:
        messages = self._model_messages(record, citations)
        try:
            parsed = self.client.complete(messages)
        except LlmError as exc:
            print(f"[orb] the model did not answer ({exc}); continuing with the local ticket")
            return "", None, False
        fields = parsed.get("fields")
        if isinstance(fields, str):
            fields = {}
        if isinstance(fields, dict):
            # Heuristics and earlier turns win. The model may only fill blanks.
            fresh = {
                key: value
                for key, value in fields.items()
                if not record["intake"].get(key)
            }
            record["errors"].extend(apply_fields(record["intake"], fresh))
        reply = str(parsed.get("reply") or "").strip()
        sentiment = parsed.get("sentiment")
        if not isinstance(sentiment, str):
            sentiment = None
        return reply, sentiment, True

    def _fallback(self, record: dict, citations: list[dict]) -> str:
        parts = []
        if citations:
            parts.append(citations[0]["snippet"])
        if record["missing"]:
            parts.append(next_question(record["missing"], record["language"], record["errors"]))
        elif record["language"] == "en":
            parts.append("I have everything I need. Please confirm the details below.")
        else:
            parts.append("Ya tengo lo necesario. Confirma los datos de abajo.")
        return "\n\n".join(parts)

    def _model_messages(self, record: dict, citations: list[dict]) -> list[dict]:
        system = system_prompt(record, citations)
        history = [item for item in record["messages"] if item["role"] in {"user", "assistant"}]
        window = history[-HISTORY_WINDOW:]
        return [{"role": "system", "content": system}, *[{"role": item["role"], "content": item["content"]} for item in window]]

    def _closed_reply(self, record: dict) -> str:
        if record["language"] == "en":
            return (
                f"Request {record['ticket_id']} is already filed. "
                "Start a new conversation if you want to open another one."
            )
        return (
            f"La consulta {record['ticket_id']} ya está registrada. "
            "Abre una conversación nueva si quieres otra ficha."
        )

    def _reply(self, record, reply, lexicon, now, sentiment_already_set: bool = False) -> dict:
        if lexicon is not None and not sentiment_already_set:
            proposed = combine_sentiment(lexicon, None)
            record["sentiment"] = sticky(record.get("sentiment"), proposed)
        record["summary"] = build_summary(record)
        record["updated_at"] = now
        record["messages"].append({"role": "assistant", "content": reply, "at": now})
        self.store.save(record)
        return self.present(record)

    def present(self, record: dict) -> dict:
        return {
            "id": record["id"],
            "ticket_id": record["ticket_id"],
            "status": record["status"],
            "language": record["language"],
            "sentiment": record["sentiment"],
            "intake": record["intake"],
            "missing": record["missing"],
            "errors": record["errors"],
            "summary": record["summary"],
            "citations": record["citations"],
            "messages": record["messages"],
            "model": record.get("model", self.model_name),
            "created_at": record["created_at"],
            "updated_at": record["updated_at"],
        }
