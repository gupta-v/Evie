from pathlib import Path

from evie.services import watcher


class World:
    """Fake folder: `files` maps path -> list of sizes over successive polls (last one repeats)."""

    def __init__(self, files):
        self.files, self.polls = files, 0

    def scan(self):
        return [Path(p) for p, sizes in self.files.items() if sizes]

    def size(self, p):
        sizes = self.files[str(p)]
        return sizes[min(self.polls, len(sizes) - 1)]


def run_watch(world, monkeypatch, timeout=300.0, **kw):
    found, ticks = [], [0.0]
    monkeypatch.setattr(Path, "stat", lambda self: type("S", (), {"st_size": world.size(self)})())

    def sleep(s):
        ticks[0] += s
        world.polls += 1

    t = watcher.watch_new_song(found.append, scan=world.scan, sleep=sleep, clock=lambda: ticks[0], timeout=timeout, **kw)
    t.join(5)
    return found


def test_fires_for_a_new_file_once_its_size_stops_changing(monkeypatch):
    world = World({"old.mp3": [10], "new.mp3": [0, 100, 500, 900, 900, 900, 900, 900]})
    # old.mp3 existed before the watch started, so only new.mp3 can fire
    world.files_before = None
    found = []
    ticks = [0.0]
    monkeypatch.setattr(Path, "stat", lambda self: type("S", (), {"st_size": world.size(self)})())
    snapshot = [Path("old.mp3")]
    calls = {"n": 0}

    def scan():
        calls["n"] += 1
        return snapshot if calls["n"] == 1 else world.scan()  # first call is the "before" snapshot

    def sleep(s):
        ticks[0] += s
        world.polls += 1

    watcher.watch_new_song(found.append, scan=scan, sleep=sleep, clock=lambda: ticks[0]).join(5)
    assert found == [Path("new.mp3")]


def test_ignores_a_file_that_vanishes_like_a_converted_intermediate(monkeypatch):
    # clip.m4a is stable for two polls, then deleted (yt-dlp converted it); clip.mp3 is the real result
    world = World({"clip.m4a": [50, 50, 50, -1, -1, -1, -1, -1], "clip.mp3": [0, 0, 0, 0, 70, 70, 70, 70, 70]})
    found = []
    ticks = [0.0]
    monkeypatch.setattr(Path, "stat", lambda self: type("S", (), {"st_size": world.size(self)})())
    first = {"done": False}

    def scan():
        if not first["done"]:
            first["done"] = True
            return []  # nothing before
        return [Path(p) for p in world.files]

    def sleep(s):
        ticks[0] += s
        world.polls += 1

    watcher.watch_new_song(found.append, scan=scan, sleep=sleep, clock=lambda: ticks[0]).join(5)
    assert found == [Path("clip.mp3")]


def test_gives_up_quietly_after_timeout(monkeypatch):
    world = World({})
    assert run_watch(world, monkeypatch, timeout=10.0) == []


def test_new_watch_cancels_the_previous_one(monkeypatch):
    first_found, second_found = [], []
    t1 = watcher.watch_new_song(first_found.append, scan=lambda: [], sleep=lambda s: __import__("time").sleep(0.01), clock=__import__("time").monotonic, timeout=5)
    t2 = watcher.watch_new_song(second_found.append, scan=lambda: [], sleep=lambda s: None, clock=lambda: 1e9, timeout=1)
    t1.join(3)
    assert not t1.is_alive()  # cancelled long before its 5 s timeout
    t2.join(3)
