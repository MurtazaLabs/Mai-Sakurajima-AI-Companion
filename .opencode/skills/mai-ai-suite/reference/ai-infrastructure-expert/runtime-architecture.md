# Runtime Architecture

## Core Components

```
ModelRegistry
  ├── register(model_metadata)
  ├── get(name, version, runtime)
  ├── list(status, capability, device)
  └── unregister(name)

ModelLifecycleManager
  ├── load(model_id, strategy)
  ├── unload(model_id, reason)
  ├── pin(model_id)
  ├── cache(model_id, ttl)
  └── warm_up(model_id)

ResourceScheduler
  ├── submit(task, priority)
  ├── cancel(task_id)
  ├── pause_priority(below)
  └── resume()

InferenceQueue
  ├── enqueue(request, priority)
  ├── dequeue() -> batch|single
  ├── cancel(token)
  └── stats()

CacheManager
  ├── get(key, level)
  ├── put(key, value, level, ttl)
  ├── invalidate(pattern)
  └── evict(level, bytes_needed)

HealthMonitor
  ├── report(model_id, status)
  ├── alert(condition, level)
  └── history(model_id, timeframe)
```

## Data Flow

```
Request → DeviceDetector → ModelSelector → ResourceScheduler
  → (cache hit?) → InferenceQueue → ModelRunner → Response
  → CacheManager.update() → HealthMonitor.report()
```

## Async Boundaries

- All components communicate via async queues
- ModelRunner yields tokens via async generator
- HealthMonitor runs on background tick (1s interval)
- CacheManager eviction runs on background trigger (memory pressure)

## Key Decisions

- **ModelRegistry is in-memory dict + optional JSON persistence**. Fast lookups, no DB dependency.
- **Lifecycle states are enum with guarded transitions**. Invalid transitions raise clear errors.
- **ResourceScheduler uses priority queue with preemption**. Higher priority cancels lower priority tokens.
- **InferenceQueue supports batching for compatible models** (e.g., embedding models batch multiple texts).
- **HealthMonitor is pull-based**. Components push status updates, monitor aggregates.