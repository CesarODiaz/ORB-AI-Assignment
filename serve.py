"""Run the local workshop desk: python serve.py"""

import argparse
import os

from orb_agent.config import DEFAULT_PORT
from orb_agent.factory import build_agent
from orb_agent.llm_setup import ensure_llm
from orb_agent.server import create_server


def main() -> None:
    configured = ensure_llm()
    parser = argparse.ArgumentParser(description="ORB Atelier local agent")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=int(os.environ.get("AGENT_PORT", DEFAULT_PORT)))
    parser.add_argument("--model", default=None)
    parser.add_argument("--ollama", default=None)
    args = parser.parse_args()
    model = args.model or os.environ.get("OLLAMA_MODEL") or configured["model"]
    ollama_host = args.ollama or os.environ.get("OLLAMA_HOST") or configured["host"]
    agent = build_agent(model=model, host=ollama_host)
    httpd = create_server(agent, host=args.host, port=args.port)
    print(f"ORB Atelier desk: http://{args.host}:{args.port}")
    print(f"Model: {model} at {ollama_host}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nClosed.")
        httpd.server_close()


if __name__ == "__main__":
    main()
