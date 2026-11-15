# Evie

Windows voice assistant (Evie / Ev, name from Spider-Man: Brand New Day). Voice first. Windows only for v1. One user, one PC.

## The idea
You talk, it acts: controls music (termusic), answers questions (weather, Wikipedia, web), opens apps and sites, drafts messages to the clipboard. Planned: mail and calendar, background tasks, phone alerts. Think JARVIS / EDITH, built to be used daily.

Why it exists: the user's earlier attempts (Eva, EDITH, Senku) are hardcoded command chains or text-only. Evie combines a real voice pipeline, an instant path for fixed commands, an LLM brain for the rest, and a safety gate on anything that writes, sends or deletes.

## Status (2026-11-16): working MVP, voice loop built, tuning in progress
Repo: github.com/gupta-v/Evie. Work happens on **`dev`** (PR #1 `dev` -> `main` is open; `main` holds only an empty README until it is merged). Local `master` is stale, ignore it. 182 tests pass.

Built and verified live:
- **Text and voice REPL** (`uv run evie`, `uv run evie --voice`). Voice is hands-free: the mic stays open, no key press, no wake word yet.
- **Voice turn:** mic -> loudness gate -> speech-to-text -> print "You:" -> router or brain -> reply streams out printed **and spoken at the same time**. Timers are printed per stage.
- **STT:** on-device Whisper (`faster-whisper`, `base` multilingual, language auto limited to en/hi, so Hinglish works) first, Groq cloud Whisper as backup (keys rotate on rate limit). The music library's artist and song names are fed to Whisper as a spelling hint.
- **TTS:** local Kokoro (`af_sarah`, int8 ONNX) first, Edge neural voices as fallback. Reply is spoken sentence by sentence (long sentences from the first comma) while still being written.
- **Brain:** Gemini (streaming) with a model fallback chain, because the free tier allows ~5 requests/min per model. Claude provider exists but is untested (no API credit) and not streaming.
- **Tools:** music (termusic over gRPC: playback, volume, songs by name, online search/download through termusic's own `s` UI), weather, web search, Wikipedia, open app, open website, time, clipboard.
- **Fast router** (`core/router.py`): exact short commands ("next", "pause", "volume 40", "louder") run the tool with no LLM.
- **Safety:** read-only by default; write tools return NEEDS_APPROVAL and the next "yes" runs them.

Not built: wake word, pausing music while listening, gaming mode, SQLite store, background tasks and ntfy (step 5), Gmail/Calendar MCP (step 6), Rust "ear", Piper fallback, history cap, `run_claude_code` tool. See Next steps.

## Read first
- `docs/handbook/`: setup, usage, settings (every env var), troubleshooting. Written for a new user, accurate to the code.
- `docs/decisions/decisions.md`: decision log and open questions. Check before changing direction.
- `docs/roadmap/roadmap.md` (steps, status) and `plan.md` (tasks per step, newest-first status log at the bottom).
- `docs/architecture/overview.md` and `flow.md`: design notes (partly aspirational: Rust/Go/React layers are later phases).
- `docs/references/prior-art.md`: what to take from Eva, EDITH, Senku, the two Jarvis repos, termusic.

## Run
```
uv sync                                   # close any running Evie first (Windows locks evie.exe)
uv run python scripts/voice_setup.py      # downloads Kokoro + Whisper models into models/, checks keys, mic, tools
uv run evie            # text      uv run evie --voice   # talk
uv run pytest          # 182 tests, no network, no real windows or processes
```
Scripts: `voice_setup.py`, `mic_check.py` (live level meter + verdict), `voices_demo.py`, `stt_compare.py` (compare speech engines on the user's voice). Settings are env vars read in `utils/config.py`, listed in `docs/handbook/settings.md`. Debug: `EVIE_DEBUG=1` prints each tool call and brain errors.

## Layout (src layout, package `evie`)
```
src/evie/
  core/       main.py (REPL, voice loop, stage timers), agent.py (talker: history, write approval, stream()),
              prompts.py (system prompt), registry.py (ToolRegistry), router.py (fast regex router)
  providers/  gemini.py (streaming + model fallback), anthropic.py
  tools/      what the LLM can call, one folder per domain, imported in each __init__: music/ (playback, volume,
              songs, online), web/, system/ (apps, clipboard), info/
  services/   the real work behind tools, same domains: music/ (termusic gRPC client, TUI input, library, watcher),
              web/, system/, voice/ (stt.py: mic + gate + Whisper; tts.py: Kokoro/Edge + Speaker)
  utils/      config.py, text.py
scripts/  tests/  docs/  proto/  models/ (gitignored)
```
Tools know nothing about the agent or voice code. A new tool = a function with `@tool(risk=, fast=)` and a Google-style docstring with an `Args:` entry per parameter, in the right `tools/<domain>/` file, imported in that folder's `__init__`.

## Rules
- Tools: MCP for third-party (Gmail, Calendar, Drive, browser). Native functions for own tools. One `ToolRegistry`.
- Fast router (local regex) before the LLM for music and volume. LLM only on no match.
- Read-only by default. Writes, sends, deletes need approval. Email send always confirms.
- Never pass LLM text into a shell string. Pass argv lists. Never use `--dangerously-skip-permissions`.
- Secrets only in `.env` (gitignored). **Never read, print, `cat`, `od` or `grep -v` the `.env` file.** To check keys, list names only (`sed -E 's/=.*/=<set>/'`) or use `scripts/voice_setup.py`. Never in prompts, logs, docs, commits or push bodies.
- Termusic is controlled over its gRPC server (`[::1]:5101`, `proto/player.proto`). Read play state before `TogglePause`.
- Tests must never launch real windows, processes or browsers (autouse guard in `tests/conftest.py`). Fake the player (`FakePlayer`), the clock and the network.
- Evie never types into windows by focus; keys go only into termusic's own console process (`services/music/console_input.py`).
- Reference repos (`C:\Projects\Eva`, `EDITH`, `Senku`, `termusic`) are read-only; their `.env` files hold keys: do not read or copy them.

## Working style (the user's preferences)
- **Design for a voice assistant, not by convention.** If a pattern from other assistants is slow or unnatural to speak, do not copy it. Answer, do not dump; few clean results; nothing that sends the user to a screen they cannot look at; never make the user touch the keyboard.
- Fast matters: the user notices every second. Measure before and after (stage timers exist), and report numbers.
- Smallest change that fully solves the task. No unrequested features. New non-trivial logic gets one small test.
- Unverified facts (APIs, model names, limits) must be checked against current docs or measured. Record decisions in `docs/decisions/decisions.md`.
- Keep docs short and update them when a decision changes. Commits end with the `Co-Authored-By` trailer the harness gives. Do not push unless asked.

## Hard-won gotchas
- **Gemini free tier:** ~5 requests/min *per model*; a tool question costs 2. The SDK silently retried for 9-16 s and then crashed. Now `attempts=1`, a comma list in `EVIE_MODEL` is the fallback chain, and a spoken "brain is busy" replaces the crash.
- **Microphones (user's PC):** default input is a Bluetooth headset (WH-CH520). Its mic only works in call mode and sometimes returns pure silence (levels 0-1); `EVIE_MIC=Headset` worked once something else held the call link. The Realtek PC mic works but is quiet and noisy (100-400 level), so the gate threshold comes from a rolling median of the room, not the quietest moment. Check with `scripts/mic_check.py`.
- **Whisper invents text from noise** ("Thank you", "ご視聴ありがとうございました"): handled by phantom phrases, a 0.25 s minimum, a steady-noise cut, and by dropping any language other than en/hi.
- **Privacy:** hands-free with no wake word means anything above the threshold is transcribed. On-device STT keeps it local; Groq and Google (stt_compare) send audio out.
- **Windows:** console is cp1252 (output is forced to UTF-8). `uv sync` fails while `evie.exe` runs; never run `uv sync --no-install-project` (it uninstalls Evie from the venv). Bash heredocs that write `b"\0"` can produce real NUL bytes in files: check with a byte count, use `bytes(2)`.
- **Bluetooth headset audio** drops to low quality while its mic is open (call mode). Cannot be fixed in code.
- **termusic:** `s` search only works with the library pane focused; the screen-scraping parser is pinned only by `tests/fixtures/termusic_search_screen.txt`. Opening apps/browsers steals focus (a gaming mode must disable that).
- `models/` (Kokoro, Whisper) is gitignored; `voice_setup.py` fetches it. protobuf must stay 6.x (Pipecat pin).

## Next steps (suggested order)
1. Decide the STT default from the user's own results of `scripts/stt_compare.py` (on-device base vs small vs Groq vs Google). Local base misheard "Jo Tum Mere Ho" and "play"; accuracy is the main complaint now.
2. Pause/duck termusic while listening and speaking (roadmap 4.4); music through speakers is picked up as speech.
3. Cap conversation history (grows without limit); record routed turns in history.
4. Wake word or a hotkey (decision 9 and 13: Rust ear with openWakeWord), plus a mute switch.
5. Gaming mode (1b.5): no window-opening tools, short replies.
6. Step 5 (TaskManager, notify/ntfy) and step 6 (Gmail/Calendar MCP).
7. Smaller: router patterns ("volume up N", mute, "open <app>"), `run_claude_code(task, folder)` tool (design in roadmap), Claude provider streaming, Piper fallback TTS, TAVILY key for fast web search.
