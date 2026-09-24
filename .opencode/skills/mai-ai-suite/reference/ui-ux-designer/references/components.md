# Component Library

All components are defined here. Every future page uses only these components. See `gallery/` for visual examples.

---

## Button

- Height: 44px
- Padding: 0 24px
- Radius: 12px
- Background: `#5E81F4`
- Hover: translateY(-1px)
- Transition: 200ms ease-out
- Font: 600, 16px

### Variants
- Primary (default) — accent fill
- Secondary — transparent, border only
- Ghost — no border, no fill
- Danger — danger fill
- Icon — square, icon only

---

## Card

- Padding: 16px
- Radius: 16px
- Background: `#20252F`
- Border: 1px `rgba(255,255,255,0.06)`

### Slots
- Header (optional icon + title)
- Body
- Footer (optional actions)

---

## Input

- Height: 48px
- Radius: 12px
- Background: `#171A21`
- Border: 1px `rgba(255,255,255,0.06)`
- Focus: accent box-shadow glow
- Padding: 0 16px
- Font: 16px
- Label: above, Caption weight 500

---

## Sidebar

- Width: 280px
- Background: `#171A21`
- Right border: 1px `rgba(255,255,255,0.06)`
- Item height: 44px
- Icon: 20px
- Label: 14px, 500 weight
- Active: accent left border + tint

---

## Top Bar

- Height: 64px
- Background: `#171A21`
- Bottom border: 1px `rgba(255,255,255,0.06)`
- Padding: 0 24px
- Contents: clock, status dot, AI state label, notification bell

---

## Message Bubble (Chat)

- Max width: 75%
- Radius: 12px (user), 12px (mai)
- User: `#5E81F4` bg, white text, right-aligned
- Mai: `#20252F` bg, `#F4F6F8` text, left-aligned
- Timestamp: Small, Text Secondary
- Animation: fadeIn 200ms

---

## Modal / Dialog

- Radius: 24px
- Background: Panels with 16px blur, 85% opacity
- Shadow: Large
- Backdrop: `rgba(0,0,0,0.6)`
- Animation: 300ms ease-out

---

## Notification / Toast

- Background: Panels with blur
- Border: 1px `rgba(255,255,255,0.06)`
- Radius: 12px
- Shadow: Medium
- Duration: auto-dismiss 3s
- Animation: slideIn 200ms

---

## Progress Bar

- Height: 6px
- Background: Secondary
- Radius: 3px
- Fill: Accent (`#5E81F4`)
- Variants: Positive, Warning, Danger
- Transition: width 0.5s ease

---

## Typing Indicator

- Three dots
- Size: 6px each
- Color: Text Secondary
- Animation: bounce 1.4s with staggered delay
- Label: "Mai is thinking"

---

## Status Dot

- Size: 8px
- Online: `#49D17D` with glow
- Booting: Warning with 1.5s pulse
- Offline: `#F45D5D`

---

## Badge

- Radius: 999px
- Padding: 2px 8px
- Font: 12px, 500 weight
- Background: Accent at 15% opacity
- Color: Accent

---

## Avatar

- Size: 96px (login), 48px (header), 32px (inline)
- Radius: 50%
- Border: 2px `rgba(255,255,255,0.06)`
- Abstract AI style illustration
