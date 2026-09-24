# Tool System Reference

> Complete reference for the tool calling and execution system — `agency/tools.py`, `agency/registry.py`, `agency/agent.py`, `execution/safe_executor.py`, `execution/handlers.py`, `execution/task_executor.py`.

---

## Overview

The tool system enables Mai to **take actions** in the world: search, calculate, open URLs, run commands, control desktop, manage clipboard/files, and more.

**Architecture:** [[01-Architecture/06-Agency Reasoning LLM & Execution]]

---

## Components

### ToolRegistry (`agency/registry.py`)

- Central registry of all available tools
- `dispatch(tool_name, params)` — RLock-guarded execution
- Tool metadata: name, description, parameters (JSON Schema), category
- Dynamic registration/unregistration supported

### Built-in Tools (`agency/tools.py`)

12+ tools across categories:

| Category | Tools |
|----------|-------|
| **Search** | `search_web`, `search_memory`, `search_knowledge` |
| **Compute** | `calculate`, `execute_code` |
| **Web** | `open_url`, `fetch_page` |
| **System** | `run_command`, `get_system_info` |
| **Desktop** | `open_app`, `type_text`, `click`, `screenshot` |
| **Clipboard** | `read_clipboard`, `write_clipboard` |
| **Filesystem** | `list_files`, `read_file`, `write_file`, `watch_directory` |
| **Internal** | `execute_action`, `get_execution_stats` (not advertised to LLM) |

Each tool: `Tool(name, description, parameters, handler_fn, category)`

### Agent (`agency/agent.py`)

Multi-step tool-use loop:

```python
async def run(task: str) -> AgentResult:
    while not complete:
        plan = _plan_next(context)           # LLM decides next tool
        result = await registry.dispatch(...) # execute
        context.add(plan, result)             # accumulate evidence
        if all steps failed:
            return AgentResult(success=False, ...)  # honest failure
    return AgentResult(success=True, ...)
```

**Key behaviors:**
- Analysis tasks (`reason`, `think`, `analyze`, `why`, `how`, `what`) get **one synthesis pass** via `reason` tool before `complete`
- **Honest failure** — run ends `success=False` when every step failed (no false success)
- `registry.call` wrapped in try/except; step tracking for observability

### SafeExecutor (`execution/safe_executor.py`)

Validates and sanitizes tool executions:

- `_validate(action)` — reads `action.get("content")` (fallback to legacy `url`/`command` keys)
- Character whitelist in `_safe_execute()` (blocks shell metacharacters; URL chars supported)
- Normalizes agent-style envelopes: `{"action": "call_tool", "tool": ..., "params": {...}}` → `{"type": ..., "content": ...}`

### Execution Handlers (`execution/handlers.py`)

Sandboxed primitives (all thread-safe):

| Handler | Methods | Security |
|---------|---------|----------|
| `SystemActions` | `open_app()`, `run_command()` | App whitelist (20+ apps); `_resolve_app_path()` fallback |
| `CommandActions` | `run_command()` | shell=False; timeout; output capture |
| `DesktopActions` | `type_text()`, `click()`, `screenshot()` | Keystroke filter blocks Alt+F4, Ctrl+W, etc. |
| `ClipboardActions` | `read()`, `write()` | pyperclip |
| `FileSystemActions` | `list()`, `read()`, `write()`, `watch()` | Sandbox: `[ROOT_DIR, OBSIDIAN_VAULT]` **active everywhere** |

**Security posture:**
- App whitelist in `SystemActions.open_app()` — only known apps
- Keystroke filter blocks destructive hotkeys
- FS + clipboard sandbox active for all entry points (not daemon-only)
- `SafeExecutor` validates every action before execution

### TaskExecutor (`execution/task_executor.py`)

- Runs long-running tasks in background
- Progress tracking, cancellation support
- Integrates with `Scheduler` for periodic tasks

---

## Tool Calling Flow (LLM → Action)

```
1. LLM generates tool call (JSON)
   └─ Prompt instructs: explicit example {"type": "open_app", "content": "chrome"}
      Allowed types: open_app, open_url, search, type_text, run_command, speak
      "Never say you cannot"

2. ResponsePipeline.process() receives LLM output
   └─ _normalize_action() flattens agent-style envelopes
   └─ _validate() checks against whitelist

3. ToolRegistry.dispatch() executes
   └─ Handler runs in thread pool
   └─ Result captured, formatted

4. Agent loop continues or completes
```

---

## Agent Prompt Contract (`prompt/agent.py`)

- **Explicit JSON example** in `_base_instructions`
- Lists allowed types with descriptions
- "Never say you cannot" — encourages tool use
- Internal tools (`execute_action`, `get_execution_stats`) hidden from LLM

---

## Events

| Topic | Publisher |
|-------|-----------|
| `data.agent.tool_called` | Agent |
| `data.agent.step_completed` | Agent |
| `state.agent.completed` | Agent (final) |

---

## Known Issues

- `generate_with_tools()` dead passthrough in LLMManager
- Providers duck-typed (no ABC)
- `_result()` duplicated across 3 handler classes

---

## Wiki Links

**Architecture:** [[01-Architecture/06-Agency Reasoning LLM & Execution]] • [[01-Architecture/09-Events & Data Flow]] — agent events  
**Related:** [[02-Subsystems/Voice Pipeline]] — voice tool path • [[03-Features/Native OS Bridge Architecture]] — clipboard/FS bridges • [[03-Features/Discord Integration Plan]] — Discord bot uses tools