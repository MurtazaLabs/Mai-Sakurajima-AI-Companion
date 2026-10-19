"""
Observability package for Mai AI.
Provides metrics, tracing, and logging capabilities.
"""
from .opentelemetry_tracing import (
    SpanAttributes,
    add_span_attributes,
    add_span_event,
    extract_trace_context,
    get_current_span,
    get_trace_id,
    get_tracer,
    init_observability,
    init_tracing,
    inject_trace_context,
    record_exception,
    # NOTE: record_llm_request / record_memory_operation / record_tool_execution
    # intentionally come from prometheus_metrics below (same names shadowed;
    # __all__ lists the Prometheus implementations as the public surface).
    set_trace_id,
    setup_tracing_middleware,
    trace_function,
    trace_span,
)
from .prometheus_metrics import (
    REGISTRY,
    PrometheusMiddleware,
    get_metrics,
    get_metrics_text,
    record_agent_task,
    record_cache_hit,
    record_cache_miss,
    record_db_query,
    record_http_request,
    record_llm_request,
    record_memory_operation,
    record_tool_execution,
    record_voice_request,
    set_cache_size,
    update_db_pool_metrics,
    update_graph_metrics,
    update_system_metrics,
    update_vector_store_size,
)

__all__ = [
    # Prometheus metrics
    "REGISTRY",
    "get_metrics",
    "get_metrics_text",
    "record_http_request",
    "record_llm_request",
    "record_voice_request",
    "record_memory_operation",
    "update_vector_store_size",
    "update_graph_metrics",
    "record_agent_task",
    "record_tool_execution",
    "update_db_pool_metrics",
    "record_db_query",
    "record_cache_hit",
    "record_cache_miss",
    "set_cache_size",
    "update_system_metrics",
    "PrometheusMiddleware",
    
    # OpenTelemetry tracing
    "init_tracing",
    "get_tracer",
    "get_trace_id",
    "set_trace_id",
    "trace_function",
    "add_span_attributes",
    "add_span_event",
    "record_exception",
    "trace_span",
    "get_current_span",
    "inject_trace_context",
    "extract_trace_context",
    "SpanAttributes",
    "init_observability",
    "setup_tracing_middleware",
]