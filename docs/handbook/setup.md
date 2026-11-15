# Setup

Windows 10/11 only. About 10 minutes plus the voice download (about 120 MB).

## 1. What you need first
- **uv** (Python project manager): https://docs.astral.sh/uv/ . It installs Python 3.12 for you.
- **git**, to clone the repo.
- **termusic** on your PATH, if you want the music tools. Evie controls it through its server, so `termusic` and `termusic-server` must both run. Its online song search and download is termusic's own feature; Evie only drives it.
- A **microphone** and speakers or headphones, for voice. Text mode needs neither.

## 2. Get the code and dependencies
```
git clone <your repo url> Evie
cd Evie
uv sync
```
Close any running Evie before you run `uv sync` again later: Windows will not replace `evie.exe` while it runs.

## 3. Keys
Copy `.env.example` to `.env` and fill it in. `.env` is ignored by git and must never be shared or pasted anywhere.

| Key | Needed for | Where to get it |
|---|---|---|
| `GEMINI_API_KEY` | The brain (default model) | https://aistudio.google.com/apikey (free tier) |
| `GROQ_API_KEY` (and optional `GROQ_API_KEY1`, `GROQ_API_KEY2`) | Speech input (Whisper) | https://console.groq.com . With several keys Evie moves to the next when one is rate limited. |
| `TAVILY_API_KEY` | Fast, reliable web search (optional) | https://tavily.com . Without it, web search uses a slower, flakier free fallback. |
| `ANTHROPIC_API_KEY` | Only if you set `EVIE_PROVIDER=anthropic` | https://console.anthropic.com (needs API credit) |

## 4. Voice files and a health check
```
uv run python scripts/voice_setup.py
```
This downloads the Kokoro voice model into `models/kokoro/` (git ignores it), then checks your keys (names only, it never prints values), microphone, termusic, Windows Terminal and the clipboard tool. Run it again any time: it skips what is already there. Anything marked `MISSING` tells you what to fix.

## 5. First run
Text mode (type, no mic needed):
```
uv run evie
```
Voice mode (press Enter, speak, Evie answers aloud):
```
uv run evie --voice
```
Try "what time is it", then "play <a song you have>".

## 6. Check your microphone (voice mode)
```
uv run python scripts/mic_check.py
```
Speak while it runs: the bar should jump well past the "speech above" number. If it does not, pick another microphone with `EVIE_MIC` (see [settings.md](settings.md)). Hear the voices with `uv run python scripts/voices_demo.py` and choose one with `EVIE_KOKORO_VOICE`.

## Not covered by the script
It does not install uv, Python, git or termusic. It only reports what is missing.
