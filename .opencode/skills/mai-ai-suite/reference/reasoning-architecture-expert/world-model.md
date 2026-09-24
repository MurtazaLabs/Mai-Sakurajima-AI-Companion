# World Model

## Internal Representation

```python
@dataclass
class WorldModelState:
    people: dict[str, PersonModel]
    relationships: dict[str, RelationshipModel]
    places: dict[str, PlaceModel]
    projects: dict[str, ProjectModel]
    events: list[EventModel]
    beliefs: list[Belief]
    current_time: datetime
    environment: EnvironmentState
```

## Continuous Updates

On each reasoning cycle:
1. Extract entities and relationships from conversation
2. Update existing models with new information
3. Detect contradictions and flag for resolution
4. Age old information (decay confidence)
5. Prune low-confidence information below threshold

## Belief System

Each belief has:
- Fact statement
- Confidence (0.0-1.0)
- Source (conversation, inference, reflection)
- First observed timestamp
- Last confirmed timestamp
- Confirmation count
- Contradictions (list of conflicting beliefs)

## Belief Updating

```python
def update_belief(existing: Belief, new_info: Fact, context) -> Belief:
    if existing.fact == new_info.fact:
        existing.confidence = min(1.0, existing.confidence + 0.1)
        existing.last_confirmed = now()
        existing.confirmation_count += 1
    elif contradicts(existing, new_info):
        existing.confidence *= 0.5
        existing.contradictions.append(new_info)
        # Flag for user resolution during dreaming
    return existing
```