# Roadmap

## MVP goal

Say "Evie, add Blinding Lights to the queue, then volume up" and it happens in about 1-2 s. Then "any unread mail?" gets an answer. A finished background task buzzes the phone.

**In MVP:** Python, push-to-talk, termusic tools, fast router, Pipecat voice, two-speed brain, ntfy, Gmail/Calendar read-only via MCP, bare web page for the mic.
**Not in MVP:** Go gateway, Rust body, React UI, wake word, memory, gesture, ESP32.

## MVP steps

Each step runs on its own. Tick when done.

- [x] **0. Spike / verify (partly).** Pipecat 1.16.0 installs and imports on Python 3.12 / Windows. Ships services for Groq (LLM, STT, TTS), Google (LLM, STT, TTS), Anthropic, Fish, Piper, Kokoro, Whisper, plus `smallwebrtc` and `local` transports and Silero VAD. No built-in Edge TTS: write a small custom TTS service. Still to verify: live latency, Fish free-tier limits, Hermes decision, local audio transport on this PC (PyAudio).
- [x] **1. Text brain.** `src/evie` package, `uv run evie`. Gemini (free) or Claude talker with own tool loop and `ToolRegistry`. Done when: type "what time is it", a tool answers.
- [ ] **2. Termusic tools.** Copy `player.proto`, generate grpcio stubs. Tools: pause/play (check state first), next, previous, volume up/down, add to queue, clear, what's playing. Name to track via local search then `yt-dlp ytsearch1:`. Done when: type "add X, next, volume up" and music reacts.
- [x] **3. Fast router.** Local regex for music and volume, LLM fallback. Done when: "next" returns in <100 ms with no LLM call. (Built; "volume up N", mute and a live latency check are not done yet.)
- [ ] **4. Voice.** Pipecat: Silero VAD, STT, TTS, push-to-talk, barge-in. Duck music while listening. Done when: step 3 works by voice.
- [ ] **5. Two-speed brain.** Fast model talks. Heavy agent runs in background via `TaskManager` (JSON state, cancel). `notify()` to toast and ntfy. Done when: long task ends, phone buzzes.
- [ ] **6. MCP.** Gmail and Calendar, read-only. Done when: "any unread mail?" works.

**Idea, later (with step 5): "open Claude Code and ask it to plan X".** Today `open_app` can't, because Claude Code is a CLI, not a Start menu app. Wanted: a `run_claude_code(task, folder)` tool that opens Windows Terminal in a folder and starts `claude` with the user's words as its first prompt, so heavy work happens in a real session. Design notes: it is a write action (asks for a yes); pass argv only, never a shell string; `wt` treats `;` as a command separator, so strip `;` from the task; never use `--dangerously-skip-permissions`; ask or default the folder; same runner interface as the planned heavy runner (decisions: Claude Code/Codex behind one interface).

## Detailed plan

Tasks, files and done criteria per step: [plan.md](plan.md). Current step: **2, termusic tools**.

## After MVP

| Phase | Add |
|---|---|
| 2 | React UI: HUD, chat, task panel, approvals (look decided later) |
| 3 | Go gateway: auth, policy gate, approvals with signed tokens, scheduler, secrets |
| 4 | Rust body: Windows OS tools, hotkey, wake word. Exposed as local MCP server |
| 5 | Persistent memory (SQLite, then pgvector), morning brief, proactive reminders |
| 6 | Email send with approval, browser agent (Playwright MCP) |
| 7 | Optional: gesture module (from EDITH), Senku ESP32 body |

If Go in phase 3 feels like overhead, Python takes the gateway job back.

## Risks

- Voice latency on Windows is untested (Pipecat local audio).
- yt-dlp streaming from termusic queue is untested.
- Research and analysis workers in binoy's Jarvis were stubs. Ours must be real.
- API quotas and cost for the talker model.

## Needed from user

1. Anthropic API key, and talker model (Haiku is fastest and cheapest).
2. Termusic server runs on this PC with the real library.
3. Later: UI vibe, Hermes yes/no.
