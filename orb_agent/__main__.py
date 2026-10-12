"""Talk to Mara from the terminal: python -m orb_agent"""

from orb_agent.factory import build_agent


def main() -> None:
    agent = build_agent()
    current = agent.start()
    print(current["messages"][-1]["content"])
    print("\nComandos: /nueva, /salir\n")
    while True:
        try:
            text = input("Tú: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not text:
            continue
        if text in {"/salir", "/quit", "/exit"}:
            break
        if text in {"/nueva", "/new"}:
            current = agent.start()
            print(f"\nMara: {current['messages'][-1]['content']}\n")
            continue
        current = agent.handle(current["id"], text)
        print(f"\nMara: {current['messages'][-1]['content']}\n")
        if current["status"] == "closed":
            print(f"Resumen: {current['summary']}")
            print(f"Guardado en data/conversations/{current['id']}.json\n")


if __name__ == "__main__":
    main()
