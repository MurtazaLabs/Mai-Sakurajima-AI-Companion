# Mai OS Design System

> Design every interface before writing code. Use this document as the single source of truth for every visual decision. Never invent new styles or components.

---

## 1. Design Philosophy

Mai should feel calm.

Not futuristic. Not cyberpunk. Not Windows. Not macOS. Not Linux.

Mai should feel like speaking to another mind.

Every interface communicates:

- **Clarity** — nothing ambiguous, nothing hidden
- **Warmth** — dark but not cold, premium but not sterile
- **Intelligence** — every pixel signals capability
- **Confidence** — no unnecessary decoration, no hesitation in layout
- **Simplicity** — the minimum interface to do the job

No visual noise.

Every animation has purpose.

Every component breathes.

The user should never feel overwhelmed.

This changes everything.

---

## 2. Color System

### Palette

| Token | Value | Usage |
|-------|-------|-------|
| Primary Background | `#0F1117` | desktop, page backgrounds |
| Secondary | `#171A21` | sidebars, panels, surfaces |
| Panels | `#20252F` | cards, elevated surfaces |
| Accent | `#5E81F4` | primary actions, links, active states |
| Accent Hover | `#7296FF` | hover states for accent elements |
| Positive | `#49D17D` | success, online, confirmed |
| Warning | `#F5B642` | caution, pending, attention |
| Danger | `#F45D5D` | errors, destructive actions, offline |
| Text Primary | `#F4F6F8` | headings, body content |
| Text Secondary | `#A9B0BD` | captions, metadata, placeholders |
| Borders | `rgba(255,255,255,0.06)` | all dividers, outlines, strokes |

### Usage Rules

- Accent on primary background: use directly
- Accent on secondary/panel backgrounds: increase brightness if needed
- Never use raw white (`#FFFFFF`) as background
- Text Secondary for anything below 14px
- Borders always use the defined border token — never custom colors

---

## 3. Typography

### Font Family

`system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif`

No custom font files. No web font imports. System stack only.

### Size Scale

| Token | Size | Weight | Usage |
|-------|------|--------|-------|
| Display | 48px | 700 | page hero, login welcome |
| Heading | 32px | 600 | page titles, section headers |
| Section | 24px | 600 | dashboard card titles, modal headers |
| Body | 16px | 400 | paragraphs, chat messages, settings |
| Caption | 13px | 400 | secondary info, timestamps, metadata |
| Small | 12px | 500 | labels, badges, stats, sidebar text |

### Line Height

- All text: **1.6** line height
- Headings: **1.2** line height

### Font Weights

700 — Display only
600 — Headings, Section titles, button labels
500 — Small labels, active nav items
400 — Body, captions, everything else

### Mono

`'Consolas', 'Monaco', 'Courier New', monospace`

Used for: code blocks, terminal output, raw data displays.

---

## 4. Spacing System

Every measurement uses the scale. **No exceptions.**

### Scale

```
4px   8px   12px   16px   24px   32px   48px   64px
```

### Mappings

| Context | Value |
|---------|-------|
| Page margin | 24px |
| Card padding | 16px |
| Section gap | 24px |
| Grid gap | 16px |
| Element inset | 12px |
| Tight grouping | 8px |
| Compact | 4px |

### Rules

- Never use odd values (no 17px, 31px, 29px)
- Never use values outside the scale
- Stack spacing: prefer 16px or 24px between stacked elements
- Inline spacing: prefer 8px or 12px between inline elements

---

## 5. Component Library

### Button

| Property | Value |
|----------|-------|
| Height | 44px |
| Padding | 0 24px |
| Radius | 12px |
| Background | Accent (`#5E81F4`) |
| Hover | translateY(-1px), brighter background |
| Shadow | Small |
| Transition | 200ms ease-out |
| Font Weight | 600 |
| Font Size | 16px |

### Cards

| Property | Value |
|----------|-------|
| Padding | 16px |
| Radius | 16px |
| Border | 1px solid Borders |
| Background | Panels (`#20252F`) |
| Hover | subtle border lighten |
| Shadow | Small |

### Input

| Property | Value |
|----------|-------|
| Height | 48px |
| Radius | 12px |
| Background | Secondary (`#171A21`) |
| Border | 1px solid Borders |
| Focus | accent glow (box-shadow) |
| Padding | 0 16px |
| Font | 16px |

### Sidebar

| Property | Value |
|----------|-------|
| Width | 280px |
| Background | Secondary |
| Border | right 1px Borders |
| Icons | 20px, centered |
| Labels | 14px |
| Item height | 44px |

### Top Bar

| Property | Value |
|----------|-------|
| Height | 64px |
| Background | Secondary |
| Border | bottom 1px Borders |
| Content | clock, status, AI state, notifications |
| Padding | 0 24px |

---

## 6. Motion Language

### Timing

| Context | Duration | Easing |
|---------|----------|--------|
| Hover | 100-150ms | ease-out |
| Page transition | 250ms | cubic-bezier(.2,.8,.2,1) |
| Modal open/close | 300ms | ease-out |
| Notification | 200ms | ease-out |
| Window open | 200ms | ease-out |

### Never use

- 0.8s animations
- linear easing
- bounces or elastic effects
- parallax or continuous background animation

### Always use

- `ease-out` for most transitions
- `cubic-bezier(.2,.8,.2,1)` for page/modal transitions
- 150ms / 200ms / 250ms / 300ms only

### Rules

- Hover: 100-150ms
- Page: 250ms
- Modal: 300ms
- Notification: 200ms

---

## 7. Glassmorphism

| Property | Value |
|----------|-------|
| Backdrop Blur | 16px |
| Transparency | 85% |
| Shadow | 0 8px 24px rgba(0,0,0,0.18) |
| Border | 1px solid rgba(255,255,255,0.06) |

Used for: modals, taskbars, floating panels, start menus.

---

## 8. Icon System

### Choice

**Lucide Icons** — one library, never mix.

### Rules

- Only Lucide icons
- 20px default size
- 16px for inline/small contexts
- 24px for standalone actions
- Stroke width: 2 (default)
- Color: currentColor or Text Secondary
- Never combine with other icon libraries

---

## 9. Corner Radius

| Context | Value |
|---------|-------|
| Buttons | 12px |
| Cards | 16px |
| Panels | 20px |
| Dialogs | 24px |
| Inputs | 12px |

---

## 10. Shadows

| Level | Value | Usage |
|-------|-------|-------|
| Small | `0 1px 3px rgba(0,0,0,0.3)` | buttons, cards |
| Medium | `0 4px 12px rgba(0,0,0,0.25)` | dropdowns, popovers |
| Large | `0 8px 32px rgba(0,0,0,0.4)` | modals, windows |

No random shadows.

---

## 11. Layout Rules

### Desktop Structure

```
┌──────────┬──────────────────────┬──────────┐
│          │                      │          │
│ Sidebar  │     Content          │ Inspector │
│ 280px    │     (flex 1)         │ 320px    │
│          │                      │          │
├──────────┴──────────────────────┴──────────┤
│              Top Bar (64px)                 │
└────────────────────────────────────────────┘
```

### Rules

- Page margin: 24px
- Grid gap: 24px
- Sidebar: fixed 280px
- Content: flex: 1, min-width: 0
- Inspector: fixed 320px (optional, collapsible)

---

## 12. AI Behavior

Mai isn't a chatbot. Mai is a presence.

### Idle

- Breathing animation (subtle scale pulse on avatar)
- Small glow pulse on status indicator
- Soft ambient particle movement

### Thinking

- Gradient shift on accent elements
- Rotating rings or progress pulse
- Typing indicator with smooth opacity fade

### Speaking

- Soft waveform animation on avatar
- Avatar glow intensifies
- Voice ripple effect

### Listening

- Microphone icon expands slightly
- Ambient circle pulse
- Blue pulse ring around avatar

---

## 13. Prompt Library

When generating UI code, always prepend:

```
Follow design_system.md.
Use only defined components.
Use the spacing system.
Keep a calm AI aesthetic.
Avoid clutter.
Maximum 5 primary sections per page.
Responsive.
Animations under 300ms.
No gradients stronger than the design system.
Use Lucide icons only.
```

---

## 14. Image Style Guide

### Illustration Style

- Soft
- Minimal
- Semi-realistic
- No anime
- No cyberpunk
- No neon
- No stock photos
- Warm ambient lighting
- Rounded shapes
- Muted colors
- Premium software aesthetic

### Avatar

- Elegant AI
- Friendly, confident, intelligent
- Not human, not robot — abstract
- Soft lighting
- Minimal geometry

### Backgrounds

- Dark
- Subtle gradients
- Glass effects
- Ambient particles
- Depth without noise

---

## 15. Component Gallery

All components are demonstrated in `gallery/`. Every future page reuses those components — never invent new ones.
