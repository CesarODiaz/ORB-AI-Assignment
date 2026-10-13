"""Local HTTP server. GitHub Pages serves the same files without these routes."""

import json
import re
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from orb_agent.config import STATIC_DIR


class AgentHandler(SimpleHTTPRequestHandler):
    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, fmt: str, *args) -> None:
        print(f"[orb] {self.address_string()} {fmt % args}")

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/health":
            health = getattr(self.server.agent.client, "health", None)
            online = bool(health()) if health else False
            self._send(200, {"ok": True, "ollama": online, "model": self.server.agent.model_name})
            return
        if path == "/api/conversations":
            self._send(200, {"conversations": self.server.agent.list_conversations()})
            return
        match = re.fullmatch(r"/api/conversations/([A-Za-z0-9]+)", path)
        if match:
            try:
                self._send(200, self.server.agent.get(match.group(1)))
            except KeyError:
                self._send(404, {"error": "Conversation not found."})
            return
        if path.startswith("/api/"):
            self._send(404, {"error": "Route not found."})
            return
        super().do_GET()

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/conversations":
            self._send(201, self.server.agent.start())
            return
        match = re.fullmatch(r"/api/conversations/([A-Za-z0-9]+)/messages", path)
        if not match:
            self._send(404, {"error": "Route not found."})
            return
        try:
            payload = self._read_json()
            result = self.server.agent.handle(match.group(1), str(payload.get("text", "")))
        except ValueError:
            self._send(400, {"error": "Write a message before sending."})
        except KeyError:
            self._send(404, {"error": "Conversation not found."})
        except json.JSONDecodeError:
            self._send(400, {"error": "The body must be JSON."})
        else:
            self._send(200, result)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length > 20_000:
            raise ValueError("body too large")
        raw = self.rfile.read(length).decode("utf-8") if length else ""
        if not raw:
            return {}
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValueError("json object required")
        return data

    def _send(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def create_server(agent, host: str = "127.0.0.1", port: int = 8765, static_dir=STATIC_DIR):
    handler = partial(AgentHandler, directory=str(static_dir))
    httpd = ThreadingHTTPServer((host, port), handler)
    httpd.agent = agent
    return httpd
