# Motion Language

## Timing Reference

| Animation | Duration | Easing |
|-----------|----------|--------|
| Button hover | 100ms | ease-out |
| Card hover | 150ms | ease-out |
| Sidebar item | 100ms | ease-out |
| Page transition | 250ms | cubic-bezier(.2,.8,.2,1) |
| Modal open | 300ms | ease-out |
| Notification slide | 200ms | ease-out |
| Window open | 200ms | ease-out |
| Progress bar | 500ms | ease |

## Keyframes

### fadeIn
```css
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}
```
Messages: 200ms. Page sections: 250ms.

### bounce (typing dots)
```css
@keyframes bounce {
  0%, 80%, 100% { transform: scale(0.6); }
  40% { transform: scale(1); }
}
```
Three dots at 1.4s total, staggered 0/0.16s/0.32s delay.

### pulse (status dot)
```css
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}
```
1.5s infinite. Only for booting/connecting states.

### slideIn (toast)
```css
@keyframes slideIn {
  from { transform: translateX(100%); opacity: 0; }
  to { transform: translateX(0); opacity: 1; }
}
```
Notifications: 200ms.

### breathing (AI idle)
```css
@keyframes breathing {
  0%, 100% { transform: scale(1); opacity: 0.8; }
  50% { transform: scale(1.02); opacity: 1; }
}
```
4s infinite loop. Subtle — almost imperceptible.

### Thinking glow
```css
@keyframes thinkGlow {
  0%, 100% { box-shadow: 0 0 8px rgba(94,129,244,0.2); }
  50% { box-shadow: 0 0 20px rgba(94,129,244,0.4); }
}
```

## Rules

- No animation longer than 500ms
- No linear easing
- No bouncing or elastic effects
- No parallax
- No continuous background animations (exception: breathing at 4s)
- Hover effects: 100-150ms only
- Reduce motion: respect `prefers-reduced-motion`
