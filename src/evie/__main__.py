from evie.core.agent import Agent


def main():
    agent = Agent()
    print("Evie text mode. Ctrl+C to quit.")
    while True:
        try:
            line = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if line:
            print(agent.respond(line))


if __name__ == "__main__":
    main()
