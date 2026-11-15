import subprocess

import pytest

import evie.tools  # noqa: F401
from evie.core import registry
from evie.services import apps
from evie.services.apps import App

START_MENU = [
    App("WhatsApp", "5319275A.WhatsAppDesktop_cv1g1gvanyjgm!App"),
    App("Spotify", r"C:\Users\x\AppData\Roaming\Spotify\Spotify.exe"),
    App("Steam", r"D:\games\Steam\Steam.exe"),
    App("Steam Beta", "SteamBeta.exe"),
    App("Notepad", r"{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\notepad.exe"),
    App("Visual Studio Code", "Microsoft.VSCode"),
    App("Visual Studio Installer", "VSInstaller"),
]


@pytest.fixture
def launched(monkeypatch):
    """Fake Start menu and a fake launcher: nothing real is listed or started."""
    out = []
    monkeypatch.setattr(apps, "_cache", list(START_MENU))
    monkeypatch.setattr(apps.shutil, "which", lambda n: "explorer.exe")
    monkeypatch.setattr(apps.subprocess, "Popen", lambda cmd, **k: out.append(cmd))
    return out


def test_find_matches_all_words_and_prefers_the_tightest_name():
    assert [a.name for a in apps.find("whatsapp", START_MENU)] == ["WhatsApp"]
    assert [a.name for a in apps.find("steam", START_MENU)] == ["Steam", "Steam Beta"]
    assert [a.name for a in apps.find("visual studio code", START_MENU)] == ["Visual Studio Code"]
    assert apps.find("zzz", START_MENU) == []


def test_open_app_launches_through_the_shell_apps_folder(launched):
    assert registry.call("open_app", {"name": "whatsapp"}) == "opening WhatsApp"
    assert launched == [["explorer.exe", r"shell:AppsFolder\5319275A.WhatsAppDesktop_cv1g1gvanyjgm!App"]]


def test_exact_name_wins_over_longer_matches(launched):
    assert registry.call("open_app", {"name": "steam"}) == "opening Steam"
    assert len(launched) == 1


def test_several_matches_are_listed_not_guessed(launched):
    out = registry.call("open_app", {"name": "visual studio"})
    assert "Several apps match" in out and "Visual Studio Code" in out and "Visual Studio Installer" in out
    assert launched == []


def test_unknown_app_says_so_and_starts_nothing(launched):
    assert "No installed app matching 'fortnite'" in registry.call("open_app", {"name": "fortnite"})
    assert launched == []


def test_list_apps_parses_powershell_json_and_drops_web_links(monkeypatch):
    monkeypatch.setattr(apps, "_cache", None)
    monkeypatch.setattr(apps.shutil, "which", lambda n: "powershell")
    rows = '[{"Name":"WhatsApp","AppID":"x!App"},{"Name":"Steam Support Center","AppID":"http://support.steampowered.com/"}]'
    got = apps.list_apps(run=lambda *a, **k: subprocess.CompletedProcess(a, 0, rows, ""))
    assert [a.name for a in got] == ["WhatsApp"]


def test_single_app_json_object_is_handled(monkeypatch):
    monkeypatch.setattr(apps, "_cache", None)  # PowerShell prints one object, not a list, for a single app
    monkeypatch.setattr(apps.shutil, "which", lambda n: "powershell")
    got = apps.list_apps(run=lambda *a, **k: subprocess.CompletedProcess(a, 0, '{"Name":"A","AppID":"b"}', ""))
    assert [a.name for a in got] == ["A"]


@pytest.fixture
def browser(monkeypatch):
    opened = []
    monkeypatch.setattr("evie.tools.apps.webbrowser.open", lambda u: opened.append(u) or True)
    return opened


def test_open_website_uses_the_default_browser(browser):
    assert registry.call("open_website", {"url": "https://mail.google.com"}) == "opening mail.google.com"
    assert browser == ["https://mail.google.com"]


def test_bare_domain_gets_https(browser):
    registry.call("open_website", {"url": "youtube.com"})
    assert browser == ["https://youtube.com"]


@pytest.mark.parametrize("bad", ["file:///c:/windows/system32/cmd.exe", "javascript:alert(1)", "ms-settings:network", "ftp://x.org/f", "https://"])
def test_open_website_refuses_anything_but_http_urls(browser, bad):
    assert "isn't a web address" in registry.call("open_website", {"url": bad})
    assert browser == []


def test_bare_domains_with_paths_get_https_but_junk_does_not(browser):
    registry.call("open_website", {"url": "github.com/anthropics?tab=repos"})
    assert browser == ["https://github.com/anthropics?tab=repos"]
    for junk in ("https://host:notaport/x", "just words here", "localhost"):
        assert "isn't a web address" in registry.call("open_website", {"url": junk})
    assert browser == ["https://github.com/anthropics?tab=repos"]  # nothing more opened


def test_windows_terminal_finds_the_app_listed_as_terminal():
    assert [a.name for a in apps.find("Windows Terminal", [App("Terminal", "x"), App("Notepad", "y")])] == ["Terminal"]
