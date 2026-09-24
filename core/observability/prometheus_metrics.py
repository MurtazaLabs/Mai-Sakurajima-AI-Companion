# core/observability/prometheus_metrics.py
"""
Prometheus metrics for Mai AI observability.

Provides counters, histograms, gauges for monitoring system health,
performance, and business metrics.
"""
import time
import threading
from typing import Dict, Optional, Callable
from functools import wraps
from contextlib import contextmanager

from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response

from core.mai_message import new_correlation_id
from core.mai_message import get_correlation_id

# Global registry
REGISTRY = CollectorRegistry()

# ── Metrics Definitions ────────────────────────────────────────────────────

# Request metrics
http_requests_total = Counter(
    "mai_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
    registry=REGISTRY,
)

http_request_duration_seconds = Histogram(
    "mai_http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
    registry=REGISTRY,
)

http_request_size_bytes = Histogram(
    "mai_http_request_size_bytes",
    "HTTP request size in bytes",
    ["method", "endpoint"],
    buckets=[100, 1000, 10000, 100000, 1000000],
    registry=REGISTRY,
)

http_response_size_bytes = Histogram(
    "mai_http_response_size_bytes",
    "HTTP response size in bytes",
    ["method", "endpoint"],
    buckets=[100, 1000, 10000, 100000, 1000000],
    registry=REGISTRY,
)

# LLM metrics
llm_requests_total = Counter(
    "mai_llm_requests_total",
    "Total LLM requests",
    ["provider", "model", "status"],
    registry=REGISTRY,
)

llm_request_duration_seconds = Histogram(
    "mai_llm_request_duration_seconds",
    "LLM request latency in seconds",
    ["provider", "model"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
    registry=REGISTRY,
)

llm_tokens_total = Counter(
    "mai_llm_tokens_total",
    "Total LLM tokens processed",
    ["provider", "model", "type"],  # type: prompt, completion
    registry=REGISTRY,
)

llm_tokens_per_request = Histogram(
    "mai_llm_tokens_per_request",
    "Tokens per LLM request",
    ["provider", "model", "type"],
    buckets=[10, 50, 100, 500, 1000, 5000, 10000, 50000],
    registry=REGISTRY,
)

# Voice metrics
voice_requests_total = Counter(
    "mai_voice_requests_total",
    "Total voice requests",
    ["type", "status"],  # type: stt, tts; status: success, error
    registry=REGISTRY,
)

voice_duration_seconds = Histogram(
    "mai_voice_duration_seconds",
    "Voice processing duration",
    ["type"],  # stt, tts
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
    registry=REGISTRY,
)

# Memory/Vector store metrics
memory_operations_total = Counter(
    "mai_memory_operations_total",
    "Total memory operations",
    ["operation", "status"],  # operation: store, recall, search; status: success, error
    registry=REGISTRY,
)

memory_operation_duration_seconds = Histogram(
    "mai_memory_operation_duration_seconds",
    "Memory operation latency",
    ["operation"],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0],
    registry=REGISTRY,
)

vector_store_size = Gauge(
    "mai_vector_store_size",
    "Number of vectors in store",
    ["index_name"],
    registry=REGISTRY,
)

# Knowledge graph metrics
graph_nodes = Gauge(
    "mai_graph_nodes",
    "Number of nodes in knowledge graph",
    ["entity_type"],
    registry=REGISTRY,
)

graph_edges = Gauge(
    "mai_graph_edges",
    "Number of edges in knowledge graph",
    ["relation_type"],
    registry=REGISTRY,
)

graph_query_duration_seconds = Histogram(
    "mai_graph_query_duration_seconds",
    "Graph query latency",
    ["query_type"],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0],
    registry=REGISTRY,
)

# Agent/Task metrics
agent_tasks_total = Counter(
    "mai_agent_tasks_total",
    "Total agent tasks",
    ["status"],  # pending, running, completed, failed
    registry=REGISTRY,
)

agent_task_duration_seconds = Histogram(
    "mai_agent_task_duration_seconds",
    "Agent task duration",
    ["task_type"],
    buckets=[0.1, 0.5, 1.0, 5.0, 10.0, 60.0, 300.0],
    registry=REGISTRY,
)

# Tool execution metrics
tool_executions_total = Counter(
    "mai_tool_executions_total",
    "Total tool executions",
    ["tool_name", "status"],
    registry=REGISTRY,
)

tool_execution_duration_seconds = Histogram(
    "mai_tool_execution_duration_seconds",
    "Tool execution duration",
    ["tool_name"],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0, 60.0],
    registry=REGISTRY,
)

# Database metrics
db_connections_active = Gauge(
    "mai_db_connections_active",
    "Active database connections",
    ["pool"],
    registry=REGISTRY,
)

db_query_duration_seconds = Histogram(
    "mai_db_query_duration_seconds",
    "Database query duration",
    ["query_type", "table"],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0],
    registry=REGISTRY,
)

db_pool_size = Gauge(
    "mai_db_pool_size",
    "Database connection pool size",
    ["pool", "state"],  # state: active, idle
    registry=REGISTRY,
)

# Cache metrics
cache_hits = Counter(
    "mai_cache_hits_total",
    "Cache hits",
    ["cache_name"],
    registry=REGISTRY,
)

cache_misses = Counter(
    "mai_cache_misses_total",
    "Cache misses",
    ["cache_name"],
    registry=REGISTRY,
)

cache_size = Gauge(
    "mai_cache_size",
    "Cache size in entries",
    ["cache_name"],
    registry=REGISTRY,
)

# System metrics
process_cpu_seconds = Counter(
    "mai_process_cpu_seconds_total",
    "Total CPU time",
    registry=REGISTRY,
)

process_memory_bytes = Gauge(
    "mai_process_memory_bytes",
    "Process memory usage",
    ["type"],  # rss, vms
    registry=REGISTRY,
)

# ── Helper Functions ─────────────────────────────────────────────────────

def record_http_request(method: str, endpoint: str, status: int, duration: float, request_size: int = 0, response_size: int = 0):
    """Record HTTP request metrics."""
    http_requests_total.labels(method=method, endpoint=endpoint, status=str(status)).inc()
    http_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(duration)
    if request_size > 0:
        http_request_size_bytes.labels(method=method, endpoint=endpoint).observe(request_size)
    if response_size > 0:
        http_response_size_bytes.labels(method=method, endpoint=endpoint).observe(response_size)


def record_llm_request(provider: str, model: str, status: str, duration: float, prompt_tokens: int = 0, completion_tokens: int = 0):
    """Record LLM request metrics."""
    llm_requests_total.labels(provider=provider, model=model, status=status).inc()
    llm_request_duration_seconds.labels(provider=provider, model=model).observe(duration)
    if prompt_tokens > 0:
        llm_tokens_total.labels(provider=provider, model=model, type="prompt").inc(prompt_tokens)
    if completion_tokens > 0:
        llm_tokens_total.labels(provider=provider, model=model, type="completion").inc(completion_tokens)
    if prompt_tokens > 0 or completion_tokens > 0:
        total_tokens = prompt_tokens + completion_tokens
        llm_tokens_per_request.labels(provider=provider, model=model, type="total").observe(total_tokens)


def record_voice_request(voice_type: str, status: str, duration: float):
    """Record voice processing metrics."""
    voice_requests_total.labels(type=voice_type, status=status).inc()
    voice_duration_seconds.labels(type=voice_type).observe(duration)


def record_memory_operation(operation: str, status: str, duration: float):
    """Record memory operation metrics."""
    memory_operations_total.labels(operation=operation, status=status).inc()
    memory_operation_duration_seconds.labels(operation=operation).observe(duration)


def update_vector_store_size(index_name: str, size: int):
    """Update vector store size gauge."""
    vector_store_size.labels(index_name=index_name).set(size)


def update_graph_metrics(nodes_by_type: dict, edges_by_type: dict):
    """Update graph metrics."""
    for etype, count in nodes_by_type.items():
        graph_nodes.labels(entity_type=etype).set(count)
    for rtype, count in edges_by_type.items():
        graph_edges.labels(relation_type=rtype).set(count)


def record_graph_query(query_type: str, duration: float):
    """Record graph query latency."""
    graph_query_duration_seconds.labels(query_type=query_type).observe(duration)


def record_agent_task(task_type: str, status: str, duration: float):
    """Record agent task metrics."""
    agent_tasks_total.labels(status=status).inc()
    agent_task_duration_seconds.labels(task_type=task_type).observe(duration)


def record_tool_execution(tool_name: str, status: str, duration: float):
    """Record tool execution metrics."""
    tool_executions_total.labels(tool_name=tool_name, status=status).inc()
    tool_execution_duration_seconds.labels(tool_name=tool_name).observe(duration)


def update_db_pool_metrics(pool_name: str, active: int, idle: int):
    """Update database pool metrics."""
    db_pool_size.labels(pool=pool_name, state="active").set(active)
    db_pool_size.labels(pool=pool_name, state="idle").set(idle)


def record_db_query(query_type: str, table: str, duration: float):
    """Record database query duration."""
    db_query_duration_seconds.labels(query_type=query_type, table=table).observe(duration)


def record_cache_hit(cache_name: str):
    """Record cache hit."""
    cache_hits.labels(cache_name=cache_name).inc()


def record_cache_miss(cache_name: str):
    """Record cache miss."""
    cache_misses.labels(cache_name=cache_name).inc()


def set_cache_size(cache_name: str, size: int):
    """Set cache size gauge."""
    cache_size.labels(cache_name=cache_name).set(size)


def update_system_metrics():
    """Update system-level metrics (CPU, memory)."""
    import psutil
    process = psutil.Process()
    
    # CPU
    cpu_times = process.cpu_times()
    process_cpu_seconds.inc(cpu_times.user + cpu_times.system)
    
    # Memory
    mem_info = process.memory_info()
    process_memory_bytes.labels(type="rss").set(mem_info.rss)
    process_memory_bytes.labels(type="vms").set(mem_info.vms)


# ── FastAPI Middleware ───────────────────────────────────────────────────

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class PrometheusMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for automatic HTTP metrics collection."""
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Read request body size
        request_size = 0
        if hasattr(request, "body"):
            try:
                body = await request.body()
                request_size = len(body)
            except Exception:
                request_size = 0
        
        # Process request
        response = await call_next(request)
        
        # Calculate metrics
        duration = time.time() - start_time
        response_size = 0
        if hasattr(response, "body"):
            response_size = len(response.body) if hasattr(response.body, "__len__") else 0
        
        # Record metrics
        record_http_request(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code,
            duration=duration,
            request_size=request_size,
            response_size=response_size,
        )
        
        return response


def get_metrics() -> Response:
    """Prometheus metrics endpoint."""
    return Response(
        content=generate_latest(REGISTRY),
        media_type=CONTENT_TYPE_LATEST,
    )


def get_metrics_text() -> str:
    """Get metrics as text (for scraping)."""
    return generate_latest(REGISTRY).decode()


# Import at bottom to avoid circular imports
import time
from fastapi import Response
from starlette.middleware.base import BaseHTTPMiddleware
from prometheus_client import CONTENT_TYPE_LATEST