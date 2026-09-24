# Performance

## Startup Optimization

| Technique | Impact |
|-----------|--------|
| Lazy import all apps | 60% reduction in initial bundle |
| Defer Python service boot | Shell visible in < 500ms |
| Warm up critical services | Voice service ready in 1s |
| SQLite connection pooling | 0-latency first query |
| Preload only essential data | Index loads in background |

## Runtime Optimization

- Virtual list for conversation history (10k+ items)
- Window pooling: max 8 windows, freeze oldest
- Memoize all React components with React.memo
- GPU-accelerated animations (CSS transforms, opacity)
- Image lazy loading + blur placeholder
- Debounce status bar updates (1s throttle)
- Worker threads for heavy computation (indexing, search)

## Memory Management

- Monitor heap usage, alert at 500MB
- Unmount off-screen windows after 5 min
- Clear unused caches every 10 min
- Snap heap on window close (global.gc() if available)
- Detect memory leaks via performance.memory

## Idle CPU

| State | Target CPU | Actions |
|-------|------------|---------|
| Active | < 10% | Normal |
| Idle (30s) | < 5% | Throttle animations |
| Idle (5min) | < 2% | Suspend background apps |
| Idle (30min) | < 1% | Only shell + voice service active |

## Profiling

- Use Chrome DevTools for renderer profiling
- Use py-spy for Python service profiling
- Log frame drops (requestAnimationFrame drift > 50ms)
- Track IPC latency (target: < 5ms round trip)