# Idea

**Evie** (or Ev): a personal voice assistant for Windows. Name from Spider-Man: Brand New Day.

## What it is
Talk to it, it acts. Controls music (termusic), reads mail and calendar, browses, runs long tasks in the background and pings the phone when done.

## Principles
- Voice first, not bolted on.
- Fast for simple commands (no LLM), smart for hard ones.
- Safe by default: read-only until you approve writes, sends, deletes.
- Reuse harnesses and MCP servers. Build only the voice, UI, policy and personal integrations.
- Local-first secrets.
- Always-on but light: one background daemon that autostarts, wake word runs locally, idle cost near zero, nothing to launch by hand (Eva was too heavy and needed managing).
- Quiet by default in games: audio only, no windows, no focus steal, no overlay, no input injection. Example: playing Valorant, say "hey Evie, do I have anything today?" and get a short spoken answer.

## Not now
Wake word, memory, gesture control, ESP32 body, Go/Rust/React layers. See [roadmap](roadmap/roadmap.md).

## Look
Decide later. Naming inspiration: red/black Spider-Man suit.
