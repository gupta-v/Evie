# Settings

Set in `.env` (kept across runs) or for one run in PowerShell: `$env:NAME="value"; uv run evie`. Keys are in [setup.md](setup.md).

| Setting | Default | What it does |
|---|---|---|
| `EVIE_PROVIDER` | `gemini` | Brain: `gemini` or `anthropic` |
| `EVIE_MODEL` | `gemini-3.5-flash-lite` / `claude-haiku-5-5` | Override the model name |
| `EVIE_SPEAK` | off | `1` reads replies aloud in text mode too (`--voice` always does) |
| `EVIE_TTS` | `kokoro,edge` | Voice backends in order; the next is tried if one fails. `kokoro` alone = fully local |
| `EVIE_KOKORO_VOICE` | `af_sarah` | Local voice. Try `af_heart`, `af_bella`, `bf_emma`. Hear them: `scripts/voices_demo.py` |
| `EVIE_VOICE` | `en-IN-NeerjaNeural` | The online Edge voice (used only as fallback) |
| `EVIE_MIC` | system default | Microphone: a device number or part of its name (list: `scripts/mic_check.py`) |
| `EVIE_THRESHOLD` | learned | Fixed speech loudness (try 400 to 2000). Unset: about 3x the quietest level the mic has shown, min 250. See `scripts/mic_check.py` |
| `EVIE_LOCATION` | `Mumbai` | City used when you do not name one |
| `EVIE_MUSIC_DIR` | `~/Music` | Where your songs live |
| `TERMUSIC_ADDR` | `[::1]:5101` | termusic server address |
| `TERMUSIC_AUTOSTART` | `1` | Start termusic when a music tool needs it |
| `TERMUSIC_SHOW_UI` | `1` | Open the termusic window with it. Set `0` (for example while gaming) to keep it hidden |
| `EVIE_DEBUG` | off | `1` prints each tool call and its result |
