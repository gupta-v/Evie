import sys

from evie.utils import config
from evie.core.agent import Agent
from evie.services.voice import tts


_last_error: list[str | None] = [None]


def listen() -> str:
    """Wait (no key press) until speech starts, record it, return what was said ('' if it was noise)."""
    from evie.services.voice import stt

    print("[listening...]", flush=True)
    try:
        pcm = stt.record(wait_seconds=None)
        text = stt.transcribe(pcm) if pcm else ""
    except stt.SttError as e:
        if str(e) != _last_error[0]:  # the loop retries (reopening the mic): say each problem once
            print(f"[voice] {e}")
        _last_error[0] = str(e)
        return ""
    _last_error[0] = None
    if text:
        print(f"You: {text}", flush=True)
    return text


def say(agent: Agent, line: str) -> None:
    """Send `line` to the brain and show and speak the reply while it is still being written."""
    speaker = tts.Speaker() if config.SPEAK else None
    print("Evie: ", end="", flush=True)
    for piece in agent.stream(line):
        print(piece, end="", flush=True)
        if speaker:
            speaker.feed(piece)
    print(flush=True)
    if speaker:
        try:
            speaker.finish()
        except tts.TtsError as e:
            print(f"[voice] {e}", flush=True)


def main():
    for stream in (sys.stdout, sys.stderr):  # the Windows console defaults to cp1252 and crashes on e.g. "ə"
        stream.reconfigure(encoding="utf-8", errors="replace")
    agent = Agent()
    voice = "--voice" in sys.argv
    config.SPEAK = config.SPEAK or voice
    if config.SPEAK:
        tts.warm_up()
    if voice:
        from evie.services.voice import stt

        stt.warm_up()
    print("Evie voice mode: just talk. Ctrl+C to quit." if voice else "Evie text mode. Ctrl+C to quit.")
    while True:
        try:
            line = listen() if voice else input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if line:
            say(agent, line)


if __name__ == "__main__":
    main()
