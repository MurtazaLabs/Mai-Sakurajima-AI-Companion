# UI Prompts & Copy

## Design Generation Prompt

When creating any new UI page, prepend this prompt to every request:

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

## Copy Guidelines

### Voice
- Calm, confident, warm
- Sentence case (not Title Case)
- Concise: 1-3 words for labels, 1-2 sentences for descriptions
- No emojis in UI copy
- No exclamation marks in system messages

### Chat
- **Welcome**: "Hello, I'm Mai. Your AI companion."
- **Thinking**: "Mai is thinking"
- **Status ready**: "Ready"
- **Status booting**: "Booting..."
- **Status offline**: "Offline"
- **Send button**: "Send"
- **Error prefix**: "Error: {message}"

### Dashboard
- **Title**: "Dashboard"
- **Refresh**: "Refresh"
- **Graph empty**: "No graph data"
- **Loading**: "Loading..."
- **Auto-refresh hint**: "Auto-refreshing every 5s"

### Desktop (OS)
- **Start menu header**: "Mai"
- **Login placeholder**: "Enter your name"
- **Login button**: "Sign In"
- **Window controls**: close, minimize, maximize (no labels)

### Buttons
- Primary actions: single word ("Save", "Send", "Delete", "Create")
- Secondary actions: "Cancel", "Back", "Skip"
- Destructive: "Delete", "Remove", "Clear"

### Notifications
- Positive: "Saved", "Updated", "Connected"
- Warning: "{n} items need attention"
- Error: "Something went wrong. Try again."
- Auto-dismiss: 3 seconds
