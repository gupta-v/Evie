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


def test_falls_back_to_the_next_backend(monkeypatch):
    from evie.utils import config

    def broken(text, path):
        raise FileNotFoundError

    def edge(text, path):
        open(path, "wb").write(b"edge")

    monkeypatch.setattr(config, "TTS_ORDER", ["kokoro", "edge"])
    monkeypatch.setattr(tts, "_BACKENDS", {"kokoro": (".wav", broken), "edge": (".mp3", edge)})
    played = []
    tts.speak("Hello there.", play=lambda p: played.append((p[-4:], open(p, "rb").read())))
    assert played == [(".mp3", b"edge")]


def test_all_backends_failing_is_one_speakable_error(monkeypatch):
    import pytest

    from evie.utils import config

    def broken(text, path):
        raise OSError

    monkeypatch.setattr(config, "TTS_ORDER", ["kokoro", "edge"])
    monkeypatch.setattr(tts, "_BACKENDS", {"kokoro": (".wav", broken), "edge": (".mp3", broken)})
    with pytest.raises(tts.TtsError):
        tts.speak("Hello.", play=lambda p: None)


def test_speaker_starts_a_sentence_before_the_reply_is_finished():
    played, order = [], []
    sp = tts.Speaker(synth=lambda t, p: open(p, "wb").write(t.encode()), play=lambda p: played.append(open(p, "rb").read().decode()))
    sp.feed("Hello th")
    sp.feed("ere. How are")
    import time
    time.sleep(0.3)
    assert played == ["Hello there."]          # spoken while "How are you?" has not been written yet
    sp.feed(" you?")
    sp.finish()
    assert played == ["Hello there.", "How are you?"]


def test_a_long_unfinished_sentence_starts_at_its_first_comma():
    played = []
    sp = tts.Speaker(synth=lambda t, p: open(p, "wb").write(t.encode()), play=lambda p: played.append(open(p, "rb").read().decode()))
    sp.feed("Coffee beans are actually seeds inside bright red berries, and in old Constantinople it was a reason for divorce")
    import time
    time.sleep(0.3)
    assert played == ["Coffee beans are actually seeds inside bright red berries,"]
    sp.finish()
    assert played[1] == "and in old Constantinople it was a reason for divorce"
