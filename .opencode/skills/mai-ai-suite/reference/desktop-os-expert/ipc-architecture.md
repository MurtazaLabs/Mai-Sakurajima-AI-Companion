# IPC Architecture

## Layers

```
Renderer (React)
  ↓ window.electronAPI (typed, context bridge)
Preload (minimal, audited)
  ↓ ipcRenderer.invoke / on
Main Process
  ↓ child_process
Python Services
```

## Typed API

```typescript
// contextBridge.exposeInMainWorld('electronAPI', {
//   chat: {
//     send: (message: string) => ipcRenderer.invoke('chat:send', message),
//     onToken: (cb: (token: string) => void) => {
//       ipcRenderer.on('chat:token', (_, token) => cb(token));
//     }
//   },
//   window: {
//     minimize: () => ipcRenderer.invoke('window:minimize'),
//     maximize: () => ipcRenderer.invoke('window:maximize'),
//     close: () => ipcRenderer.invoke('window:close'),
//   }
// })
```

## IPC Patterns

| Pattern | Method | Use |
|---------|--------|-----|
| Request/Response | ipcRenderer.invoke | Queries, mutations |
| Streaming | ipcRenderer.on (event) | Token streams, progress |
| Subscription | Register + cleanup | Real-time updates |
| Events | ipcRenderer.send (fire-and-forget) | Telemetry, logs |

## Security

- All IPC channels validated in preload
- Input validation on main process side
- No eval(), no dynamic require()
- CSP restricts renderer to local assets only
- Context isolation enabled, nodeIntegration: false