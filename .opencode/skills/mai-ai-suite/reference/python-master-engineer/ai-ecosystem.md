# AI & Agent Development Reference

Deep knowledge for reviewing and building AI-powered Python applications at production scale.

---

## LLM API Clients

### OpenAI / Compatible APIs
```python
from openai import AsyncOpenAI

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

async def chat(messages: list[dict], model: str = "gpt-4o") -> str:
    response = await client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.7,
        max_tokens=1000,
    )
    return response.choices[0].message.content
```

### Anthropic (Claude)
```python
import anthropic

client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

async def ask_claude(prompt: str, system: str = "") -> str:
    message = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        system=system,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text
```

### Ollama (local)
```python
import ollama

def ask_ollama(prompt: str, model: str = "qwen2.5:3b") -> str:
    response = ollama.chat(
        model=model,
        messages=[{"role": "user", "content": prompt}]
    )
    return response["message"]["content"]

# Async version
async def ask_ollama_async(prompt: str, model: str = "qwen2.5:3b") -> str:
    client = ollama.AsyncClient()
    response = await client.chat(
        model=model,
        messages=[{"role": "user", "content": prompt}]
    )
    return response["message"]["content"]
```

### OpenRouter (multi-provider routing)
```python
from openai import AsyncOpenAI

client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

async def ask_openrouter(prompt: str, model: str = "meta-llama/llama-3.1-8b-instruct:free") -> str:
    response = await client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content
```

---

## LangChain

### Common Review Issues
- **Chain bloat**: overly complex chains for simple tasks — evaluate if vanilla API calls would be cleaner
- **Memory leaks**: `ConversationBufferMemory` grows unbounded — use `ConversationBufferWindowMemory`
- **Callback hell**: nested callbacks make debugging painful — add `verbose=True` during dev
- **Deprecated patterns**: LangChain changes APIs frequently — check for `langchain_core` vs `langchain` imports

### Clean Patterns
```python
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

# LCEL chain (current preferred pattern)
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful assistant."),
    ("human", "{input}")
])

chain = prompt | ChatOpenAI(model="gpt-4o") | StrOutputParser()
result = await chain.ainvoke({"input": "hello"})
```

---

## LangGraph

### Core Concepts
- **StateGraph**: defines nodes (functions) and edges (transitions)
- **State**: typed dict shared across all nodes
- **Conditional edges**: route to different nodes based on state

### Common Review Issues
- State type not properly typed → runtime errors, hard to debug
- No error handling in nodes → one failure crashes entire graph
- Infinite loops in conditional routing → always have a terminal condition

```python
from langgraph.graph import StateGraph, END
from typing import TypedDict

class AgentState(TypedDict):
    messages: list[dict]
    step: int
    done: bool

def think(state: AgentState) -> AgentState:
    # process and return updated state
    return {**state, "step": state["step"] + 1}

def should_continue(state: AgentState) -> str:
    return END if state["done"] or state["step"] > 10 else "think"

graph = StateGraph(AgentState)
graph.add_node("think", think)
graph.add_conditional_edges("think", should_continue)
graph.set_entry_point("think")
app = graph.compile()
```

---

## CrewAI

### Common Review Issues
- Agents with overly broad roles → poor specialization, inconsistent output
- Missing `expected_output` in tasks → LLM doesn't know when it's done
- No `max_iter` limit → can loop forever on complex tasks
- Tools not properly error-handled → one tool failure crashes the crew

```python
from crewai import Agent, Task, Crew

researcher = Agent(
    role="Research Specialist",
    goal="Find accurate, current information on the given topic",
    backstory="Expert at finding and synthesizing information",
    max_iter=5,
    verbose=True
)

task = Task(
    description="Research {topic} and summarize key findings",
    expected_output="A structured 3-paragraph summary with sources",
    agent=researcher
)

crew = Crew(agents=[researcher], tasks=[task], verbose=True)
result = crew.kickoff(inputs={"topic": "Python async patterns"})
```

---

## RAG Systems

### Architecture
```
Documents → Chunking → Embedding → Vector Store
Query → Embedding → Similarity Search → Retrieved Chunks → LLM + Context → Response
```

### Common Review Issues
- **Chunk size mismatch**: too small = lost context; too large = diluted relevance
- **No metadata filtering**: searching entire DB instead of scoped collections
- **Embedding model mismatch**: using different model at index vs query time
- **No reranking**: top-k by cosine similarity isn't always the best k docs
- **Context window overflow**: stuffing too many retrieved chunks into the prompt

### ChromaDB Pattern (used in Mai_ai)
```python
import chromadb
from chromadb.utils import embedding_functions

class VectorMemory:
    def __init__(self, path: str = "./memory/chroma"):
        self.client = chromadb.PersistentClient(path=path)
        self.ef = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        self.collection = self.client.get_or_create_collection(
            name="memories",
            embedding_function=self.ef
        )

    def save(self, doc_id: str, text: str, metadata: dict = None):
        self.collection.upsert(
            documents=[text],
            ids=[doc_id],
            metadatas=[metadata or {}]
        )

    def search(self, query: str, n: int = 5) -> list[dict]:
        results = self.collection.query(query_texts=[query], n_results=n)
        return [
            {"text": doc, "metadata": meta, "distance": dist}
            for doc, meta, dist in zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0]
            )
        ]
```

---

## MCP (Model Context Protocol)

### Core Concepts
- MCP is a standard for connecting AI models to external tools/data sources
- Server exposes tools → client (LLM host) calls them
- Tools have typed inputs/outputs with JSON Schema

### Common Review Issues
- No input validation on tool parameters → crashes on bad LLM output
- Synchronous tools blocking async MCP server
- Missing error responses (should return structured error, not raise)

```python
from mcp.server import Server
from mcp.types import Tool, TextContent
import mcp.server.stdio

server = Server("my-tool-server")

@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="search_memory",
            description="Search conversation memory",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "limit": {"type": "integer", "default": 5}
                },
                "required": ["query"]
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "search_memory":
        try:
            results = await memory.search(arguments["query"], arguments.get("limit", 5))
            return [TextContent(type="text", text=str(results))]
        except Exception as e:
            return [TextContent(type="text", text=f"Error: {e}")]
```

---

## AI Application Review Checklist

### Reliability
- [ ] Retry logic with exponential backoff for API calls
- [ ] Fallback provider when primary is unavailable
- [ ] Timeout on all LLM calls (LLMs can hang)
- [ ] Token limit checks before sending (avoid 400 errors)

### Cost Control
- [ ] Token counting before expensive calls
- [ ] Caching repeated identical queries
- [ ] Model tier selection (don't use GPT-4o for simple tasks)
- [ ] Streaming for long outputs (better UX, same cost)

### Prompt Engineering
- [ ] System prompts are version-controlled, not hardcoded mid-function
- [ ] No sensitive data injected into prompts unfiltered
- [ ] Prompt injection risks considered for user-provided input

### Production Readiness
- [ ] API keys in environment variables, never in code
- [ ] Request IDs logged for tracing
- [ ] Rate limiting handled (429 responses)
- [ ] Response validation (LLM output isn't always well-formed)
- [ ] Latency monitored (LLM calls can be 2–30 seconds)

---

## Robust LLM Call Wrapper

```python
import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)

async def safe_llm_call(
    client,
    messages: list[dict],
    model: str,
    max_retries: int = 3,
    timeout: float = 30.0,
) -> Optional[str]:
    for attempt in range(max_retries):
        try:
            response = await asyncio.wait_for(
                client.chat.completions.create(model=model, messages=messages),
                timeout=timeout
            )
            return response.choices[0].message.content

        except asyncio.TimeoutError:
            logger.warning(f"LLM call timed out (attempt {attempt + 1}/{max_retries})")
        except Exception as e:
            wait = 2 ** attempt
            logger.warning(f"LLM error: {e}. Retrying in {wait}s...")
            if attempt < max_retries - 1:
                await asyncio.sleep(wait)

    logger.error("All LLM retries exhausted")
    return None
```