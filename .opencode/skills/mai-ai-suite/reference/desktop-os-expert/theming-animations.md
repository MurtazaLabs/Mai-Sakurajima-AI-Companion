# Theming / Animations

## Theme Engine

```typescript
interface Theme {
  id: string;
  name: string;
  type: 'dark' | 'light' | 'custom';
  colors: {
    background: string;
    surface: string;
    surfaceElevated: string;
    text: string;
    textSecondary: string;
    accent: string;
    accentHover: string;
    border: string;
    error: string;
    success: string;
    warning: string;
  };
  blur: {
    glass: number; // backdrop blur px
    modal: number;
    panel: number;
  };
  opacity: {
    glass: number;
    disabled: number;
    overlay: number;
  };
  font: {
    sans: string;
    mono: string;
    size: number;
  };
  animation: {
    duration: number; // global multiplier (0.5-2)
    reduced: boolean;
  };
}
```

## Animation Principles

- Duration: 300-500ms for most transitions (slower than typical web)
- Easing: cubic-bezier(0.4, 0, 0.2, 1) — iOS-like
- Avoid: bounce, elastic, spring for UI elements
- Purpose: communicate state changes, not impress

## Glassmorphism

- Use backdrop-filter: blur() for glass effect
- Semi-transparent backgrounds (rgba with 0.3-0.7 alpha)
- Subtle border (1px, low opacity) for glass edge definition
- Reduce blur on low-end GPUs (detect via navigator.hardwareConcurrency)

## Live Updates

- Theme changes apply immediately via CSS custom properties
- No page reload needed
- Animations respect prefers-reduced-motion
- Wallpaper changes animate via crossfade