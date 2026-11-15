# Implementation plan

Detailed, step by step. High-level view and phases: [roadmap.md](roadmap.md). Tick boxes as work lands. Update the status log at the bottom.

Conventions: package `src/evie`, run `uv run evie`, test `uv run pytest`. A new tool is a file in `tools/` plus an import in `tools/__init__.py`. Services (clients, background jobs) live in `services/`. Tools never import the agent or voice code.

---

## Step 0: Verify (done)
- [x] Pipecat 1.16.0 installs on Python 3.12 / Windows. Python capped `<3.14`.
- [x] Pipecat ships Groq STT, Google, Anthropic, Fish, Piper, Kokoro services, local and smallwebrtc transports, Silero VAD. No Edge TTS built in.
- [ ] Still open: PyAudio / local audio on this PC, live latency, Fish free-tier limits, Hermes yes/no.

## Step 1: Text brain (done)
- [x] `config.py`, `core/registry.py`, `core/agent.py`, `providers/{gemini,anthropic}.py`, `tools/basic.py`, `__main__.py`.
- [x] Verified live: Gemini `gemini-3.5-flash-lite`, "what time is it" calls `get_time`.
- [ ] Add a test that fakes the provider and checks the tool loop (no network).

## Step 1b: Foundation (before tools multiply)
| # | Task | Files | Done when |
|---|---|---|---|
| 1b.1 | [x] Tool metadata: `risk` (read or write), `fast` (fast-path eligible) on `@tool`; `registry.meta(name)` | `core/registry.py` | Test reads metadata |
| 1b.2 | [x] Policy hook: write-risk tools return "needs approval" unless approved | `core/registry.py` | Test: write tool blocked |
| 1b.3 | Lazy tool loading: tool modules import on first use, not at startup | `tools/__init__.py` | Startup does not import heavy deps |
| 1b.4 | SQLite state store (sessions, reminders, tasks) | `services/store.py` | Roundtrip test |
| 1b.5 | Modes in config (`normal`, `gaming`) read by agent and tools | `config.py` | Gaming mode shortens replies |


Prereqs: `termusic`, `termusic-server`, `yt-dlp`, `ffmpeg` on PATH (scoop). Server must be running, default `[::1]:5101`.

| # | Task | Files | Done when |
|---|---|---|---|
| 2.1 | [x] Copy `player.proto`, generate stubs with a protoc matching protobuf 6.x | `proto/player.proto`, `src/evie/services/termusic_pb/` | `import` of generated modules works |
| 2.2 | [x] gRPC client: connect, helpful error if server down, optional auto-start | `services/termusic.py` | `get_progress()` returns volume and status against a live server |
| 2.3 | [x] Music tools: play, pause (read status first), next, previous, volume up/down N times, now playing, queue list, clear, shuffle | `tools/music.py` | Typing each command makes termusic react |
| 2.4 | [x] Name to track: local library search, else `yt-dlp ytsearch1:`, then `AddToPlaylist` | `services/music_search.py` | "add Blinding Lights" lands in the queue |
| 2.5 | Tests with a fake gRPC server | `tests/test_music.py` | `uv run pytest` green |

Regenerate stubs (protobuf must stay 6.x to match Pipecat's pin, so use grpcio-tools 1.74-1.78, not latest):
`uv run --no-project --with "grpcio-tools==1.74.0" python -m grpc_tools.protoc -Iproto --python_out=src/evie/services/termusic_pb --grpc_python_out=src/evie/services/termusic_pb proto/player.proto`, then change `import player_pb2` in `player_pb2_grpc.py` to `from evie.services.termusic_pb import player_pb2`.

Needs from user: music folder path, auto-start preference.
Unknown: whether termusic plays a YouTube URL from the queue. Test early in 2.4.
Rules: volume step is 5 (server `VOLUME_STEP`). No absolute volume: read `GetProgress.volume`, then call N times. Never pass LLM text to a shell: `yt-dlp` gets an argv list.

## Step 3: Fast router
| # | Task | Files |
|---|---|---|
| 3.1 | Normalize text, regex map for pause, play, next, previous, volume up/down (+N), mute, stop | `core/router.py` |
| 3.2 | Router runs before the LLM. Match runs the tool and returns a canned reply. No match goes to the agent | `core/agent.py` |
| 3.3 | Record routed turns in history so follow-ups keep context | `core/agent.py` |
| 3.4 | Tests: phrases to actions, near-misses fall through | `tests/test_router.py` |

Done when: "next" returns in under 100 ms with no LLM call.

## Step 4: Voice (Python gateway, then Rust ear)
Design: a small always-on Rust "ear" detects the wake word and records the utterance, then sends audio to the Python brain over a local WebSocket (127.0.0.1). Python does STT, router, agent, TTS and plays the reply. See decisions 8 and 13.

**Protocol (define first, in `docs/architecture/protocol.md`):**
- Ear to brain: `wake`, `audio` (pcm16 mono 16 kHz, binary frames), `end_of_speech`.
- Brain to ear: `speaking_start`, `speaking_end` (ear ignores the mic or wake word meanwhile), `mode` (`normal` or `gaming`), `shutdown`.

| # | Task | Files |
|---|---|---|
| 4.1 | Write the protocol doc | `docs/architecture/protocol.md` |
| 4.2 | Python voice gateway: WebSocket server, Groq Whisper STT (`GROQ_API_KEY`), router then agent, TTS (custom Edge service, Piper fallback), plays reply | `voice/gateway.py`, `voice/stt.py`, `voice/tts.py` |
| 4.3 | Test client: push-to-talk script that speaks the same protocol (proves the brain by voice with no Rust) | `scripts/ptt_client.py` |
| 4.4 | Duck or pause termusic while listening and speaking | `services/termusic.py` |
| 4.5 | Rust ear: cpal mic, openWakeWord via `ort`, Silero VAD, record utterance, WebSocket client | `ear/` (Rust crate) |
| 4.6 | Tray icon, autostart at login, single instance; ear launches the Python brain on demand and stops it when idle (optional) | `ear/` |
| 4.7 | Gaming mode: short replies, no automation tools, no windows or focus steal | `config.py` |
| 4.8 | Custom "Evie" wake word (train with openWakeWord); stock "hey jarvis" first | `models/` |
| 4.9 | Measure idle CPU and RAM of ear and brain, set a budget | |

Done when: with the ear running and a game open, "hey Jarvis, next song" works by voice with no window appearing.
Test early: mic shared with Discord, output device (headset vs speakers), Python cold-start time if the brain launches on demand.
Licensing: write our own Rust against the openWakeWord spec (Apache-2.0 code). binoy's repo has no license, so use it as a design reference only. Pretrained model license unverified.

## Step 5: Two-speed brain and notify
| # | Task | Files |
|---|---|---|
| 5.1 | TaskManager: record, JSON state, detached worker, cancel, list | `services/tasks.py` |
| 5.2 | Heavy worker via Claude Agent SDK behind a policy gate (needs terms check on Pro login, or API credits) | `services/workers.py` |
| 5.3 | `notify()`: Windows toast, ntfy phone push (long random topic) | `services/notify.py` |
| 5.4 | Tools: spawn, list, cancel task | `tools/tasks.py` |

Done when: a long task finishes and the phone buzzes.

## Step 6: MCP (Gmail, Calendar)
| # | Task |
|---|---|
| 6.1 | MCP client in the registry: load servers, expose their tools as registry tools |
| 6.2 | Gmail and Calendar read-only servers, OAuth tokens kept in `.env` or a gitignored file |
| 6.3 | Approval gate for any write (policy hook in the registry) |

Done when: "any unread mail?" works.

---

## Cross-cutting
- Docs: update `roadmap.md`, `decisions.md` when a decision changes, and this file's boxes.
- Commit after each step. No secrets in git (`.env` ignored).
- One small test per non-trivial module.

## Status log
- 2026-11-15: step 2.4 done. Songs by name: `services/library.py` (whole-word match on file names in `EVIE_MUSIC_DIR`, default ~/Music; one-letter words ignored), `services/online.py` (yt-dlp search/download, argv only, YouTube hosts only), tools `music_play_song`, `music_queue_song`, `music_search_online`, `music_download` (risk=write). Flow: library miss -> say so -> offer online search -> options -> user picks -> approval (Agent remembers the blocked write, user's yes runs it) -> download to library, queue, play. Bug found and fixed: termusic silently ignores adds it cannot use, so `Termusic.add` now verifies the queue grew and `music_add` rejects non-paths. 56 tests. Download not run live yet.
- 2026-11-15: any music command now opens the termusic TUI window first (`TERMUSIC_SHOW_UI`, default on; the TUI starts the server; headless server only if off, for gaming). `play` starts at track 1 when Evie just opened the player or it was stopped (termusic otherwise resumes the saved track); new `music_play_track(n)`; `EVIE_DEBUG=1` prints tool calls. 37 tests. Verified: TUI visible, track 1 plays. Known: after a force-kill termusic may not remember the last track, so the saved-position restart branch is covered by unit tests, not seen live.
- 2026-11-15: tools rebuilt on LangChain `@tool` + pydantic validation (30 tests). Fixed: headless server launch showed a blank console (DETACHED_PROCESS + scoop shim); now hidden console. `music_start` now opens the termusic TUI (which starts the server) and does not auto-play.
- 2026-11-15: verified live against real termusic: "start terminal music" auto-starts the server and plays, "what is playing" works, "stop termusic" quits gracefully then force-kills termusic* (native equivalent of the PowerShell `termusic-kill-server` profile function). `music_start` and `music_stop_player` tools added, `TERMUSIC_AUTOSTART` config, 23 tests. Known gap: status gives track number, not title (protocol has no title).
- 2026-11-15: step 2.3 done: `tools/music.py` (12 tools; transport and volume marked fast), registry gained `optional` args, 17 tests green, Gemini accepts schemas and relays the server-down message. Real termusic-server not tested yet.
- 2026-11-15: step 2.1 (proto stubs, protobuf 6.31 gencode) and 2.2 (`services/termusic.py` client + fake-server tests, 10 tests green) done. Not yet run against the real termusic-server.
- 2026-11-15: foundation decisions added (daemon, wake word, tool contract, game safety). Step 1b added.
- 2026-11-15: docs created. Step 0 verified. Step 1 done: `src/evie` package, Gemini talker verified live.
