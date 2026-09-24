# Idle Behaviour

## Priority Levels

| Priority | Activity | Resource Budget |
|----------|----------|-----------------|
| P0 | Listening (always active) | 2% CPU, 100MB RAM |
| P1 | STT model warm | 5% CPU, 2GB RAM (cached) |
| P2 | TTS model warm | 5% CPU, 500MB RAM (cached) |
| P3 | Memory consolidation | 10% CPU, 200MB RAM |
| P4 | Reflection generation | 15% CPU, 300MB RAM |
| P5 | Dreaming cycle | 20% CPU, 400MB RAM |
| P6 | Index rebuilding | 15% CPU, 200MB RAM |
| P7 | Vault health check | 5% CPU, 100MB RAM |

## Background Cycle

After 30s of inactivity:
1. Complete any in-flight memory writes
2. Start memory consolidation (if >10 new memories)
3. Run reflection (if significant conversation since last)
4. Start dreaming cycle
5. On ANY voice activity: immediately pause all P3-P7
6. Resume listening at P0

## Resume on Activity

When voice activity is detected during idle processing:
- P3-P7 tasks are suspended within 100ms
- Completed tasks save state for resumption
- Partial tasks checkpoint progress
- After conversation ends, idle processing resumes from checkpoint