# Settings

Set in `.env` (kept across runs) or for one run in PowerShell: `$env:NAME="value"; uv run evie`. Keys are in [setup.md](setup.md).

| Setting | Default | What it does |
|---|---|---|
| `EVIE_PROVIDER` | `gemini` | Brain: `gemini` or `anthropic` |
| `EVIE_MODEL` | `gemini-3.5-flash-lite,gemini-3.1-flash-lite,gemini-3.5-flash,gemini-2.5-flash` / `claude-haiku-5-5` | Model name. For Gemini a comma list: the free tier allows about 5 requests a minute per model, so when one is limited Evie uses the next |
| `EVIE_SPEAK` | off | `1` reads replies aloud in text mode too (`--voice` always does) |
| `EVIE_TTS` | `kokoro,edge` | Voice backends in order; the next is tried if one fails. `kokoro` alone = fully local |
| `EVIE_KOKORO_VOICE` | `af_sarah` | Local voice. Try `af_heart`, `af_bella`, `bf_emma`. Hear them: `scripts/voices_demo.py` |
| `EVIE_TTS_SPEED` | `1.0` | How fast the local voice speaks: `0.9` slower, `1.2` faster |
| `EVIE_VOICE` | `en-IN-NeerjaNeural` | The online Edge voice (used only as fallback) |
| `EVIE_LANG` | `auto` | Language you speak. `auto` handles Hinglish (Hindi and English mixed). `en` or `hi` forces one, which cuts noise guesses but breaks mixing |
| `EVIE_LANGS` | `en,hi` | With `EVIE_LANG=auto`: speech detected as any other language is treated as noise |
| `EVIE_STT_MODEL` | `base` | On-device Whisper model (the backup, or the main one with `EVIE_STT=local`). `base` = Hindi and English, about 0.7 s. `base.en` = English only. `small` = more accurate but about 2 s and writes Hindi in Devanagari |
| `EVIE_STT` | `groq,local` | Speech-to-text order: `groq` = cloud (most accurate, about 0.4 s, sends your speech to Groq), `local` = on this PC. `local,groq` keeps audio on the PC but is less accurate |
| `EVIE_GROQ_MODEL` | `whisper-large-v3-turbo` | Groq model; `whisper-large-v3` is the other choice |
| `EVIE_MIC` | system default | Microphone: a device number or part of its name (list: `scripts/mic_check.py`) |
| `EVIE_THRESHOLD` | learned | Fixed speech loudness (try 400 to 2000). Unset: about 3x the quietest level the mic has shown, min 250. See `scripts/mic_check.py` |
| `EVIE_LOCATION` | `Mumbai` | City used when you do not name one |
| `EVIE_MUSIC_DIR` | `~/Music` | Where your songs live |
| `TERMUSIC_ADDR` | `[::1]:5101` | termusic server address |
| `TERMUSIC_AUTOSTART` | `1` | Start termusic when a music tool needs it |
| `TERMUSIC_SHOW_UI` | `1` | Open the termusic window with it. Set `0` (for example while gaming) to keep it hidden |
| `EVIE_DEBUG` | off | `1` prints each tool call and its result |
