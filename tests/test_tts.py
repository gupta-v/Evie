from evie.services import tts


def test_clean_drops_emoji_and_markdown():
    assert tts.clean("Hey! **stay** warm ❤️ 🔥  tonight") == "Hey! stay warm tonight"


def test_speak_synthesizes_then_plays_then_removes_file(tmp_path):
    seen = {}

    def synth(text, path):
        seen["text"] = text
        open(path, "wb").write(b"x")

    def play(path):
        seen["existed"] = __import__("os").path.exists(path)
        seen["path"] = path

    tts.speak("hi ❤️", synth=synth, play=play)
    assert seen["text"] == "hi" and seen["existed"]
    assert not __import__("os").path.exists(seen["path"])


def test_empty_text_says_nothing():
    tts.speak("🔥", synth=lambda *a: (_ for _ in ()).throw(AssertionError), play=lambda *a: None)


def test_synth_failure_is_speakable():
    import pytest

    def boom(t, p):
        raise OSError

    with pytest.raises(tts.TtsError):
        tts.speak("hello", synth=boom, play=lambda p: None)
