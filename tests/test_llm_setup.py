import json

import pytest

from orb_agent.llm_setup import PINNED_MODEL, ensure_llm, select_model


def test_pinned_tag_wins_over_latest():
    assert select_model(["llama3.2:latest", PINNED_MODEL]) == PINNED_MODEL


def test_existing_llama_is_reused():
    assert select_model(["llama3.2:latest"]) == "llama3.2:latest"
    assert select_model(["mistral:latest"]) is None


def test_existing_model_is_configured_without_download(tmp_path, monkeypatch):
    import orb_agent.llm_setup as setup

    monkeypatch.setattr(setup, "CONFIG_PATH", tmp_path / "llm.json")
    monkeypatch.setattr(setup.shutil, "which", lambda _name: "/usr/bin/ollama")
    monkeypatch.setattr(setup, "_api_models", lambda _host: ["llama3.2:latest"])
    monkeypatch.setattr(setup.subprocess, "run", lambda *args, **kwargs: pytest.fail("pull"))

    record = ensure_llm()

    assert record["model"] == "llama3.2:latest"
    assert json.loads((tmp_path / "llm.json").read_text(encoding="utf-8"))["model"] == "llama3.2:latest"


def test_missing_model_is_pulled(tmp_path, monkeypatch):
    import orb_agent.llm_setup as setup

    commands = []
    monkeypatch.setattr(setup, "CONFIG_PATH", tmp_path / "llm.json")
    monkeypatch.setattr(setup.shutil, "which", lambda _name: "/usr/bin/ollama")
    monkeypatch.setattr(setup, "_api_models", lambda _host: [])

    def fake_run(cmd, **kwargs):
        commands.append(cmd)

    monkeypatch.setattr(setup, "_run_visible", fake_run)
    record = ensure_llm()

    assert commands == [["/usr/bin/ollama", "pull", PINNED_MODEL]]
    assert record["model"] == PINNED_MODEL


def test_server_starts_when_ollama_is_down(tmp_path, monkeypatch):
    import orb_agent.llm_setup as setup

    started = []
    monkeypatch.setattr(setup, "CONFIG_PATH", tmp_path / "llm.json")
    monkeypatch.setattr(setup.shutil, "which", lambda _name: "/usr/bin/ollama")
    calls = {"n": 0}

    def api(_host):
        calls["n"] += 1
        if calls["n"] == 1:
            return None
        return ["llama3.2:3b"]

    monkeypatch.setattr(setup, "_api_models", api)
    monkeypatch.setattr(setup, "_start_server", lambda binary: started.append(binary))
    monkeypatch.setattr(setup.subprocess, "run", lambda *args, **kwargs: pytest.fail("pull"))

    record = ensure_llm()

    assert started == ["/usr/bin/ollama"]
    assert record["model"] == "llama3.2:3b"
