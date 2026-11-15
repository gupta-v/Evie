# Prior art

Read from source: Eva README, Senku README, EDITH `edith.py` and requirements, binoymanoj/jarvis (`agent.rs`, `jev.rs`, `fallback.rs`, `tasks.rs`, `agent_tasks.rs`, architecture doc), termusic proto. adewaskar/jarvis: README only.

| Project | Take | Skip |
|---|---|---|
| `C:\Projects\Eva` | Fuzzy app launch, local control, FastAPI UI | Hardcoded commands, pyttsx3, no agent loop |
| `C:\Projects\EDITH` | Webcam gesture control (mediapipe), air-doodle board. Optional later | Same substring `if` chain as Eva, Gemini, empty README |
| `C:\Projects\Senku` | LangGraph router, specialist agents, verifier, SSE, Groq Whisper, ntfy, scheduler, ESP32 body | In-process MCP servers nobody else uses, RAM-only MemorySaver |
| adewaskar/jarvis | Browser = face and voice, bridge = brain. Read-only tool gate by default, policy check on every call. Barge-in VAD. HUD | Node bridge, tied to Agent SDK |
| binoymanoj/jarvis | Two-stage fast router (regex then small classifier). TaskManager with JSON state and cancel. Delegate coding to `claude -p`. Code-side confirmations. Model fallback chain. Ducking | Stub research and analysis workers, `--dangerously-skip-permissions`, shell-string prompt injection, 20-rule system prompt, RAM-only history, Hyprland-only |

## binoy brain, short
1. `is_exit_command` and `FastPathRouter` (local regex, then Jev classifier at confidence 0.75) before any LLM.
2. One generalist LLM, 56 native tools, `MAX_TOOL_TURNS = 5`, context line prepended per turn.
3. Heavy work to `TaskManager` (detached worker, JSON state, 800 ms log tail, process-group cancel).
4. Confirmations generated in code per tool; guards catch "Done" without a tool call.
5. Fallback list advances on 429.

## Termusic
`C:\Projects\termusic` (fork of the Rust TUI player). gRPC server, `lib/proto/player.proto`. See decision 0007.
