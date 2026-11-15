# Decisions

Status: `accepted`, `proposed`, `open`.

| # | Decision | Status | Why |
|---|---|---|---|
| 1 | **Tools:** MCP for third-party (Gmail, Calendar, Drive, Playwright). Native functions for own tools (memory, todos, termusic, OS, scheduler). One `ToolRegistry`. | accepted | MCP is a plugin standard, not a requirement. Senku's private in-process MCP servers were overhead for nothing. Rust body (later) is a local MCP server. |
| 2 | **Brain:** no from-scratch agent runtime. Heavy work via Claude Agent SDK. Talker is a thin own loop with a fast model. Brain behind one interface. | accepted | Tool loop, permissions, MCP hosting are solved. Do not copy `--dangerously-skip-permissions` or shell-string prompts. |
| 3 | **Voice:** Pipecat for VAD, STT, LLM, TTS, barge-in. Silero VAD. Push-to-talk first. STT Groq Whisper or Deepgram. TTS Edge first, Fish Audio after. | accepted (version verified) | Interruption and turn-taking are hard to build. Pipecat 1.16.0 installed on Py 3.12 Windows. STT decided: Groq Whisper (cloud, light, free key). TTS: Edge first (custom service, no built-in), Piper as local fallback (built-in), Fish/Kokoro later. Browser Web Speech API considered, not chosen. |
| 4 | **Stack:** Python (brain, voice), Rust (Windows body), Go (gateway), React+TS (UI). Python plus bare web page first, others added in phases. `uv` for Python, `requires-python >=3.12,<3.14` (Pipecat resolution fails for 3.14). Do not add `openai` or `grpcio-tools` directly: they clash with Pipecat's `protobuf`/`typing-extensions` pins. Generate termusic proto stubs with a protoc matching protobuf 6.x. | accepted | Each language has one job. Rust and Go would delay a working voice if put in MVP. If Go is overhead, Python takes gateway back. |
| 5 | **Platform:** Windows only for v1. Voice in MVP. UI look decided later. | accepted | |
| 6 | **Notifications:** one native `notify()` to toast, ntfy, UI. Phone push only if away or long task. | accepted | From Senku ntfy. Fixes: long random topic or self-host, no sensitive body, signed one-time approve token, persist reminders in SQLite. |
| 7 | **Termusic:** gRPC client of `termusic-server` (`[::1]:5101`) using `player.proto`. | accepted | Server has pause, skip, volume (step 5), queue, shuffle, loop, seek. Gaps: no absolute volume, TogglePause flips state, queue needs path or URL, music drowns mic. |
| 8 | **Process model:** always-on Rust "ear" (tray, autostart, mic, wake word, VAD) plus Python brain, talking over a local WebSocket. No browser page needed for voice. Heavy Python modules and MCP servers load lazily; brain may be started on demand and stopped when idle. | accepted | Always-on and light. Cloud STT/LLM/TTS keep local cost to mic, wake word and a socket. Drops the browser-mic-page idea (needs an open tab, sends audio to Google all the time). |
| 9 | **Wake word:** openWakeWord (local ONNX, 80 ms frames, threshold plus cooldown), run in the Rust ear via `ort`. Stock "hey jarvis" first, custom "Evie" model trained later. | proposed | Read in binoy's Jarvis `wakeword.rs`. adewaskar's Jarvis regex-matches browser SpeechRecognition output instead. Custom-word training quality for "Evie" unverified. |
| 10 | **Tool contract:** every tool declares `risk` (read or write) and `fast` (fast-path eligible). Approval gate and fast router read this metadata. Tools never import agent or voice code. | accepted | New tools are added without touching the brain. The loop in `core/agent.py` can change later (own loop, LangGraph) with no tool changes. |
| 11 | **State:** SQLite from the start for sessions, reminders, tasks. **Modes** in config; `gaming` mode = quiet short replies, no automation tools, phone push for long results. | proposed | |
| 12 | **Game safety:** Evie stays a separate audio-only process. No hooking, screen capture, overlay or input injection while a game runs (Valorant uses the Vanguard kernel anti-cheat). | accepted | Rule of thumb. What Vanguard flags is unverified. |
| 13 | **Rust ear, Python brain:** Rust does only mic, wake word, VAD, tray, autostart. Python does STT, thinking, TTS, tools. Python voice gateway and a push-to-talk test client come first, so the brain is proven by voice before any Rust. Stay on Python 3.12 (3.15 is alpha; AI/audio packages lag). 3.15 has PEP 810 `lazy import` (verified on 3.15.0a7); until then use function-level imports for heavy modules and convert later. | accepted | Measured: idle Python with google-genai, numpy, onnxruntime is ~96 MB RSS (imports only, no pipeline). Rust is lighter for the always-on loop. Brain speed is network-bound, not CPU-bound. Own Rust code written against the openWakeWord spec; binoy's repo has no license. |

## Open questions

| Question | Leaning | Blocks |
|---|---|---|
| Hermes Agent as core, or own brain plus Agent SDK? | Own. Read Hermes first | step 0 |
| LLM providers and fallback chain | Claude Haiku talker, Agent SDK for heavy | step 1 |
| TTS Fish Audio vs Edge/Kokoro | Edge first | step 4 |
| UI vibe: HUD vs minimal | later | phase 2 |
| Termusic server on this PC with real library? | ask user | step 2 |
| Headset or speakers, Discord at the same time? Where does Evie's voice play? | ask user | step 4 |
| Autostart at login? Tray icon only or status window? | tray only, autostart yes (confirm) | step 4 |
| Custom "Evie" wake word: train with openWakeWord or use Porcupine? | train openWakeWord | step 4 |
| Memory store | SQLite then pgvector | phase 5 |
