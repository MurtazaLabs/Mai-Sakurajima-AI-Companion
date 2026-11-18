import logging

logger = logging.getLogger(__name__)

# Module-level constant for permission checking
# "run_command" removed for security - arbitrary shell execution is too risky.
# If specific commands are needed, add them as dedicated action types with strict validation.
_EXECUTE_ALLOWED_TYPES = {"open_app", "open_url", "search", "type_text"}


def register_builtin_tools(registry, brain=None, memory=None, knowledge_retriever=None,
                           reasoning_engine=None, belief_engine=None, executor=None,
                           graph_manager=None, graph_reasoning=None,
                           obsidian_writer=None):
    if brain:
        registry.register(
            name="get_brain_state",
            description="Retrieve the current cognitive state, including emotion, topic, and turn count.",
            handler=lambda: _call(brain, "get_state", {}),
            parameters={},
            category="core",
        )

        registry.register(
            name="set_emotion",
            description="Set the AI's emotional state (type and intensity).",
            handler=lambda **kw: _call(brain, "set_emotion", kw),
            parameters={
                "emotion_type": {"type": "string", "description": "Emotion name (e.g. happy, sad, curious)"},
                "intensity": {"type": "number", "description": "Intensity 0.0 to 1.0"},
            },
            category="core",
        )

        registry.register(
            name="set_topic",
            description="Update the current conversation topic.",
            handler=lambda **kw: _call(brain, "set_topic", kw),
            parameters={
                "topic": {"type": "string", "description": "The new conversation topic"},
            },
            category="core",
        )

    if memory:
        registry.register(
            name="store_memory",
            description="Store a memory with text content, type, and optional tags.",
            handler=lambda **kw: _call(memory, "store", kw),
            parameters={
                "text": {"type": "string", "description": "Memory content text"},
                "memory_type": {"type": "string", "description": "Memory category (e.g. conversation, preference)"},
                "tags": {"type": "array", "description": "Optional tags for retrieval"},
            },
            category="memory",
        )

        registry.register(
            name="search_memories",
            description="Search memories by query text or tags.",
            handler=lambda **kw: _call(memory, "search", kw),
            parameters={
                "query": {"type": "string", "description": "Search query"},
                "limit": {"type": "number", "description": "Maximum results"},
            },
            category="memory",
        )

        registry.register(
            name="recall",
            description="Recall recent or important memories by type.",
            handler=lambda **kw: _call(memory, "recall", kw),
            parameters={
                "memory_type": {"type": "string", "description": "Type filter"},
                "limit": {"type": "number", "description": "Maximum results"},
            },
            category="memory",
        )

    if knowledge_retriever:
        registry.register(
            name="retrieve_knowledge",
            description="Search the knowledge base for information on a topic.",
            handler=lambda **kw: _call(knowledge_retriever, "retrieve", kw),
            parameters={
                "query": {"type": "string", "description": "The knowledge query"},
                "top_k": {"type": "number", "description": "Number of results"},
            },
            category="knowledge",
        )

    if belief_engine:
        registry.register(
            name="get_beliefs",
            description="Get current beliefs and their confidence levels.",
            handler=lambda **kw: _call(belief_engine, "get_beliefs_by_topic", kw),
            parameters={
                "topic": {"type": "string", "description": "Optional topic filter"},
            },
            category="knowledge",
        )

        registry.register(
            name="update_belief",
            description="Create or update a belief on a topic with evidence.",
            handler=lambda **kw: _call(belief_engine, "update_belief", kw),
            parameters={
                "topic": {"type": "string", "description": "Belief topic"},
                "content": {"type": "string", "description": "Belief content"},
                "confidence": {"type": "number", "description": "Confidence 0.0 to 1.0"},
            },
            category="knowledge",
        )

    if reasoning_engine:
        registry.register(
            name="reason",
            description="Perform reasoning on a question or problem using available knowledge and memory.",
            handler=lambda **kw: _call(reasoning_engine, "reason", kw),
            parameters={
                "query": {"type": "string", "description": "The question or problem to reason about"},
            },
            category="reasoning",
        )

    if executor:
        import re as _re

        def _safe_execute(**kw):
            action_type = kw.get("type", "")
            content = kw.get("content", "")
            if action_type not in _EXECUTE_ALLOWED_TYPES:
                return {"error": f"action_type '{action_type}' not allowed; must be one of {sorted(_EXECUTE_ALLOWED_TYPES)}"}
            if not isinstance(content, str) or len(content) > 500:
                return {"error": "content must be a string of at most 500 characters"}
            safe_chars = _re.sub(r'[^a-zA-Z0-9\s\-_.:/\\@()?#&=%~+,;!$\'*]', '', content)
            if safe_chars != content:
                return {"error": "content contains disallowed characters; allowed: alphanumeric, spaces, and .:-_/\\@()?#&=%~+,;!$'*"}
            return _call(executor, "run", {"action": kw})

        registry.register(
            name="execute_action",
            description="Execute a system-level action like opening an app, searching the web, or typing text.",
            handler=_safe_execute,
            parameters={
                "type": {"type": "string", "description": "Action type: open_app, open_url, search, type_text"},
                "content": {"type": "string", "description": "Action target content"},
            },
            category="execution",
        )

        registry.register(
            name="get_execution_stats",
            description="Get execution statistics (success rate, counts, queued tasks).",
            handler=lambda: _call(executor, "stats", {}),
            parameters={},
            category="execution",
        )


    if graph_manager:
        registry.register(
            name="graph_query",
            description="Query the knowledge graph for entities related to a topic. Returns structured relationships.",
            handler=lambda **kw: _call(graph_manager, "query", kw),
            parameters={
                "entity": {"type": "string", "description": "The entity name to query"},
                "depth": {"type": "number", "description": "Traversal depth (1 = direct neighbors)"},
            },
            category="knowledge",
        )

        registry.register(
            name="graph_search",
            description="Search for entities in the knowledge graph by name.",
            handler=lambda **kw: _call(graph_manager, "search", kw),
            parameters={
                "query": {"type": "string", "description": "Entity name search query"},
            },
            category="knowledge",
        )

    if graph_reasoning:
        registry.register(
            name="graph_reason",
            description="Answer natural language questions about the knowledge graph. Supports: 'what connects X and Y', 'what is related to X', 'path from X to Y'.",
            handler=lambda **kw: _call(graph_reasoning, "answer", kw),
            parameters={
                "query": {"type": "string", "description": "Natural language question about graph relationships"},
            },
            category="reasoning",
        )


    if obsidian_writer:
        registry.register(
            name="obsidian_sync",
            description="Sync the knowledge graph to Obsidian vault markdown files. Writes entities with frontmatter and [[wiki-links]].",
            handler=lambda: _call(obsidian_writer, "sync", {}),
            parameters={},
            category="knowledge",
        )


def register_file_tools(registry, file_tools=None, partner=None):
    """Sandboxed file tools for the LLM surface.

    Reads and in-workspace writes execute directly. A write outside the
    sandbox is parked in the partner approval tier when available; otherwise it
    is refused with a clear error (never silently redirected).
    """
    if registry is None or file_tools is None:
        return 0

    def _write(path, content, overwrite=True):
        if file_tools.writable(path):
            return file_tools.write(path, content, overwrite=overwrite)
        if partner is not None:
            entry = partner.request_file(
                path, content, reason="file write requested by a tool"
            )
            return {
                "status": "needs_approval",
                "path": path,
                "approval": entry,
                "note": "outside the sandbox — nothing is written until approved",
            }
        return {"error": "write_outside_sandbox", "path": path}

    def _read(path, max_chars=20000):
        return file_tools.read(path, max_chars=max_chars)

    def _list(path="", limit=100):
        return file_tools.list(path, limit=limit)

    def _create(path, content):
        return _write(path, content, overwrite=False)

    registry.register(
        name="read_file",
        description="Read a UTF-8 text file inside Mai's file sandbox.",
        handler=lambda **kw: _read(**kw),
        parameters={
            "path": {"type": "string", "description": "File path (workspace-relative or absolute inside the sandbox)"},
            "max_chars": {"type": "number", "description": "Optional character cap"},
        },
        category="files",
    )
    registry.register(
        name="list_dir",
        description="List a directory inside Mai's file sandbox.",
        handler=lambda **kw: _list(**kw),
        parameters={
            "path": {"type": "string", "description": "Directory path (default: workspace root)"},
            "limit": {"type": "number", "description": "Maximum entries"},
        },
        category="files",
    )
    registry.register(
        name="write_file",
        description="Write a text file. Inside the workspace this is autonomous; "
                    "outside it becomes an approval request.",
        handler=lambda **kw: _write(**kw),
        parameters={
            "path": {"type": "string", "description": "Target path"},
            "content": {"type": "string", "description": "Text to write"},
            "overwrite": {"type": "boolean", "description": "Allow replacing an existing file"},
        },
        category="files",
    )
    registry.register(
        name="create_file",
        description="Create a new text file without clobbering an existing one. "
                    "Outside the workspace it becomes an approval request.",
        handler=lambda **kw: _create(**kw),
        parameters={
            "path": {"type": "string", "description": "Target path"},
            "content": {"type": "string", "description": "Text to write"},
        },
        category="files",
    )
    return 4


def _call(obj, method_name, kwargs):
    if obj is None:
        return {"error": f"system_not_available:{method_name}"}
    method = getattr(obj, method_name, None)
    if method is None:
        return {"error": f"method_not_found:{method_name}"}
    if not isinstance(kwargs, dict):
        logger.warning("_call(%s) expected dict kwargs, got %s", method_name, type(kwargs).__name__)
        return method()
    return method(**kwargs)
