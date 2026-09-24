# CPU / Resource Scheduler

## Priority Levels

| Priority | Components | Preempts | Preemptable By |
|----------|-----------|----------|-----------------|
| 0 (highest) | Wake word, VAD | everything | nothing |
| 1 | Speech-to-text | 2-6 | wake word, VAD |
| 2 | LLM inference | 3-6 | 0-1 |
| 3 | Text-to-speech | 4-6 | 0-2 |
| 4 | Memory retrieval, embeddings | 5-6 | 0-3 |
| 5 | Knowledge indexing | 6 | 0-4 |
| 6 (lowest) | Dreaming, maintenance, background | nothing | everything |

## Thread Pool

- Main thread: orchestrator, never blocks
- Worker threads: 1-2 per model type, pooled
- Audio thread: dedicated, real-time priority on supported platforms
- I/O threads: async file reads, network (offline updates)

Thread count formula:
```
worker_threads = max(1, cpu_count() - 2)  # leave 2 cores for OS + audio
```

## Affinity

On systems with heterogeneous cores (P-cores / E-cores):
- P-cores: voice pipeline, LLM inference
- E-cores: background tasks, maintenance, I/O
- OS-controlled: health monitor, telemetry

## Background Pause

When any priority 0-1 task starts:
1. Pause all priority 5-6 tasks immediately
2. Complete current inference for priority 2-4 (no new tasks)
3. Resume background when priority 0-1 queue empties

## Queue Implementation

```
class PriorityQueue:
    def __init__(self):
        self.queues = [collections.deque() for _ in range(7)]
    
    def enqueue(self, task, priority):
        self.queues[priority].append(task)
    
    def dequeue(self):
        for q in self.queues:
            if q:
                return q.popleft()
        return None
    
    def cancel(self, task_id):
        for q in self.queues:
            q[:] = [t for t in q if t.id != task_id]
```