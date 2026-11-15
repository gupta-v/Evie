import sys
import time

from evie.utils import config
from evie.core.agent import Agent
from evie.services.voice import tts


_last_error: list[str | None] = [None]


def listen() -> str:
    """Wait (no key press) until speech starts, record it, return what was said ('' if it was noise).
    Prints each stage as it happens: listening, listening done, how long speech-to-text took, then the words."""
    from evie.services.voice import stt

    print("[listening...]", flush=True)
    try:
        pcm = stt.record(wait_seconds=None)
        if not pcm:
            return ""
        print("[listening done]", flush=True)
        started = time.monotonic()
        text = stt.transcribe(pcm)
    except stt.SttError as e:
        if str(e) != _last_error[0]:  # the loop retries (reopening the mic): say each problem once
            print(f"[voice] {e}", flush=True)
        _last_error[0] = str(e)
        return ""
    _last_error[0] = None
    print(f"  [speech-to-text {time.monotonic() - started:.2f}s]", flush=True)
    if text:
        print(f"You: {text}", flush=True)
    return text


def say(agent: Agent, line: str, timed: bool = False) -> None:
    """Send `line` to the brain and show and speak the reply while it is still being written.
    `timed` prints how long the brain took to start answering."""
    speaker = tts.Speaker() if config.SPEAK else None
    started, first = time.monotonic(), True
    for piece in agent.stream(line):
        if first:
            if timed:
                print(f"  [brain {time.monotonic() - started:.2f}s]", flush=True)
            print("Evie: ", end="", flush=True)
            first = False
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
            say(agent, line, timed=voice)


if __name__ == "__main__":
    main()
