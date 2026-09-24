# Caching

## Cache Levels

| Level | Name | Location | Latency | Capacity | Persistence |
|-------|------|----------|---------|----------|-------------|
| L1 | Hot | GPU VRAM | < 1µs | 1 GB | No |
| L2 | Warm | System RAM | < 100µs | 8 GB | No |
| L3 | Cold | Disk (mmap) | < 10ms | 100 GB | Yes |

## Cache Types

| Cache | Key | Value | Size | Eviction |
|-------|-----|-------|------|----------|
| Prompt cache | (model_id, text_hash) | Precomputed KV | 100 MB-1 GB | LRU, TTL=60s |
| Embedding cache | (model_id, text_hash) | Embedding vector | 10 MB-100 MB | LRU, TTL=3600s |
| Tokenizer cache | (model_id, text) | Token IDs | 1 MB-10 MB | LRU, TTL=300s |
| Model cache | model_id | Loaded model | Full model size | Memory pressure |
| Inference cache | (model_id, prompt_hash, params) | Generated output | 10 MB-100 MB | LRU, TTL=30s |
| Knowledge cache | query_hash | Retrieved chunks | 10 MB-50 MB | LRU, TTL=600s |

## Cache Architecture

```python
class MultiLevelCache:
    def __init__(self):
        self.l1 = LRUCache(capacity_gb=1)  # GPU
        self.l2 = LRUCache(capacity_gb=8)  # RAM
        self.l3 = DiskCache(capacity_gb=100)  # SSD
    
    async def get(self, key, level=1):
        if level <= 1 and key in self.l1:
            return self.l1.get(key)
        if level <= 2 and key in self.l2:
            val = self.l2.get(key)
            self.l1.put(key, val)  # promote
            return val
        if level <= 3 and await self.l3.exists(key):
            val = await self.l3.get(key)
            self.l2.put(key, val)  # promote
            return val
        return None
    
    async def put(self, key, value, level=1, ttl=60):
        if level <= 1:
            self.l1.put(key, value, ttl=ttl)
        if level <= 2:
            self.l2.put(key, value, ttl=ttl * 2)
        self.l3.put(key, value, ttl=ttl * 10)
```

## Invalidation

- Explicit: `cache.invalidate(pattern)` clears all matching keys
- Time-based: TTL per entry, auto-evict on expiry
- Memory pressure: LRU eviction when capacity exceeded
- Model change: clear all caches for model_id when model version changes
- Event-driven: subscribe to EventBus for invalidation events