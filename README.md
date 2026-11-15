# Evie

A voice assistant for one Windows PC. You talk, it acts: it plays your music, answers questions, opens apps and drafts messages. Built to be used daily, and built for voice: it speaks while it is still thinking, and it never sends you to a screen you cannot look at.

> Status: working MVP. Hands-free voice loop, local speech recognition and voice, music control, web answers. Mail, calendar, background tasks and a wake word are planned. See [docs/roadmap/roadmap.md](docs/roadmap/roadmap.md).

## What it does
- **Music** through [termusic](https://github.com/tramhao/termusic): "play Jo Tum Mere Ho", "next", "volume 40", "queue something by Anuv Jain". If a song is not in your library it searches online with termusic's own search and plays it when it arrives.
- **Answers:** weather, Wikipedia facts, current web questions, in one or two spoken sentences.
- **PC:** opens any installed app or website, and drafts a message for you onto the clipboard (you paste and send).
- **Voice:** speech in English, Hindi or both mixed (Hinglish), recognised on your PC. Replies are printed and spoken together, sentence by sentence.
- **Safe by default:** anything that writes, sends or deletes asks for a "yes" first.

## How a voice turn works
```
mic (always open) -> loudness gate -> speech-to-text (Whisper on this PC, Groq as backup)
  -> "You: ..." printed -> fast router (exact commands, no AI)  or  Gemini brain with tools
  -> reply streams out: printed and spoken together (Kokoro voice on this PC, Edge as backup)
```

## Quick start (Windows 10/11)
```
git clone https://github.com/gupta-v/Evie.git && cd Evie
git checkout dev
uv sync
copy .env.example .env        # then add your keys (never commit .env)
uv run python scripts/voice_setup.py    # downloads voice models, checks keys, mic, tools
uv run evie --voice           # or: uv run evie   (text mode)
```
You need [uv](https://docs.astral.sh/uv/), a Gemini key (free), and optionally Groq and Tavily keys. Full guide: [docs/handbook/setup.md](docs/handbook/setup.md).

## Docs
| | |
|---|---|
| [docs/handbook/](docs/handbook/README.md) | Setup, usage, every setting, troubleshooting |
| [docs/roadmap/roadmap.md](docs/roadmap/roadmap.md) | What is built and what is next |
| [docs/decisions/decisions.md](docs/decisions/decisions.md) | Why things are the way they are |
| [docs/architecture/](docs/architecture/overview.md) | Design notes and flows |
| [.claude/CLAUDE.md](.claude/CLAUDE.md) | Project brief for Claude Code sessions: state, layout, rules, gotchas, next steps |

## Develop
```
uv run pytest        # no network, never opens real windows or processes
```
Layout: `src/evie/core` (agent, router, registry, prompts), `providers`, `tools` (what the AI can call), `services` (the real work), `utils`. Scripts in `scripts/`.

## Notes
- Windows only for now. Your audio stays on the PC for speech recognition and voice by default; cloud fallbacks (Groq, Edge) send audio or text out.
- Hands-free listening has no wake word yet: anything loud enough is transcribed. Use a headset mic or raise `EVIE_THRESHOLD` in noisy rooms.
