# Troubleshooting

## Evie never reacts when I talk
Voice mode waits for sound above a threshold. Run `uv run python scripts/mic_check.py` and speak: your voice should rise well past the "speech above" number.
- If it never does: wrong or very quiet microphone. Try another with `EVIE_MIC`.
- If the threshold is too high for your mic, set a fixed lower one: `EVIE_THRESHOLD` (for example `400`).
- Bluetooth headsets switch to a low-quality call mode when the mic opens and take about a second to settle. Evie allows for that, but the built-in PC mic is more reliable.

## Evie reacts to music, TV or other people
There is no wake word: anything above the threshold is recorded and sent to Groq for transcription. Raise `EVIE_THRESHOLD`, use a headset mic, or pause the music. Pausing music while you talk is planned, not built.

## Evie hears the wrong thing, such as "Thank you."
Speech-to-text models invent words from near-silence. Speak after the "[listening...]" line and close to the mic.

## "No Groq key is set" / "All Groq keys were rejected or rate limited"
Add `GROQ_API_KEY` (or `_KEY1`/`_KEY2`) to `.env`. A rate-limited key is skipped for 5 minutes while the others are tried.

## No sound, or an error from the voice
- Run `uv run python scripts/voice_setup.py`: it downloads missing Kokoro files.
- With `EVIE_TTS=kokoro,edge`, a failing local voice falls back to the online one, which needs internet.

## "I couldn't reach the web search"
Without `TAVILY_API_KEY` search uses a free fallback that sometimes returns nothing. Add a Tavily key.

## Music: "can't find termusic" or nothing plays
Put `termusic` and `termusic-server` on PATH. Check that `TERMUSIC_ADDR` matches the server. If music windows pile up, say "stop termusic".

## "failed to remove ... evie.exe" during `uv sync`
Evie is still running in another terminal. Close it and run `uv sync` again.

## An app is not found ("open X")
Evie opens apps by their Start menu name; "Windows Terminal" is listed as just "Terminal". Command-line tools such as Claude Code are not Start menu apps.

## Replies take 5-15 seconds, or "My brain is busy right now"
The Gemini free tier allows only about 5 requests a minute per model, and a question that uses a tool costs 2. Evie moves to the next model in `EVIE_MODEL` when one is limited, and says "My brain is busy" if all are. Waiting a minute clears it. A paid Gemini key removes the limit. `EVIE_DEBUG=1` prints the error.

## Evie misunderstands names or Hindi words
Compare the options on your own voice: `uv run python scripts/stt_compare.py`. Say a sentence; it prints what each speech engine heard (on-device Whisper, Groq cloud Whisper, Google) and how long each took. Then set `EVIE_STT` and `EVIE_STT_MODEL` to the one that fits (see [settings.md](settings.md)).
