# Evie: Architecture Notes (draft v0)

> These notes are the original design and research. For what is actually built and the current layout, see `.claude/CLAUDE.md` and `docs/decisions/decisions.md` (decisions 19-24). The Rust ear, Go gateway, React UI, Pipecat and MCP layers described below are later phases or were replaced.

## Do we need MCP?

No. MCP is a plugin standard for tools, not a requirement. Plain Python functions with a JSON schema work fine for an agent.

| Use MCP when | Skip MCP when |
|---|---|
| Tool already exists as an MCP server (Gmail, Calendar, Drive, Playwright, GitHub, filesystem) | Tool is tiny and only Evie uses it (time, todos, notes, open app) |
| You want to add or swap tools without redeploying the brain | Tool needs very low latency (local OS control in Rust) |
| You want other clients (Claude Code, etc.) to reuse the same tools | Tool is called in a hot loop |

**Decision:** hybrid.
- MCP for third-party integrations: Gmail, Calendar, Drive, browser (Playwright MCP). Free, maintained, no code written.
- Native in-process tools for core and local things: memory, todos, notes, OS and app control, scheduler.
- One `ToolRegistry` interface in the brain hides the difference. The agent sees a flat list of tools either way. If an MCP server later proves a pain, replace it with a native tool without touching agents.

Senku used 4 in-process FastMCP servers on localhost ports. That is MCP overhead without MCP's benefit (nobody else consumes them). Evie should not repeat it.

## What we take from the references

| Source | Take |
|---|---|
| Eva | Fuzzy app launch, local OS control, FastAPI web UI |
| EDITH | Only unique idea: webcam hand-gesture control (mediapipe) and an air-doodle whiteboard (OpenCV). Optional later "gesture" module. Skip the rest: same `if "open x" in query` chain as Eva, Gemini, Streamlit app, empty README |
| Senku | LangGraph router, specialist agents, verifier, SSE streaming, Groq Whisper, per-thread memory |
| adewaskar/jarvis | Read-only tool gate by default, policy check on every tool call, barge-in VAD, HUD UI, browser as face and voice |
| binoymanoj/jarvis | Rust voice daemon (wake word, VAD), fast local intent router before the LLM, confirm destructive actions, background task manager, provider fallback chain |

## Deep read: binoymanoj/jarvis brain

Files read: `src/ai/agent.rs`, `jev.rs`, `fallback.rs`, `src/core/tasks.rs`, `src/tools/agent_tasks.rs`.

**Pattern worth copying**
- Two-stage fast router before the LLM: local regex (<0.1ms), then an optional tiny classifier (Jev, ~70ms, threshold 0.75), then the full LLM. Matched actions skip the LLM and speak a canned confirmation. The turn is still written to chat history.
- Background `TaskManager`: `spawn_agent_task` returns an id instantly. The worker runs detached. Task state (status, activity, progress, recent log lines, pid) is a record flushed atomically to a JSON file. The UI reads that file. Cancel kills the process group. The voice loop is never blocked.
- Coding tasks run by shelling out to an existing harness (`claude -p`, `codex exec`) with output to a log file, and a monitor loop tails the log every 800ms. No agent loop is written for coding work.
- Confirmations are produced in code per tool, not by the LLM. Guards catch the LLM saying "Done" without calling a tool.
- Model fallback list advances on 429 and resets on success.

**Weak or broken (do not copy)**
- `run_research_worker` and `run_analysis_worker` are stubs. They write a template report or sleep 600ms and report success. There is no real research.
- Coding worker runs with `--dangerously-skip-permissions` and interpolates the LLM prompt into a `bash -c` string. Quotes in the prompt can break or inject commands.
- ~20-rule system prompt does the behavior work. Fragile.
- Three separate history stores (Gemini, OpenAI, Anthropic formats). History is RAM-only, so no memory across restarts.
- All tools are in-binary and Hyprland-specific.

**Evie takeaway:** copy the fast router, TaskManager shape, code-side confirmations. Replace stubs with real agents. Run delegated tasks through the Claude Agent SDK with a policy gate instead of skip-permissions. Pass the prompt as an argument, never through a shell string.

## Notifications (from Senku's ntfy tool)

Source: `Senku/SenkuNoChinou/MCP/tools/ntfy_tool.py` (POST to `ntfy.sh/<topic>`, Discord fallback) and `core/scheduler.py` (60s asyncio poll, fires reminder 15 min before events). Partly read via grep only.

**Design**
- One native `notify(title, body, priority, channels, actions)` function. Not MCP. TaskManager, scheduler and policy gate call it directly.
- Channels: Windows toast, phone via ntfy, UI. Optional Discord fallback.
- Triggers: background task done or failed, reminders, morning brief, approval requests.
- Send a phone push only if the user is away from the PC or the task was long. Toast otherwise.
- ntfy action buttons (click URL, Approve / Deny) for gated actions.

**Fixes over Senku**
- Topic name is the password on public ntfy.sh. Use a long random topic, or self-host ntfy.
- No sensitive content (email bodies, tokens) in the push body. Send a short title and a link.
- Approve buttons need a signed one-time token with expiry, checked by the gateway. Otherwise anyone who finds the topic can approve an action.
- Reminders persist (SQLite) so they survive restarts. Scheduler reloads pending reminders on boot.

## Termusic voice control

Source read: `C:\Projects\termusic\lib\proto\player.proto`, `server/src/server.rs`. Termusic runs a gRPC server (`termusic-server`, default `[::1]:5101`, tonic).

**Tool map (native tools, not MCP)**
| Voice | gRPC |
|---|---|
| "pause" / "play" | `TogglePause` (returns new state; check `GetProgress.status` first so "play" never pauses) |
| "next" / "previous" | `SkipNext` / `SkipPrevious` |
| "volume up/down" | `VolumeUp` / `VolumeDown` (server `VOLUME_STEP = 5`, so one call = 5) |
| "volume to 30" | no absolute set. `GetProgress.volume`, then N x up/down |
| "add X to queue" | `AddToPlaylist{at_index, tracks:[TrackId{path|url}]}` |
| "play track 3", "clear queue", "shuffle", "loop" | `PlaySpecific`, `RemoveFromPlaylist{clear}`, `ShufflePlaylist`, `CycleLoop` |
| "what's playing" | `GetPlaylist` + `GetProgress` |
| seek, speed | `SeekForward/Backward`, `SpeedUp/Down` |

**Name to track.** Queue needs a path or URL, so Evie must resolve "add Blinding Lights": search local library first (termusic DB or file scan), else `yt-dlp "ytsearch1:<query>"` to get a URL, then `AddToPlaylist`. Termusic README lists yt-dlp search and URL tracks, but I have not tested streaming a YouTube URL from the queue.

**Wiring:** Rust (tonic + prost, reuse the repo's own proto) or Python (grpcio) client. Rust body is the natural home, exposed to the brain as a tool. Add `SubscribeServerUpdates` stream to feed "now playing" to the UI and to skip-announcements.

**Voice-flow notes**
- Music commands are fixed intents: the fast router handles them with no LLM. Only "add X to queue" needs name extraction.
- Duck or pause music while Evie listens and speaks (binoy has `audio/ducking.rs` for this). Otherwise STT hears the music.
- Keep `deck.proto` (DJ decks) out of scope for now.

## Layout

```
React UI (HUD, chat, voice, approvals)
      | WebSocket / SSE
Go gateway: auth, sessions, event bus, policy gate, scheduler, MCP host
  |                |                    |
Python brain     Rust daemon          MCP servers
(LangGraph,      (wake word, VAD,     (Gmail, Calendar, Drive,
 memory, LLM     audio, OS control,    Playwright browser)
 routing)        screen capture)
```

- **Python:** agents, LLM calls, memory.
- **Rust:** local voice and OS control.
- **Go:** gateway and policy.
- **React:** UI.

## Rules
1. Read-only by default. Write, send, delete, shell need approval in the UI. Email send always confirms.
2. Local intent router first (regex or small classifier). LLM only when it does not match.
3. Persistent memory (SQLite to start, pgvector later). No in-RAM-only state.
4. OAuth tokens and keys live only in the gateway. Never in the UI or in prompts.
5. Provider fallback chain for LLMs (quota or outage).

## Build order
1. Python brain plus Gmail, Calendar, browser MCP. CLI only.
2. Go gateway plus React UI: streaming, approval prompts.
3. Voice: Groq Whisper plus Edge TTS first, then Rust daemon for wake word.
4. Memory, background tasks, proactive morning brief.
5. Optional: Senku ESP32 body.

Cutting scope: phases 1 and 2 are a usable Evie. Do not start Rust or Go in phase 1.

## Open questions
- Brain: own LangGraph, or Hermes Agent as core? (Hermes not yet read.)
- LLM provider(s): Claude, Groq, Gemini, mix?
- Windows only for v1?
- Voice in v1, or text first?
- UI vibe: Spider-Man "Brand New Day" red/black suit, HUD or minimal?
