"""Run the local workshop desk: python serve.py"""

import argparse
import os

from orb_agent.config import DEFAULT_MODEL, DEFAULT_PORT, OLLAMA_HOST
from orb_agent.factory import build_agent
from orb_agent.server import create_server


def main() -> None:
    parser = argparse.ArgumentParser(description="ORB Atelier local agent")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=int(os.environ.get("AGENT_PORT", DEFAULT_PORT)))
    parser.add_argument("--model", default=os.environ.get("OLLAMA_MODEL", DEFAULT_MODEL))
    parser.add_argument("--ollama", default=os.environ.get("OLLAMA_HOST", OLLAMA_HOST))
    args = parser.parse_args()
    agent = build_agent(model=args.model, host=args.ollama)
    httpd = create_server(agent, host=args.host, port=args.port)
    print(f"Mesa de ORB Atelier: http://{args.host}:{args.port}")
    print(f"Modelo: {args.model} en {args.ollama}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nCerrado.")
        httpd.server_close()


if __name__ == "__main__":
    main()
