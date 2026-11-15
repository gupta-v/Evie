import sys

from evie.utils import config
from evie.core.agent import Agent
from evie.services.voice import tts


def listen() -> str:
    """Wait (no key press) until speech starts, record it, return what was said ('' if it was noise)."""
    from evie.services.voice import stt

    print("[listening...]")
    try:
        pcm = stt.record(wait_seconds=None)
        text = stt.transcribe(pcm) if pcm else ""
    except stt.SttError as e:
        print(f"[voice] {e}")
        return ""
    if text:
        print(f"You: {text}")
    return text


def main():
    for stream in (sys.stdout, sys.stderr):  # the Windows console defaults to cp1252 and crashes on e.g. "ə"
        stream.reconfigure(encoding="utf-8", errors="replace")
    agent = Agent()
    voice = "--voice" in sys.argv
    config.SPEAK = config.SPEAK or voice
    if config.SPEAK:
        tts.warm_up()
    print("Evie voice mode: just talk. Ctrl+C to quit." if voice else "Evie text mode. Ctrl+C to quit.")
    while True:
        try:
            line = listen() if voice else input("> ").strip()
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
