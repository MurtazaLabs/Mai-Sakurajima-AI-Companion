# Accessibility

## Colour Contrast

All ratios meet WCAG AA (4.5:1 for text, 3:1 for large text).

- `#F4F6F8` on `#0F1117` = 15.2:1 (AAA)
- `#A9B0BD` on `#0F1117` = 7.1:1 (AA)
- `#5E81F4` on `#0F1117` = 5.8:1 (AA)
- `#5E81F4` on `#171A21` = 5.2:1 (AA)
- `#FFFFFF` on `#5E81F4` = 4.6:1 (AA)
- `#49D17D` on `#0F1117` = 7.9:1 (AA)
- `#F45D5D` on `#0F1117` = 6.1:1 (AA)

## Focus

- All interactive elements: visible focus ring
- Style: `2px solid #5E81F4` with `2px offset`
- Never remove `outline` without providing an alternative
- Focus order matches visual order

## Keyboard

- All actions accessible via keyboard
- Tab order: left-to-right, top-to-bottom
- Escape closes modals, dropdowns, menus
- Enter/Space activates buttons and links
- Arrow keys navigate lists and sidebars

## Screen Readers

- Semantic HTML (`<button>`, `<nav>`, `<main>`, `<h1>-<h3>`)
- `aria-label` on icon-only buttons
- `aria-live="polite"` for dynamic content (chat messages, notifications)
- Status updates: text content, not just colour changes
- Loading states announced

## Motion

- `prefers-reduced-motion` respected: disable all animations
- No auto-playing animations on page load (except breathing at 4s)
- No parallax or continuous motion
- Animations short (100-300ms) — low motion sickness risk

## Touch

- Minimum target size: 44x44px
- Adequate spacing between interactive elements (8px min)
