import pytest

from evie.services.text import clean_title, spoken_duration


@pytest.mark.parametrize("raw, clean", [
    # real titles from termusic's search and from the library
    ("KR$NA ft. Seedhe Maut - Hola Amigo | Official Music Video", "KR$NA ft. Seedhe Maut - Hola Amigo"),
    ("Hola Amigo - KR$NA, Seedhe Maut | Lyrics | Lyrical Resort", "Hola Amigo - KR$NA, Seedhe Maut"),
    ("Hola Amigo (8D) || KR$NA, SEEDHE MAUT || DHH 8D", "Hola Amigo (8D)"),
    ("Seedhe Maut x Kr$na - Hola Amigo || Legacy Performance", "Seedhe Maut x Kr$na - Hola Amigo"),
    ("Anuv Jain X Lost Stories - Arz Kiya Hai (Official Video) | Coke Studio Bharat", "Anuv Jain X Lost Stories - Arz Kiya Hai"),
    ("Hola_Amigo_Official_Music_Video", "Hola Amigo"),
    ("Arz_Kiya_Hai_Official_Video_Coke_Studio_Bharat", "Arz Kiya Hai Coke Studio Bharat"),
    ("KR$NA - I Guess ｜ Official Music Video [Qg9LxRHLbAk]", "KR$NA - I Guess"),  # fullwidth bar + id
    ("Shape of You (Official Video)", "Shape of You"),
    # what helps you choose between versions stays
    ("hola amigo - kr$na ft. seedhe maut ( slowed & reverb )", "hola amigo - kr$na ft. seedhe maut ( slowed & reverb )"),
    ("Blinding Lights (feat. The Weeknd) [Remix]", "Blinding Lights (feat. The Weeknd) [Remix]"),
    ("Aadat Se Majboor - Salim–Sulaiman, Benny Dayal", "Aadat Se Majboor - Salim–Sulaiman, Benny Dayal"),
])
def test_clean_title(raw, clean):
    assert clean_title(raw) == clean


def test_a_title_that_is_all_noise_falls_back_to_the_original():
    assert clean_title("Lyrics") == "Lyrics"
    assert clean_title("Official_Music_Video") == "Official Music Video"


def test_spoken_duration():
    assert (spoken_duration("04:03"), spoken_duration("10:07"), spoken_duration("odd")) == ("4:03", "10:07", "odd")
