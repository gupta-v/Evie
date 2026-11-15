import pytest

from evie.services.music import library


@pytest.fixture
def lib(tmp_path):
    for name in ("Husn - Anuv Jain.flac", "Jo Tum Mere Ho - Anuv Jain.mp3", "Tum Se - Sachin-Jigar, Raghav Chaitanya.opus"):
        (tmp_path / name).write_bytes(b"x")
    library._names_cache.clear()
    return tmp_path


@pytest.mark.parametrize("heard,want", [
    ("Play Anubjain", "Play Anuv Jain"),
    ("Can you search something from Anup Jain?", "Can you search something from Anuv Jain?"),
    ("Le Jyotum Mereho", "Jo Tum Mere Ho"),
    ("play anuv jain", "play Anuv Jain"),
])
def test_near_miss_names_snap_to_the_librarys_spelling(lib, heard, want):
    assert library.correct(heard, lib) == want


@pytest.mark.parametrize("heard", [
    "What's the weather in Kolhapur?", "Hey Evie, how are you?", "next song please", "Watch the weather now.",
])
def test_ordinary_sentences_are_left_alone(lib, heard):
    assert library.correct(heard, lib) == heard
