# Memory Code Review

## Checklist

### Duplicate Writes
- [ ] Same data written to multiple stores unnecessarily
- [ ] Conversation written to both MemoryState and vault directly
- [ ] Entity created in graph and also stored as standalone file

### Timestamp Preservation
- [ ] `created_at` never overwritten
- [ ] `updated_at` always updated on modification
- [ ] Timezone consistent (UTC)
- [ ] Clock skew handled

### Metadata Preservation
- [ ] Source field populated
- [ ] Confidence tracked
- [ ] Importance scored
- [ ] Version incremented on updates

### Merge Correctness
- [ ] Merges check version before applying
- [ ] Conflicts flagged, not silently resolved
- [ ] History preserved on merge

### Graph Consistency
- [ ] No orphan nodes (edges reference valid nodes)
- [ ] Entity IDs are canonical
- [ ] No duplicate entities
- [ ] Relationship symmetry maintained

### Vault Synchronization
- [ ] Vault is derived from MemoryState, not written directly
- [ ] Only changed pages are rewritten
- [ ] Index.md reflects actual pages
- [ ] Log.md captures significant changes

## Architectural Drift Detection

Watch for:
- Direct vault writes bypassing compiler
- Memory categories used interchangeably (episodic → semantic)
- Runtime state cached in markdown
- Graph treated as primary storage instead of MemoryState
- Reflection logic duplicated in dreaming engine
- Conversation stored as raw text instead of extracted knowledge