from evie.services.voice import tts


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


def test_sentences_play_in_order_even_if_a_later_one_is_ready_first():
    import time

    played = []

    def synth(text, path):
        time.sleep(0.2 if text.startswith("One") else 0)  # first is slowest
        open(path, "wb").write(text.encode())

    tts.speak("One. Two! Three?", synth=synth, play=lambda p: played.append(open(p, "rb").read().decode()))
    assert played == ["One.", "Two!", "Three?"]


def test_a_failing_sentence_stops_speech_and_leaves_no_files(tmp_path):
    import glob
    import pytest
    import tempfile

    before = set(glob.glob(tempfile.gettempdir() + "/*.mp3"))

    def synth(text, path):
        if text == "Two.":
            raise OSError
        open(path, "wb").write(b"x")

    with pytest.raises(tts.TtsError):
        tts.speak("One. Two. Three.", synth=synth, play=lambda p: None)
    assert set(glob.glob(tempfile.gettempdir() + "/*.mp3")) == before


def test_empty_text_says_nothing():
    tts.speak("🔥", synth=lambda *a: (_ for _ in ()).throw(AssertionError), play=lambda *a: None)


def test_synth_failure_is_speakable():
    import pytest

    def boom(t, p):
        raise OSError

    with pytest.raises(tts.TtsError):
        tts.speak("hello", synth=boom, play=lambda p: None)
