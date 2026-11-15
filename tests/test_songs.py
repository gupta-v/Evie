import json
import subprocess

import pytest

import evie.tools  # noqa: F401
from evie import config
from evie.core import registry
from evie.core.agent import Agent
from evie.services import library, online
from evie.services.termusic import Termusic
from evie.tools import music

FILES = [
    "Aadat Se Majboor - Salim–Sulaiman, Benny Dayal.flac",
    "1985 - Bo Burnham.flac",
    "Aai Paapi - Neeraj Shridhar, Pritam.flac",
    "Blinding Lights - The Weeknd.opus",
    "Blinding Lights (Remix) - The Weeknd.opus",
    "notes.txt",
]


@pytest.fixture
def lib(tmp_path, monkeypatch):
    for f in FILES:
        (tmp_path / f).write_bytes(b"x")
    monkeypatch.setattr(config, "MUSIC_DIR", tmp_path)
    return tmp_path


@pytest.fixture
def wired(player):
    music.set_client(player.client)
    yield player
    music.set_client(None)


# --- library search ---

def test_library_ignores_non_audio_and_finds_by_words(lib):
    assert len(library.scan(lib)) == 5
    top = library.search("aadat se majboor", lib)[0]
    assert top.hit == 1.0 and top.title.startswith("Aadat Se Majboor")


def test_library_has_no_full_match_for_a_song_that_is_not_there(lib):
    # "i guess" must not match every file just because of a stray word
    assert [m for m in library.search("i guess", lib) if m.hit == 1.0] == []


def test_one_letter_words_do_not_create_close_matches(lib):
    (lib / "I Will Survive - Demi Lovato.flac").write_bytes(b"x")
    assert library.search("i guess", lib) == []  # only "i" overlaps, which says nothing
    assert library.search("i will survive", lib)[0].hit == 1.0


def test_library_prefers_tighter_title(lib):
    hits = library.search("blinding lights", lib)
    assert [h.hit for h in hits] == [1.0, 1.0]
    assert hits[0].title == "Blinding Lights - The Weeknd"


# --- play by name ---

def test_play_song_adds_to_queue_and_plays_it(lib, wired):
    out = registry.call("music_play_song", {"name": "bo burnham 1985"})
    assert out.startswith("playing") and "1985 - Bo Burnham" in out
    assert len(wired.tracks) == 1 and "PlaySpecific:0" in wired.calls


def test_play_song_reuses_track_already_in_queue(lib, wired):
    registry.call("music_play_song", {"name": "bo burnham 1985"})
    registry.call("music_play_song", {"name": "bo burnham 1985"})
    assert len(wired.tracks) == 1


def test_play_song_not_found_says_so_and_offers_search(lib, wired):
    out = registry.call("music_play_song", {"name": "i guess"})
    assert "No song matching 'i guess'" in out and "search online" in out
    assert wired.tracks == [] and wired.calls == []  # nothing queued, nothing played


def test_play_song_with_several_matches_asks_which(lib, wired):
    out = registry.call("music_play_song", {"name": "blinding lights weeknd"})
    assert "Several songs match" in out and "1." in out and "2." in out
    assert wired.calls == []


# --- online ---

def _fake_run(stdout="", code=0):
    def run(cmd, **kw):
        run.cmd = cmd
        return subprocess.CompletedProcess(cmd, code, stdout, "")
    return run


def test_online_search_parses_results_and_uses_argv_not_shell(monkeypatch):
    monkeypatch.setattr(online.shutil, "which", lambda n: "yt-dlp")
    line = json.dumps({"id": "abc", "title": "I Guess", "channel": "Artist", "duration": 201})
    run = _fake_run(line + "\nnot json\n")
    res = online.search("i guess; rm -rf /", run=run)
    assert res == [{"title": "I Guess", "channel": "Artist", "seconds": 201, "url": "https://www.youtube.com/watch?v=abc"}]
    assert isinstance(run.cmd, list) and "ytsearch5:i guess; rm -rf /" in run.cmd  # one argv item, no shell


def test_download_rejects_non_youtube_and_option_like_urls(tmp_path):
    for bad in ("https://evil.example/x", "--exec=calc", "file:///c:/x", "http://youtube.com/watch?v=1"):
        with pytest.raises(online.OnlineError):
            online.download(bad, tmp_path)


def test_download_returns_file_path_and_separates_url(monkeypatch, tmp_path):
    monkeypatch.setattr(online.shutil, "which", lambda n: "yt-dlp")
    run = _fake_run(str(tmp_path / "I Guess [abc].opus") + "\n")
    path = online.download("https://www.youtube.com/watch?v=abc", tmp_path, run=run)
    assert path.name == "I Guess [abc].opus"
    assert run.cmd[-2:] == ["--", "https://www.youtube.com/watch?v=abc"]


def test_search_tool_formats_options(monkeypatch):
    monkeypatch.setattr(online, "search", lambda q: [{"title": "I Guess", "channel": "A", "seconds": 125, "url": "https://www.youtube.com/watch?v=abc"}])
    out = registry.call("music_search_online", {"query": "i guess"})
    assert out.startswith("1. I Guess by A (2:05) https://")


# --- approval gate: download needs the user's yes ---

class FakeProvider:
    """Scripted model: first turn calls the write tool, later turns just echo."""

    def __init__(self):
        self.seen = []

    def respond(self, text):
        self.seen.append(text)
        if text == "get it":
            registry.call("music_download", {"url": "https://www.youtube.com/watch?v=abc", "title": "I Guess"})
            return "Download I Guess? Say yes."
        return "ok"


@pytest.fixture
def agent(monkeypatch, lib, wired):
    a = Agent.__new__(Agent)
    a.provider, a.pending = FakeProvider(), None
    monkeypatch.setattr(online.shutil, "which", lambda n: "yt-dlp")
    monkeypatch.setattr(online.subprocess, "run", _fake_run(str(lib / "I Guess [abc].opus") + "\n"))
    (lib / "I Guess [abc].opus").write_bytes(b"x")
    return a


def test_download_is_blocked_until_user_says_yes(agent, lib):
    assert agent.respond("get it") == "Download I Guess? Say yes."
    assert agent.pending and agent.pending[0] == "music_download"
    agent.respond("yes please")
    assert "Result of music_download: downloaded I Guess [abc]" in agent.provider.seen[-1]
    assert agent.pending is None


def test_user_no_discards_pending_and_never_downloads(agent):
    agent.respond("get it")
    agent.respond("no thanks")
    assert agent.pending is None
    assert agent.provider.seen[-1].startswith("The user declined")


def test_unrelated_reply_drops_pending(agent):
    agent.respond("get it")
    agent.respond("what time is it")
    assert agent.pending is None
    assert agent.provider.seen[-1] == "what time is it"


# --- add by name, and never report an add that did not happen ---

def test_queue_song_adds_without_playing(lib, wired):
    out = registry.call("music_queue_song", {"name": "bo burnham 1985"})
    assert out == "added to the queue: 1985 - Bo Burnham"
    assert len(wired.tracks) == 1 and wired.calls == []  # nothing played
    assert registry.call("music_queue_song", {"name": "bo burnham 1985"}).startswith("already in the queue")
    assert len(wired.tracks) == 1


def test_queue_song_not_in_library_adds_nothing_and_offers_search(lib, wired):
    out = registry.call("music_queue_song", {"name": "arz kiya hai"})
    assert "No song matching" in out and "search online" in out
    assert wired.tracks == []


def test_music_add_rejects_a_song_name(lib, wired):
    out = registry.call("music_add", {"source": "arz kiya hai"})
    assert "not a file or link" in out and wired.tracks == []


def test_client_add_errors_when_server_silently_ignores_the_track(player):
    player.ignore_adds = True
    with pytest.raises(Exception, match="didn't accept"):
        player.client.add("C:/nope/missing.mp3")


def test_underscored_file_names_match_spaced_queries(lib):
    # real library has yt-dlp style names: Arz_Kiya_Hai_Official_Video_Coke_Studio_Bharat.opus
    (lib / "Arz_Kiya_Hai_Official_Video_Coke_Studio_Bharat.opus").write_bytes(b"x")
    top = library.search("arz kiya hai", lib)[0]
    assert top.hit == 1.0 and top.title.startswith("Arz_Kiya_Hai")
