import pytest

import evie.tools  # noqa: F401
from evie import config
from evie.core import registry
from evie.core.agent import Agent
from evie.services import library, tui_input
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


# --- online search is termusic's own 's' feature, typed into its window ---

@pytest.fixture
def keys(monkeypatch):
    """No real keys are ever sent: records what would be typed and which process gets it."""
    sent = []
    monkeypatch.setattr(tui_input, "tui_pids", lambda: [111, 222])
    monkeypatch.setattr(tui_input.console_input, "send_keys", lambda pid, k, pause_after_first=0: sent.append((pid, k)))
    monkeypatch.setattr(music.watcher, "watch_new_song", lambda cb: sent.append(("watching", cb)))
    return sent


def test_search_online_types_into_newest_tui_in_background_and_starts_watching(wired, keys):
    out = registry.call("music_search_online", {"query": "hola amigo"})
    assert keys[0] == (222, ["s", *"hola amigo", "<enter>"])  # no window focus involved
    assert keys[1][0] == "watching" and "Opened termusic's YouTube search" in out


def test_search_online_reports_no_tui(wired, monkeypatch):
    monkeypatch.setattr(tui_input, "tui_pids", lambda: [])
    assert "can't find the termusic window" in registry.call("music_search_online", {"query": "x"})


def test_search_online_reports_typing_failure_without_starting_a_watch(wired, monkeypatch):
    def boom(pid, k, pause_after_first=0):
        raise RuntimeError("cannot attach")

    monkeypatch.setattr(tui_input, "tui_pids", lambda: [5])
    monkeypatch.setattr(tui_input.console_input, "send_keys", boom)
    monkeypatch.setattr(music.watcher, "watch_new_song", lambda cb: pytest.fail("must not watch"))
    out = registry.call("music_search_online", {"query": "x"})
    assert "couldn't type into termusic" in out and "cannot attach" in out


def test_downloaded_song_is_queued_and_played(lib, wired, monkeypatch):
    said = []
    monkeypatch.setattr(music, "_announce", said.append)
    song = lib / "Hola Amigo.mp3"
    song.write_bytes(b"x")
    music._on_downloaded(song)
    assert len(wired.tracks) == 1 and "PlaySpecific:0" in wired.calls
    assert said == ["Downloaded Hola Amigo. playing"]


# --- approval gate: any write tool needs the user's yes ---

RAN = []


@registry.tool(name="_t_danger", risk="write")
def _danger(what: str) -> str:
    """Test write tool.

    Args:
        what: anything
    """
    RAN.append(what)
    return f"did {what}"


class FakeProvider:
    """Scripted model: 'go' calls the write tool, anything else just echoes."""

    def __init__(self):
        self.seen = []

    def respond(self, text):
        self.seen.append(text)
        if text == "go":
            registry.call("_t_danger", {"what": "thing"})
            return "Do the thing? Say yes."
        return "ok"


@pytest.fixture
def agent():
    RAN.clear()
    a = Agent.__new__(Agent)
    a.provider, a.pending = FakeProvider(), None
    return a


def test_write_is_blocked_until_user_says_yes(agent):
    assert agent.respond("go") == "Do the thing? Say yes."
    assert agent.pending == ("_t_danger", {"what": "thing"}) and RAN == []
    agent.respond("yes please")
    assert RAN == ["thing"]
    assert "Result of _t_danger: did thing" in agent.provider.seen[-1] and agent.pending is None


def test_user_no_discards_pending_and_never_runs_it(agent):
    agent.respond("go")
    agent.respond("no thanks")
    assert agent.pending is None and RAN == []
    assert agent.provider.seen[-1].startswith("The user declined")


def test_unrelated_reply_drops_pending(agent):
    agent.respond("go")
    agent.respond("what time is it")
    assert agent.pending is None and RAN == []
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
