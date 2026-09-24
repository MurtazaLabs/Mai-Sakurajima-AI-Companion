# MemoryState

## Schema

```python
@dataclass
class MemoryState:
    identity: IdentityModel          # self-description, name, personality traits
    preferences: PreferencesModel    # likes, dislikes, communication style
    relationships: RelationshipsModel  # per-person trust, closeness, history
    projects: dict[str, ProjectModel]  # active and completed projects
    people: dict[str, PersonModel]     # known people with profiles
    places: dict[str, PlaceModel]      # known locations
    goals: list[GoalModel]             # active, pending, completed goals
    dreams: list[DreamModel]           # synthesized ideas and hypotheses
    knowledge: KnowledgeModel          # general facts about the world
    reflections: list[ReflectionModel] # insights discovered
    statistics: StatisticsModel        # conversation counts, duration, etc.
    conversation_summaries: list[SummaryModel]  # per-session summaries
    recent_context: RecentContext       # last N conversation turns
    working_memory: WorkingMemory       # current session state
    active_tasks: list[TaskModel]       # in-progress tasks
```

## Merge Semantics

When merging new data into MemoryState:
- **Identity**: Replace if newer and more complete
- **Preferences**: Add new, preserve existing unless explicitly changed
- **Relationships**: Update scores, preserve history
- **Projects**: Update progress, preserve metadata
- **Knowledge**: Add new facts, flag contradictions for resolution
- **Reflections**: Append, never replace

## Conflict Resolution

When two values conflict:
1. Prefer explicitly stated over inferred
2. Prefer more recent (within same source)
3. Prefer higher confidence
4. Prefer direct statement over indirect
5. Flag unresolved conflicts for user resolution during dreaming

## Persistence

MemoryState is persisted to JSON on every meaningful update. Auto-save after each conversation turn. Full save every 5 minutes during idle. Corrupted state recovers from last valid save.