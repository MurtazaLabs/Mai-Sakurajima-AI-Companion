# Command Palette / Global Search

## Trigger

- Keyboard: Ctrl+K (Cmd+K on macOS)
- Click: Search icon in status bar
- Voice: "Hey Mai, search..."

## Index

```
index = {
  apps: AppManifest[],
  memories: MemoryIndex,
  conversations: ConversationIndex,
  files: FileIndex,
  commands: Command[],
  settings: Setting[],
  tools: Tool[],
  recent: RecentActivity[]
}
```

Built on app startup, updated incrementally. Stored in SQLite with FTS5 for full-text search.

## Results

- Displayed in a glass card overlay
- Grouped by category with section headers
- Keyboard navigable (arrow keys, enter to select)
- Fuzzy matching on all indexed terms
- Results appear within 50ms of keypress (debounced input)

## Commands

Built-in commands:
- `/theme` — switch theme
- `/settings` — open settings panel
- `/memory search:` — search memories
- `/voice` — toggle voice mode
- `/dream` — trigger dreaming cycle
- `/debug` — open developer console
- `/quit` — quit Mai
- `/restart` — restart services

## Future

- Plugin commands: registered by extensions
- Custom commands: user-defined macros
- AI-powered: natural language → command matching