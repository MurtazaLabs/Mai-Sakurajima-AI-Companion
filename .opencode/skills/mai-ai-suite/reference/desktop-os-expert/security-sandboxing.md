# Security / Sandboxing

## Electron Security

| Setting | Value |
|---------|-------|
| nodeIntegration | false |
| contextIsolation | true |
| sandbox | true (renderer) |
| webSecurity | true |
| allowRunningInsecureContent | false |
| enableRemoteModule | false |

## Context Bridge

Only expose specific, typed APIs. Never expose ipcRenderer directly.

```typescript
// GOOD
contextBridge.exposeInMainWorld('electronAPI', {
  chat: { send, onToken, onError }
});

// BAD
contextBridge.exposeInMainWorld('electronAPI', {
  ipcRenderer: ipcRenderer // NEVER
});
```

## CSP

```
default-src 'self';
script-src 'self';
style-src 'self' 'unsafe-inline';
img-src 'self' data: blob:;
connect-src 'self' ws:;  # local WebSocket for Python streaming
font-src 'self';
media-src 'self';
```

## Plugin Isolation

- Plugins run in separate iframes with their own context
- No access to electronAPI unless explicitly granted
- Limited to plugin-specific API subset
- Resource limits (CPU, memory) per plugin
- Plugin manifest declares required permissions

## File Access

- Renderer never accesses file system directly
- All file operations go through IPC → main process
- Main process validates paths against allowed directories
- Drag & drop validates mime types and file extensions