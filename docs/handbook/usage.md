# Using Evie

Talk or type naturally. Short fixed commands are handled instantly without the AI; everything else goes to the AI, which picks a tool.

## Instant commands (no AI, no delay)
"next", "previous", "pause", "resume", "volume 40", "louder", "quieter", "shuffle". Only these whole phrases. "play hola amigo" or "next song by X" go to the AI.

## Music
- "Play <song>" or "queue <song>": looks in your music folder first (`EVIE_MUSIC_DIR`, default `~/Music`).
- Not in the library: Evie offers to search online. She reads the first few results aloud, you say a number, termusic downloads it, then it plays.
- "What's playing", "what's in the queue", "clear the queue", "stop termusic".

## Answers
- Weather: "what's the weather", "will it rain in Pune tonight". Default city is `EVIE_LOCATION` (Mumbai).
- Facts: "what is kubernetes", "who is ..." (Wikipedia).
- Anything current: "who won the match yesterday" (web search).

## Doing things on the PC
- "Open WhatsApp", "open Spotify": opens any installed app by its Start menu name.
- "Open gmail.com": opens a link in your default browser.
- "Text my friend that it will be cold tonight": Evie drafts the message, puts it on your **clipboard**, and tells you. You paste and send it yourself. Evie never types into other windows and never sends messages.

## Safety
- Evie is read-only by default. Anything that writes, sends or deletes asks first; answer "yes" or "no".
- Opening apps and browsers takes focus. Do not use them while in a full-screen game (a gaming mode is planned, not built).
- Tool arguments are never put into shell strings, and Evie never runs with permission checks disabled.

## Not built yet
Wake word (voice mode listens all the time and answers anything it hears; there is no wake word yet), pausing music while you talk, mail and calendar, background tasks and phone alerts, "open Claude Code and ask it to ...". See the roadmap in `docs/roadmap/`.
