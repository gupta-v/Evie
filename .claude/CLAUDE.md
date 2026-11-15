# Evie

Windows voice assistant (Evie / Ev, name from Spider-Man: Brand New Day). Voice first. Windows only for v1.

## The idea
Evie is a personal voice assistant for one user on one Windows PC. You talk, it acts: controls music (termusic), reads mail and calendar, browses the web, runs long tasks in the background and pings the phone when they finish. Think JARVIS / EDITH, built to be actually used daily.

Why this exists: the user's earlier attempts (Eva, EDITH, Senku) are either hardcoded command chains or a text-only backend. Evie combines the best parts: a real voice pipeline, a fast path for simple commands, an agent brain for hard ones, and a safety gate on anything that writes, sends or deletes.

How it works in one breath: push-to-talk, then VAD and STT. A local regex router handles fixed commands ("next", "volume up 5") with no LLM. Everything else goes to a fast talker model that answers or hands heavy work to a background Claude agent. Results come back by voice, toast or phone push (ntfy). Third-party tools come through MCP, own tools are native functions.

Principles: voice first, fast for simple and smart for hard, safe by default (read-only until approved), reuse harnesses and MCP servers, local-first secrets.

Not in scope now: wake word, memory, gesture control, ESP32 body, Go/Rust/React layers (see roadmap).

**Status:** docs only, no code yet. Next: roadmap step 0 (verify Pipecat, Fish Audio, Hermes) then step 1 (text brain).

## Read first
- `docs/idea.md`: what and why
- `docs/decisions/decisions.md`: decision log and open questions. Check before changing direction.
- `docs/architecture/overview.md` and `flow.md`: layout, tool maps, flows
- `docs/roadmap/roadmap.md`: MVP steps. Tick checkboxes when a step is done.
- `docs/references/prior-art.md`: what to copy from Eva, EDITH, Senku, the two Jarvis repos, termusic

## Stack
- Python 3.12 (`>=3.12,<3.14`) managed with `uv` (`uv sync`, `uv run`). Brain and voice (Pipecat, talker LLM, Claude Agent SDK, TaskManager, MCP client).
- Rust: Windows body, later. Go: gateway, later. React + TypeScript: UI, later.
- MVP is Python plus a bare web page only. Do not add Rust, Go or React before the roadmap says so.

## Layout (src layout, package `evie`)
```
src/evie/
  config.py       env settings
  core/           registry.py (ToolRegistry), agent.py, router.py (later)
  providers/      LLM backends: gemini.py, anthropic.py
  tools/          one file per capability, imported in tools/__init__.py
  services/       termusic gRPC client, notify, tasks (when added)
  voice/          pipecat pipeline (step 4)
tests/
docs/
```
Run: `uv run evie`. Tests: `uv run pytest`. Tools know nothing about the agent or voice code.

## Rules
- Tools: MCP for third-party (Gmail, Calendar, Drive, browser). Native functions for own tools. One `ToolRegistry`.
- Fast router (local regex) before the LLM for music and volume. LLM only on no match.
- Two-speed brain: fast model talks, heavy work runs in a background task via the Claude Agent SDK.
- Read-only by default. Writes, sends, deletes need approval. Email send always confirms.
- Never pass LLM text into a shell string. Pass argv. Never use `--dangerously-skip-permissions`.
- Secrets only in `.env` (gitignored). Never in prompts, logs, docs, or push bodies.
- Termusic is controlled over its gRPC server (`[::1]:5101`, `player.proto`). Read play state before `TogglePause`.
- Duck or pause music while Evie listens and speaks.

## Reference code (read-only, do not edit)
`C:\Projects\Eva`, `C:\Projects\EDITH`, `C:\Projects\Senku`, `C:\Projects\termusic`. Their `.env` files hold keys: do not read or copy them.

## Working style
- Smallest change that fully solves the task. No unrequested features.
- Unverified facts (Pipecat, Fish Audio, Hermes APIs) must be checked against current docs before use. Record results in `docs/decisions/decisions.md`.
- New non-trivial logic gets one small test.
- Keep docs short. Update docs when a decision changes.
