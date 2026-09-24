# Model Lifecycle

## States

```
NOT_LOADED ──→ LOADING ──→ INITIALIZING ──→ WARM_UP ──→ READY
  ↑                                                          │
  │                                                          ↓
  │  ARCHIVED ←── UNLOADED ←── CACHED ←── IDLE ←── BUSY
  │                    ↑                      ↑
  └────────────────────┴──────────────────────┘
```

| State | Description | Memory | GPU |
|-------|-------------|--------|-----|
| NOT_LOADED | Model known but not loaded | 0 | 0 |
| LOADING | Loading from disk/network | growing | 0 |
| INITIALIZING | Allocating buffers, warming cache | peak | peak |
| WARM_UP | Running dummy inference | full | full |
| READY | Available for inference | full | full |
| BUSY | Currently running inference | full | full |
| IDLE | Loaded but unused | full | full |
| CACHED | Resident in RAM, GPU freed | model size | 0 |
| UNLOADED | Memory freed, metadata kept | 0 | 0 |
| ARCHIVED | Removed from registry | 0 | 0 |

## Loading Strategies

| Strategy | When | Latency | Memory |
|----------|------|---------|--------|
| Lazy | On first use | 1-5s (cold) | minimal |
| Background | At boot or after idle | 0s perceived | gradual |
| Warm | Pre-loaded during startup | <1s | full | 
| Cold | Loaded on demand from disk | 1-30s | fresh |
| Pinned | Always resident, never evicted | 0s | permanent |

## Transitions

- LOADING → INITIALIZING: weights loaded, tensors on device
- INITIALIZING → WARM_UP: buffers allocated, running first pass
- WARM_UP → READY: dummy inference complete, model is hot
- READY → BUSY: inference started
- BUSY → READY: inference complete
- READY/IDLE → CACHED: memory pressure, GPU freed, RAM retained
- CACHED → READY: model needed, reload from RAM (fast)
- CACHED → UNLOADED: RAM needed, full eviction
- UNLOADED → NOT_LOADED: metadata kept for quick re-registration
- UNLOADED → ARCHIVED: model removed, must re-register

## Unloading Policy

Triggered by:
1. Idle timeout (configurable per model, default: 300s)
2. Memory pressure (threshold: 90% VRAM / 80% RAM)
3. Priority preemption (higher priority model needs resources)
4. Manual unload request

When unloading:
1. First move to CACHED (free GPU but keep in RAM)
2. If still needed, move to UNLOADED (free RAM)
3. Log the unload with reason and duration loaded