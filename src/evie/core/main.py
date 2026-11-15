import sys

from evie.utils import config
from evie.core.agent import Agent
from evie.services.voice import tts


def listen() -> str:
    """Wait for Enter, record one utterance, return what was said ('' if nothing)."""
    from evie.services.voice import stt

    input("[Enter to talk] ")
    print("[listening...]")
    try:
        pcm = stt.record()
        text = stt.transcribe(pcm) if pcm else ""
    except stt.SttError as e:
        print(f"[voice] {e}")
        return ""
    if text:
        print(f"You: {text}")
    else:
        lv = stt.last_levels
        print(f"[heard nothing: loudest {lv['loudest']:.0f}, needed {lv['needed']:.0f}. Set EVIE_MIC to pick another mic]")
    return text


def main():
    for stream in (sys.stdout, sys.stderr):  # the Windows console defaults to cp1252 and crashes on e.g. "ə"
        stream.reconfigure(encoding="utf-8", errors="replace")
    agent = Agent()
    voice = "--voice" in sys.argv
    config.SPEAK = config.SPEAK or voice
    if config.SPEAK:
        tts.warm_up()
    print("Evie voice mode: Enter, then speak. Ctrl+C to quit." if voice else "Evie text mode. Ctrl+C to quit.")
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
