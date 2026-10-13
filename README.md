# ORB Atelier

Mara is the intake assistant for **ORB Atelier**, a fictional restoration workshop in Valencia. She interviews a customer, fills a structured ticket, and files it only after the customer confirms the facts.

The model runs on your machine through [Ollama](https://ollama.com). The same interface can be published on GitHub Pages as a static example, because Pages cannot run Python or a local model.

## Quick start

`pip install -r requirements.txt` installs the project and prepares the same local model on every machine: Ollama and `llama3.2:3b`. An existing `llama3.2` is reused. The choice is saved in `data/llm.json`.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
python3 serve.py
```

Open [http://127.0.0.1:8765](http://127.0.0.1:8765). The chat, the ticket, and the JSON download work there. From the terminal, without a browser:

```bash
python3 -m orb_agent
```

The tests use the standard library plus pytest. Set `ORB_SKIP_LLM_SETUP=1` if you need to install the dependencies without downloading the model.

```bash
.venv/bin/pytest
```

## What it collects

Mara keeps a ticket with:

| Field | Required | Notes |
| --- | --- | --- |
| Name | yes | |
| Email or phone | one of them | Checked before it is stored |
| Piece | yes | Lamp, furniture, upholstery, or other |
| Reason | yes | Damage, finish, electrical, parts, scheduling, billing, other |
| Description | yes | The customer's own words |
| Urgency | yes | Low, medium, high, or critical |
| Order number | no | `ORB-` plus 3 to 6 digits |
| Call window | no | Morning, afternoon, evening |

A spark, smoke, or a burning smell is stored as critical and the reply tells the customer to unplug the piece. The interface and the stored values are in English. If a customer writes in Spanish, Mara answers in Spanish.

## System architecture

```
Browser (docs/)
  chat, microphone, speech
        |
        |  only when you run python serve.py
        v
Python agent (orb_agent/)
  language, sentiment, heuristics
  validation, confirmation, summary
  JSON store, lexical notes
        |
        v
Ollama llama3.2 at 127.0.0.1:11434
```

GitHub Pages serves the `docs/` folder and nothing else. On that URL the page loads `sample.json` and shows a finished ticket. `api/health` does not exist there, so the composer stays off and the banner explains how to run Mara locally.

Speech uses the browser. Transcription is the Web Speech API (Chrome). Reading aloud is `speechSynthesis`. Audio is not sent to Ollama or to a third-party speech service. On GitHub Pages the example can still be read aloud; the microphone needs the local server because there is nowhere to send the text.

## Setup

1. `python3 -m venv .venv`
2. `.venv/bin/pip install -r requirements.txt`
3. That install starts Ollama if needed, downloads `llama3.2:3b` when no `llama3.2` is present, and writes `data/llm.json`.
4. `python3 serve.py` and open `http://127.0.0.1:8765`.

Optional environment variables: `OLLAMA_HOST`, `OLLAMA_MODEL`, `AGENT_PORT`.

A turn on a laptop CPU is often under a minute once `llama3.2` is loaded. The first turn after Ollama starts is slower, because the model has to load. The send button counts the seconds. If Ollama is down, Mara still asks for the next missing field and still saves the JSON; she just does not draft a free-form reply.

## Key design decisions

**Python owns the ticket.** llama3.2 writes the reply. Names, emails, phones, categories, and urgency are normalized in code, and a value that fails validation is not stored. The model may fill a blank field. It cannot replace a fact already taken from the customer's message. The confirmation text and the closing summary are generated from the stored JSON, so the customer confirms the file rather than a paraphrase.

**One short model call per turn.** The model is asked for a JSON object (`reply`, `language`, `sentiment`, `fields`) with a small context. A local CPU is the bottleneck, so the greeting, the confirmation, and the closing line do not call the model.

**Memory is the ticket plus a short window.** The model sees the system brief and the last six messages. Facts already stored are repeated in that brief, so an early name or order number survives after the raw turn has scrolled out of the window.

**Notes are retrieved by words, not embeddings.** llama3.2 does not expose an embedding model here, and a second download is not required. Articles in `knowledge/articles.json` are scored by token overlap. High-scoring notes are injected into the prompt. Prices, warranties, and timelines that are not in those notes are not invented; the prompt says the workshop will confirm.

**Sentiment is a lexicon, and frustration sticks.** Words such as "harta" or "estafa" mark the turn. If the model calls an angry customer calm, the lexicon wins. Once the conversation has been frustrated or angry, a later polite "yes" does not wipe that mark.

**Language follows the customer.** Spanish and English share the same ticket schema. The reply language comes from the user's words, not from a toggle.

**Files are the database.** Each conversation is one JSON document under `data/conversations/`, written by replace so a crash does not leave a half file. That is enough for a workshop desk. A larger deployment would keep the same record shape in SQLite or Postgres and put Ollama behind a queue: one CPU model cannot serve many concurrent chats.

## Tests

`tests/test_agent.py` covers validation, extraction, a correction ("it is not a lamp, it is a chair"), sentiment, retrieval, a full confirm-and-save flow, a rejected email, an Ollama outage, English plus the warranty note, memory outside the message window, and the HTTP API. The suite does not call Ollama.

## Publish on GitHub Pages

1. Push this repository to GitHub.
2. Settings → Pages → Build and deployment → Deploy from a branch.
3. Branch `main` (or the branch you use), folder **`/docs`**.
4. Save. The site will be `https://<user>.github.io/<repo>/`.

The published page is the interface plus the example ticket. Visitors do not reach your Ollama. To give someone the live agent, they run `python3 serve.py` on a machine where Ollama is installed.

`docs/.nojekyll` is there so GitHub Pages does not hide files with Jekyll.

## Demo video

Record a short capture of two chats: one that files a complete ticket, and one that asks about the warranty. Upload it and put the URL here.

[DEMO_VIDEO_URL](https://youtu.be/AWcx86yCBuI)

## Possible improvements

- Stream the reply so the first words appear before the model finishes.
- Swap the word-overlap notes for embeddings if a second local model is available.
- Add a real calendar instead of a preferred call window.
- Move the JSON files to a database and serialize access to Ollama with a queue.
- Add French or Catalan by extending the detectors, the questions, and the notes. The ticket schema can stay as it is.
