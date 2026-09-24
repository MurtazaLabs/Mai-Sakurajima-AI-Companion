# Desktop Shell

## Architecture

```
ShellContainer (persistent, never unmounts)
  ├── Wallpaper (live, static, video, gradient)
  ├── WidgetLayer (transparent overlay)
  │     ├── ClockWidget
  │     ├── WeatherWidget
  │     ├── MemoryWidget
  │     └── CustomWidgets
  ├── DockLayer (absolute bottom)
  │     ├── PinnedApps
  │     ├── RunningApps
  │     ├── RecentApps
  │     └── VoiceIndicator
  ├── StatusBar (absolute top)
  │     ├── AIState (listening/thinking/speaking/idle/dreaming)
  │     ├── SystemStats (CPU, RAM, GPU)
  │     ├── Time
  │     └── Network, Mic, Battery
  ├── NotificationCenter (slide-in panel)
  └── CommandPalette (overlay, Ctrl+K)
```

## Key Properties

- Shell NEVER unmounts during app switching
- Wallpaper is its own layer, can animate (parallax, time-of-day shift)
- Widget layer supports third-party widgets via plugin system
- Dock is always visible unless in fullscreen app
- Status bar is always visible unless in fullscreen app
- Command palette opens as modal overlay, search is debounced

## Performance

- Shell components use React.memo() extensively
- Status bar updates throttle to 1s intervals
- Wallpaper uses CSS transforms (GPU accelerated) when animating
- Widgets suspend when off-screen (IntersectionObserver)