import json
import threading
from urllib import request

import pytest

from orb_agent.agent import Agent
from orb_agent.extract import extract_fields
from orb_agent.flow import is_pure_confirmation, is_rejection
from orb_agent.knowledge import KnowledgeBase
from orb_agent.ollama_client import LlmError, _object_from_text
from orb_agent.sentiment import combine_sentiment, lexicon_sentiment, sticky
from orb_agent.server import create_server
from orb_agent.storage import ConversationStore
from orb_agent.validation import apply_fields, empty_intake, missing_fields, normalize_field


class ScriptedClient:
    def __init__(self, reply="Gracias, lo anoto.", fields=None, sentiment="neutral", fail=False):
        self.reply = reply
        self.fields = fields or {}
        self.sentiment = sentiment
        self.fail = fail
        self.seen = []

    def complete(self, messages):
        self.seen.append(messages)
        if self.fail:
            raise LlmError("down")
        return {
            "reply": self.reply,
            "language": "es",
            "sentiment": self.sentiment,
            "fields": self.fields,
        }


@pytest.fixture
def agent(tmp_path):
    client = ScriptedClient()
    store = ConversationStore(tmp_path)
    built = Agent(client, store, KnowledgeBase.load(), model_name="scripted")
    built.client = client
    return built


def test_validation_accepts_aliases_and_rejects_bad_email():
    ok, email, _ = normalize_field("contact_email", "Ana.Ruiz@Example.com")
    assert ok and email == "ana.ruiz@example.com"
    ok, _, code = normalize_field("contact_email", "ana@no")
    assert not ok and code == "invalid_email"
    ok, urgency, _ = normalize_field("urgency", "crítica")
    assert ok and urgency == "critical"
    ok, item, _ = normalize_field("item_type", "lámpara")
    assert item == "lamp"
    ok, code_value, _ = normalize_field("reference_code", "1042")
    assert code_value == "ORB-1042"


def test_extract_spanish_intake_and_a_correction():
    found = extract_fields(
        "Hola, soy Ana Ruiz, ana.ruiz@example.com. "
        "Se me rompió la lámpara del pedido ORB-1042 y echa chispas. "
        "Avisadme por la mañana."
    )
    assert found["customer_name"] == "Ana Ruiz"
    assert found["contact_email"] == "ana.ruiz@example.com"
    assert found["reference_code"] == "ORB-1042"
    assert found["item_type"] == "lamp"
    assert found["category"] == "electrical"
    assert found["urgency"] == "critical"
    assert found["preferred_contact"] == "morning"
    assert "lámpara" in found["description"]

    corrected = extract_fields("No es una lámpara, es una silla")
    assert corrected["item_type"] == "furniture"


def test_sentiment_sticks_when_the_customer_was_angry():
    assert lexicon_sentiment("Estoy harta de esperar") == "frustrated"
    assert lexicon_sentiment("Esto es una estafa") == "angry"
    assert combine_sentiment("angry", "calm") == "angry"
    assert sticky("angry", "calm") == "angry"


def test_confirmation_phrases():
    assert is_pure_confirmation("Sí, confirmo los datos.")
    assert is_pure_confirmation("Confirmo los datos de la ficha.")
    assert not is_pure_confirmation("Sí, pero el email es otro@example.com")
    assert is_rejection("No, cambia el nombre")
    assert not is_rejection("Anoche llamé al taller")


def test_knowledge_finds_warranty_in_spanish():
    hits = KnowledgeBase.load().search("¿Cuál es la garantía de la mano de obra?", "es")
    assert hits
    assert hits[0]["id"] == "warranty-es"
    assert KnowledgeBase.load().search("hola", "es") == []


def test_sparks_pull_the_safety_note():
    hits = KnowledgeBase.load().search("La lámpara del pedido ORB-1042 echa chispas", "es")
    assert hits[0]["id"] == "electrical-es"


def test_full_intake_review_and_close(agent, tmp_path):
    started = agent.start()
    result = agent.handle(
        started["id"],
        "Hola, soy Ana Ruiz, ana.ruiz@example.com. "
        "Se me rompió la lámpara del pedido ORB-1042 y echa chispas. "
        "Avisadme por la mañana.",
    )
    assert result["status"] == "review"
    assert result["missing"] == []
    assert result["intake"]["customer_name"] == "Ana Ruiz"
    assert result["intake"]["urgency"] == "critical"
    assert "Ana Ruiz" in result["messages"][-1]["content"]
    assert "Confirma estos datos" in result["messages"][-1]["content"]
    assert "Ana Ruiz" in agent.client.seen[-1][0]["content"]

    closed = agent.handle(result["id"], "Confirmo los datos de la ficha.")
    assert closed["status"] == "closed"
    assert closed["ticket_id"] in closed["messages"][-1]["content"]
    assert "Ana Ruiz" in closed["summary"]
    saved = json.loads((tmp_path / f"{closed['id']}.json").read_text(encoding="utf-8"))
    assert saved["status"] == "closed"
    assert saved["intake"]["contact_email"] == "ana.ruiz@example.com"


def test_invalid_model_email_is_not_stored(agent):
    agent.client.fields = {"contact_email": "no-es-un-email", "customer_name": "Ana Ruiz"}
    started = agent.start()
    result = agent.handle(started["id"], "Quiero restaurar una pieza")
    assert result["intake"]["contact_email"] is None
    assert result["intake"]["customer_name"] == "Ana Ruiz"
    assert any(item["code"] == "invalid_email" for item in result["errors"])
    assert "email" in result["messages"][-1]["content"].lower()


def test_ollama_outage_still_asks_for_the_next_fact(agent):
    agent.client.fail = True
    started = agent.start()
    result = agent.handle(started["id"], "Hola, se me rompió la lámpara")
    assert result["status"] == "collecting"
    assert "¿Cómo te llamas?" in result["messages"][-1]["content"]
    assert result["intake"]["item_type"] == "lamp"


def test_english_turn_and_rag_note(agent):
    agent.client.reply = "Thanks, I have noted that."
    started = agent.start()
    result = agent.handle(started["id"], "What is the warranty on the labour?")
    text = result["messages"][-1]["content"]
    assert "12 months" in text
    assert result["language"] == "en"
    assert "What is your name?" in text


def test_memory_keeps_facts_outside_the_window(agent):
    started = agent.start()
    agent.handle(
        started["id"],
        "Soy Ana Ruiz, ana.ruiz@example.com. Se me rompió la lámpara y echa chispas.",
    )
    for index in range(6):
        agent.handle(started["id"], f"sigo con la misma pieza {index}")
    system = agent.client.seen[-1][0]["content"]
    user_turns = [item["content"] for item in agent.client.seen[-1] if item["role"] == "user"]
    assert "Ana Ruiz" in system
    assert all("ana.ruiz" not in turn for turn in user_turns)


def test_rejection_does_not_close(agent):
    started = agent.start()
    review = agent.handle(
        started["id"],
        "Soy Ana Ruiz, ana.ruiz@example.com. Se me rompió la lámpara y echa chispas.",
    )
    assert review["status"] == "review"
    held = agent.handle(review["id"], "No, cambia el nombre")
    assert held["status"] == "collecting"
    assert "no la cierro" in held["messages"][-1]["content"]
    assert held["intake"]["customer_name"] == "Ana Ruiz"


def test_json_parser_reads_object_wrapped_in_text():
    parsed = _object_from_text('Sure\n{"reply":"Hola","fields":{}} trailing')
    assert parsed["reply"] == "Hola"


def test_http_api_roundtrip(agent, tmp_path):
    static = tmp_path / "static"
    static.mkdir()
    (static / "index.html").write_text("<!doctype html><title>orb</title>", encoding="utf-8")
    httpd = create_server(agent, "127.0.0.1", 0, static_dir=static)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    port = httpd.server_address[1]
    try:
        with request.urlopen(f"http://127.0.0.1:{port}/") as response:
            assert response.status == 200
            assert b"orb" in response.read()
        with request.urlopen(f"http://127.0.0.1:{port}/api/health") as response:
            health = json.loads(response.read().decode())
        assert health["ok"] is True
        created_req = request.Request(
            f"http://127.0.0.1:{port}/api/conversations",
            data=b"{}",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with request.urlopen(created_req) as response:
            created = json.loads(response.read().decode())
        message_req = request.Request(
            f"http://127.0.0.1:{port}/api/conversations/{created['id']}/messages",
            data=json.dumps({"text": "Soy Ana Ruiz y se me rompió la lámpara"}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with request.urlopen(message_req) as response:
            updated = json.loads(response.read().decode())
        assert updated["intake"]["customer_name"] == "Ana Ruiz"
        empty_req = request.Request(
            f"http://127.0.0.1:{port}/api/conversations/{created['id']}/messages",
            data=json.dumps({"text": "   "}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with pytest.raises(Exception) as caught:
            request.urlopen(empty_req)
        assert "400" in str(caught.value)
    finally:
        httpd.shutdown()
        thread.join(timeout=3)


def test_missing_fields_require_one_contact():
    intake = empty_intake()
    assert "contact" in missing_fields(intake)
    apply_fields(intake, {"contact_phone": "600 111 222"})
    assert "contact" not in missing_fields(intake)
