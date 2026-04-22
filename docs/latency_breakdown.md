# Latency Breakdown

| Stage         | Target | Measured (CPU) |
|---------------|--------|----------------|
| STT (Whisper) | <150ms | ~300ms (tiny)  |
| Lang detect   | <20ms  | ~10ms          |
| Memory load   | <20ms  | ~8ms           |
| Groq LLM      | <250ms | ~180ms         |
| Tool exec     | <30ms  | ~15ms          |
| gTTS          | <100ms | ~80ms          |
| Total         | <450ms | ~593ms (CPU)   |

On GPU, Whisper tiny can drop near ~60ms and bring total latency below target.
