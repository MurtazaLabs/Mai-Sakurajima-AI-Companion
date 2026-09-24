# Window Manager

## Window Types

| Type | Resizable | Floating | Tabbed | Persist | Use Case |
|------|-----------|----------|--------|---------|----------|
| Standard | Yes | Yes | Yes | Yes | Apps, settings |
| Dialog | No | Yes | No | No | Modals, prompts |
| Panel | Yes | Yes | No | Yes | Side panels, devtools |
| Fullscreen | No | No | No | Yes | Immersive apps |
| Pinned | No | Always | No | Yes | Widgets, mini-player |
| Notification | No | Auto-dismiss | No | No | Toasts |

## Snap Layouts

Support Windows 11-style snap:
- Left half, right half
- Four quadrants
- Center 70%
- Custom ratios (future)

## State Persistence

```typescript
interface WindowState {
  id: string;
  appId: string;
  type: WindowType;
  bounds: { x, y, width, height };
  isMinimized: boolean;
  isMaximized: boolean;
  isFullscreen: boolean;
  zIndex: number;
  tabId?: string;
  metadata: Record<string, unknown>;
}
```

Stored in SQLite, restored on app launch.

## Multi-Monitor

- Track which monitor each window is on
- Snap respects monitor boundaries
- Fullscreen fills current monitor
- DnD across monitors via Electron's screen API