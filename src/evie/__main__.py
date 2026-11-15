import sys

from evie.core.agent import Agent


def main():
    for stream in (sys.stdout, sys.stderr):  # the Windows console defaults to cp1252 and crashes on e.g. "ə"
        stream.reconfigure(encoding="utf-8", errors="replace")
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
