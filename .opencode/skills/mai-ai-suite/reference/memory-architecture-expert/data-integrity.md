# Data Integrity

## Provenance Tracking

Every memory entry must track:
- `id`: unique identifier (UUID)
- `created_at`: first creation timestamp
- `updated_at`: last modification timestamp
- `source`: what created this (conversation, reflection, dream, import)
- `confidence`: 0.0-1.0, how sure are we
- `importance`: 0.0-1.0, how important is this
- `version`: integer, incremented on each update
- `history`: list of previous values (for audit)

## Merge Rules

When merging two entries with same ID:
1. Take the higher `version`
2. If versions equal, take the later `updated_at`
3. Merge `confidence`: average of both
4. Merge `importance`: max of both
5. Concatenate `history` from both
6. Never overwrite `created_at`
7. Update `updated_at` to now

## Dedup Prevention

- Before creating any memory, search for existing match
- Match criteria: same entity + same fact + confidence > 0.8
- If match found: reinforce (increment confidence, update timestamp)
- If no match: create new with unique ID
- Batch check before bulk operations

## Integrity Checklist

- [ ] All entities have canonical IDs
- [ ] All timestamps are UTC
- [ ] No dangling entity references
- [ ] No duplicate IDs
- [ ] Graph edges reference valid nodes
- [ ] Vault pages match MemoryState
- [ ] Confidence values in [0, 1]
- [ ] Importance values in [0, 1]