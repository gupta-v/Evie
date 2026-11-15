import sys

from evie import config
from evie.core.agent import Agent
from evie.services import tts


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
            reply = agent.respond(line)
            print(reply)
            if config.SPEAK:
                try:
                    tts.speak(reply)
                except tts.TtsError as e:
                    print(f"[voice] {e}")


if __name__ == "__main__":
    main()
