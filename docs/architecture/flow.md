# Flow

## Voice turn
```
push-to-talk / wake word
  -> mic -> VAD (Silero) -> STT
  -> fast router (local regex)
       match  -> run tool, canned reply -> TTS
       no     -> talker LLM (fast model, tools)
                   quick answer -> TTS
                   heavy task   -> spawn background task, say "on it" -> TTS
  -> music ducked while listening and speaking
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
