"""Ollama chat client. One JSON completion per turn."""

import json
from urllib import error, request

from orb_agent.config import DEFAULT_MODEL, OLLAMA_HOST


class LlmError(RuntimeError):
    pass


def _object_from_text(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
    start = raw.find("{")
    if start == -1:
        raise LlmError("the model did not return JSON")
    try:
        payload, _ = json.JSONDecoder().raw_decode(raw[start:])
    except json.JSONDecodeError as exc:
        raise LlmError("the model returned malformed JSON") from exc
    if not isinstance(payload, dict):
        raise LlmError("the model returned a JSON value that is not an object")
    return payload


class OllamaClient:
    def __init__(self, host: str = OLLAMA_HOST, model: str = DEFAULT_MODEL, timeout: float = 180):
        self.host = host.rstrip("/")
        self.model = model
        self.timeout = timeout

    def health(self) -> bool:
        try:
            with request.urlopen(f"{self.host}/api/tags", timeout=3) as response:
                return response.status == 200
        except (error.URLError, TimeoutError, OSError):
            return False

    def complete(self, messages: list[dict]) -> dict:
        try:
            return self._once(messages)
        except LlmError:
            repair = list(messages) + [
                {
                    "role": "user",
                    "content": (
                        "Reply again as one JSON object with keys reply, language, "
                        "sentiment, and fields. No markdown."
                    ),
                }
            ]
            return self._once(repair)

    def _once(self, messages: list[dict]) -> dict:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "format": "json",
            "keep_alive": "30m",
            "options": {"temperature": 0.2, "num_predict": 140, "num_ctx": 2048},
        }
        body = json.dumps(payload).encode("utf-8")
        call = request.Request(
            f"{self.host}/api/chat",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(call, timeout=self.timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
        except TimeoutError as exc:
            raise LlmError("Ollama took too long to answer") from exc
        except error.URLError as exc:
            raise LlmError("Ollama is not reachable") from exc
        prompt_tokens = data.get("prompt_eval_count") or 0
        answer_tokens = data.get("eval_count") or 0
        prompt_s = (data.get("prompt_eval_duration") or 0) / 1e9
        answer_s = (data.get("eval_duration") or 0) / 1e9
        print(
            f"[orb] {self.model}: {prompt_tokens} context tokens in {prompt_s:.1f}s, "
            f"{answer_tokens} reply tokens in {answer_s:.1f}s"
        )
        content = ((data.get("message") or {}).get("content")) or ""
        parsed = _object_from_text(content)
        if "reply" not in parsed:
            raise LlmError("the model JSON has no reply")
        return parsed
