# Notifications

## Design

- Glass card with backdrop blur
- Soft appear/disappear animation (opacity + translateY)
- Auto-dismiss after 5s (configurable per type)
- Swipe to dismiss
- Click to open related app
- Right-click for actions menu

## Types

| Type | Priority | Persist | Sound | Example |
|------|----------|---------|-------|---------|
| Info | Low | No | No | "Memory consolidation complete" |
| Success | Low | No | Soft | "Goal completed: Learn Rust" |
| Warning | Medium | Yes | Yes | "Low disk space (15% remaining)" |
| Error | High | Yes | Yes | "Voice service crashed, restarting..." |
| Achievement | Low | Yes | Special | "1000 conversations with Mai" |

## Notification Center

- Slide-in panel from right edge
- Groups notifications by app
- "Clear all" button
- Per-app mute settings
- History (last 30 days, stored in SQLite)

## Priority Levels

| Level | Behavior |
|-------|----------|
| Low | Toast only, no center entry |
| Medium | Toast + center entry, auto-dismiss |
| High | Toast + center entry, persists until dismissed |
| Critical | Toast + center entry + sound, persists, re-alerts every 60s |