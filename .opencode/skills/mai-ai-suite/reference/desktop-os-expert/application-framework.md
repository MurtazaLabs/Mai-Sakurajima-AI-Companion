# Application Framework

## App Lifecycle

```
Registered → LazyLoaded → Mounted → Active → Background → Suspended → Unmounted
```

| State | UI | Memory | CPU |
|-------|----|--------|-----|
| Registered | None | 0 | 0 |
| LazyLoaded | None | Bundle code | 0 |
| Mounted | Rendered | Bundle + state | Active |
| Active | Focused | Full | Full |
| Background | Hidden | Full | Reduced |
| Suspended | Hidden | State only (snapshot) | 0 |
| Unmounted | None | 0 | 0 |

## App Registration

```typescript
interface AppManifest {
  id: string;
  name: string;
  icon: string;
  description: string;
  component: () => Promise<React.ComponentType>; // lazy import
  window: { defaultWidth, defaultHeight, minWidth, minHeight };
  keywords: string[]; // for command palette search
  permissions: string[];
}
```

## State Restoration

- Window state saved on close (bounds, tabs, scroll position)
- App state saved on background (form inputs, selected items)
- Session restored on app launch
- Crash recovery: last known good state, no data loss