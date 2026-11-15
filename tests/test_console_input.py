import pytest

from evie.services.console_input import ENTER, key_records


def test_each_key_is_a_down_and_an_up_event():
    ev = key_records(["s"])
    assert [(e[0], e[3]) for e in ev] == [(True, "s"), (False, "s")]


def test_uppercase_and_symbols_carry_shift_and_enter_is_a_return_key():
    h = key_records(["H"])[0]
    assert h[3] == "H" and h[4] & 0x10  # SHIFT_PRESSED
    s = key_records(["s"])[0]
    assert not s[4] & 0x10
    e = key_records([ENTER])[0]
    assert (e[1], e[3]) == (0x0D, "\r")


def test_order_is_preserved_and_multichar_keys_rejected():
    assert [e[3] for e in key_records(["a", "b"]) if e[0]] == ["a", "b"]
    with pytest.raises(ValueError):
        key_records(["ab"])


def test_arrow_and_escape_keys():
    from evie.services.console_input import DOWN, ESC, UP

    down, up, esc = (key_records([k])[0] for k in (DOWN, UP, ESC))
    assert (down[1], up[1], esc[1]) == (0x28, 0x26, 0x1B)
    assert down[4] & 0x100 and up[4] & 0x100  # enhanced-key flag, like a real arrow key
    assert not esc[4]
