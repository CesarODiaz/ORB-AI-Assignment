"""Talk to Mara from the terminal: python -m orb_agent"""

from orb_agent.factory import build_agent
from orb_agent.llm_setup import ensure_llm


def main() -> None:
    configured = ensure_llm()
    agent = build_agent(model=configured["model"], host=configured["host"])
    current = agent.start()
    print(current["messages"][-1]["content"])
    print("\nCommands: /new, /quit\n")
    while True:
        try:
            text = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not text:
            continue
        if text in {"/quit", "/exit", "/salir"}:
            break
        if text in {"/new", "/nueva"}:
            current = agent.start()
            print(f"\nMara: {current['messages'][-1]['content']}\n")
            continue
        current = agent.handle(current["id"], text)
        print(f"\nMara: {current['messages'][-1]['content']}\n")
        if current["status"] == "closed":
            print(f"Summary: {current['summary']}")
            print(f"Saved to data/conversations/{current['id']}.json\n")


if __name__ == "__main__":
    main()
