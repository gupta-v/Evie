# Flow

## Voice turn (as built)
```
mic, always open (sounddevice callback -> queue)
  -> Gate: loudness above threshold starts an utterance, ~0.7 s of quiet ends it ("[listening done]")
  -> STT: faster-whisper on this PC (Groq if it fails)               "[speech-to-text 0.6s]"
  -> print "You: ..." (flushed), then at once:
  -> fast router (local regex): match -> run the tool, reply with its text, no LLM
     no match -> Agent.stream -> Gemini (streaming; tools run between turns)   "[brain 1.0s]"
  -> pieces of the reply are printed AND fed to tts.Speaker as they arrive:
     Kokoro makes each finished sentence in parallel, plays them in order
  -> back to listening (audio heard while speaking is discarded)
Planned: duck or pause termusic while listening and speaking; wake word or hotkey; gaming mode;
heavy work handed to a background task ("on it") instead of answered inline.
```

## Background task
```
talker calls spawn_task(title, prompt)
  -> TaskManager: record {id, status, activity, progress, log}, JSON state
  -> worker: Claude Agent SDK, behind policy gate
  -> UI / voice can list or cancel
  -> done or failed -> notify(): toast, or phone push (ntfy) if away
```

## Approval (writes, sends, deletes)
```
agent wants effectful tool
  -> policy gate: read-only allowed, effectful needs approval
  -> ask via voice or UI (and ntfy button with signed one-time token)
  -> approved -> run; denied -> report back
```

## Termusic
```
"add X to queue" -> resolve name: local library, else yt-dlp ytsearch1
  -> gRPC AddToPlaylist
"volume up" / "next" -> fast router -> VolumeUp / SkipNext (no LLM)
```
