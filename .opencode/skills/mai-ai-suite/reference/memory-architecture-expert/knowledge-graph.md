# Knowledge Graph

## Entity Types

| Type | Example | Canonical ID Pattern |
|------|---------|---------------------|
| Person | "Sam", "Alice" | person/username_hash |
| Place | "New York", "Home" | place/name_lowercase |
| Project | "Rust Compiler", "Mai OS" | project/name_lowercase |
| Technology | "Rust", "Python", "CUDA" | tech/name_lowercase |
| Organization | "OpenAI", "Google" | org/name_lowercase |
| Event | "Trip to Japan 2025" | event/date_description |
| Concept | "Functional Programming" | concept/slug |
| Book | "The Pragmatic Programmer" | book/author_title_slug |
| Movie | "Rascal Does Not Dream" | movie/title_slug |
| Goal | "Learn Rust" | goal/slug |

## Relationship Types

| Type | Source | Target | Weight Decay |
|------|--------|--------|-------------|
| knows | Person | Person | Slow |
| works_on | Person | Project | Medium |
| visited | Person | Place | Fast |
| owns | Person | Technology | Medium |
| likes | Person | Concept | Slow |
| dislikes | Person | Concept | Slow |
| related_to | Any | Any | Slow |
| mentioned_with | Any | Any | Fast |
| created | Person | Project | None |
| depends_on | Project | Technology | None |
| located_in | Place | Place | None |

## Dedup Strategy

- Same canonical ID → merge attributes, sum confidence
- Different IDs, same entity → detect via embedding similarity > 0.9 + relationship overlap > 0.7
- Merged entities redirect old ID to canonical ID
- Deleted entities soft-delete (marked as deprecated, not removed)