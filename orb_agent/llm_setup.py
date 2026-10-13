"""Install and configure the same local model on every machine.

Running ``pip install -r requirements.txt`` calls this once. Starting the
agent calls it again, so a copied folder still ends up with the model ready.
"""

import json
import os
import platform
import shutil
import subprocess
import time
from pathlib import Path
from urllib import error, request

from orb_agent.config import OLLAMA_HOST, ROOT

PINNED_MODEL = "llama3.2:3b"
MODEL_FAMILY = "llama3.2"
CONFIG_PATH = ROOT / "data" / "llm.json"


def select_model(names: list[str]) -> str | None:
    """Prefer the pinned tag. Any already installed llama3.2 build is enough."""
    if PINNED_MODEL in names:
        return PINNED_MODEL
    for name in names:
        family = name.split("@", 1)[0].split(":", 1)[0]
        if family == MODEL_FAMILY:
            return name
    return None


def load_llm_config() -> dict:
    if CONFIG_PATH.exists():
        try:
            saved = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            saved = {}
        host = saved.get("host")
        model = saved.get("model")
        if host and model:
            return {"provider": "ollama", "host": host, "model": model}
    return {"provider": "ollama", "host": OLLAMA_HOST, "model": PINNED_MODEL}


def _api_models(host: str) -> list[str] | None:
    try:
        with request.urlopen(f"{host}/api/tags", timeout=3) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (error.URLError, TimeoutError, OSError, json.JSONDecodeError):
        return None
    return [item["name"] for item in payload.get("models", []) if item.get("name")]


def _write_config(host: str, model: str) -> dict:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    record = {"provider": "ollama", "host": host, "model": model}
    temporary = CONFIG_PATH.with_suffix(".tmp")
    temporary.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, CONFIG_PATH)
    return record


def _say(message: str) -> None:
    """pip hides build output. The terminal still shows the install progress."""
    try:
        stream = open("/dev/tty", "w", buffering=1)
    except OSError:
        print(message, flush=True)
        return
    print(message, file=stream, flush=True)
    stream.close()


def _run_visible(cmd, *, shell: bool = False, check: bool = True) -> subprocess.CompletedProcess:
    try:
        stream = open("/dev/tty", "w", buffering=1)
    except OSError:
        stream = None
    try:
        return subprocess.run(cmd, shell=shell, check=check, stdout=stream, stderr=stream)
    finally:
        if stream is not None:
            stream.close()


def install_ollama() -> str:
    if platform.system().lower() == "windows":
        raise SystemExit(
            "Install Ollama from https://ollama.com/download and run "
            "pip install -r requirements.txt again"
        )
    _say("Ollama is not installed. Using the official installer...")
    completed = _run_visible("curl -fsSL https://ollama.com/install.sh | sh", shell=True, check=False)
    if completed.returncode != 0:
        raise SystemExit(
            "Could not install Ollama. Install it from https://ollama.com/download "
            "and run pip install -r requirements.txt again"
        )
    binary = shutil.which("ollama")
    if binary:
        return binary
    for candidate in ("/usr/local/bin/ollama", "/usr/bin/ollama"):
        if Path(candidate).exists():
            return candidate
    raise SystemExit("The installer finished, but the ollama command is missing.")


def _start_server(binary: str) -> None:
    _say("Starting Ollama in the background.")
    subprocess.Popen(
        [binary, "serve"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


def _wait_for_models(host: str, attempts: int = 30) -> list[str]:
    for _ in range(attempts):
        models = _api_models(host)
        if models is not None:
            return models
        time.sleep(1)
    raise SystemExit(f"Ollama did not respond at {host}.")


def ensure_llm() -> dict:
    """Make sure Ollama is running and llama3.2 is present, then save that choice."""
    host = os.environ.get("OLLAMA_HOST", OLLAMA_HOST).rstrip("/")
    binary = shutil.which("ollama") or install_ollama()
    models = _api_models(host)
    if models is None:
        _start_server(binary)
        models = _wait_for_models(host)
    chosen = select_model(models)
    if chosen is None:
        _say(f"Downloading {PINNED_MODEL}. The first download can take a while.")
        _run_visible([binary, "pull", PINNED_MODEL])
        chosen = PINNED_MODEL
    else:
        _say(f"Local model ready: {chosen}")
    return _write_config(host, chosen)


def main() -> None:
    if os.environ.get("ORB_SKIP_LLM_SETUP") == "1":
        print("Model setup skipped (ORB_SKIP_LLM_SETUP=1).")
        return
    record = ensure_llm()
    _say(f"Configured {record['model']} at {record['host']}")
    _say(f"Saved to {CONFIG_PATH}")


if __name__ == "__main__":
    main()
