# Layout System

## Desktop Structure

```
┌──────────┬──────────────────────────────────┬──────────┐
│          │                                  │          │
│ Sidebar  │          Content                 │ Inspector│
│ 280px    │        (flex: 1)                 │ 320px    │
│          │        24px margin               │ optional │
│          │        24px gap                   │          │
├──────────┴──────────────────────────────────┴──────────┤
│                     Top Bar (64px)                      │
└────────────────────────────────────────────────────────┘
```

## Page Template

```
┌─────────────────────────────────────────────────────────┐
│  Top Bar (64px)                                         │
├──────────┬──────────────────────────────────────────────┤
│ Sidebar  │  Content Area                                │
│ 280px    │                                              │
│          │  ┌── Page Header ──────────────────────────┐ │
│          │  │  Heading (32px) + action button          │ │
│          │  └──────────────────────────────────────────┘ │
│          │                                              │
│          │  ┌── Section ─────────────────────────────┐ │
│          │  │  Section title (24px)                   │ │
│          │  │  Grid (auto-fill, 24px gap)             │ │
│          │  │  ┌─────┐ ┌─────┐ ┌─────┐               │ │
│          │  │  │card │ │card │ │card │               │ │
│          │  │  └─────┘ └─────┘ └─────┘               │ │
│          │  └──────────────────────────────────────────┘ │
│          │                                              │
│          │  24px margin on each side                     │
│          │  24px gap between sections                    │
└──────────┴──────────────────────────────────────────────┘
```

## Grid System

- Dashboard grid: `repeat(auto-fill, minmax(300px, 1fr))` gap 24px
- Settings grid: `repeat(2, 1fr)` gap 24px
- Stat list: stacked, 16px gap between items

## Responsive

| Breakpoint | Behavior |
|------------|----------|
| >1200px | Full layout: sidebar + content + optional inspector |
| 768-1200px | Sidebar collapses to icon-only (64px) |
| <768px | Sidebar hidden, hamburger menu. Single column grids. |
| <480px | Sidebar overlay. Full-width cards. Stacked forms. |

## Rules

- 24px margin from content area edges
- 24px gap between grid items
- 24px gap between page sections
- 16px card padding (inner)
- 24px top bar padding (horizontal)
- Never use margins smaller than 16px for layout structure
