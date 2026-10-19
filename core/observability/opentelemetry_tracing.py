"""
OpenTelemetry tracing configuration for Mai AI.
Provides distributed tracing for all services and components.
"""
import importlib
import logging
import os
from contextvars import ContextVar

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.trace.sampling import TraceIdRatioBased


def _optional_import(module: str, attr: str):
    """Import ``module.attr`` or return None when the package is not installed.

    The opentelemetry-instrumentation-* extras (and the Prometheus exporter)
    are optional: their absence must not break module import — init_tracing()
    works with the OTel core (SDK + OTLP exporter) alone.
    """
    try:
        return getattr(importlib.import_module(module), attr)
    except Exception:
        return None


FastAPIInstrumentor = _optional_import("opentelemetry.instrumentation.fastapi", "FastAPIInstrumentor")
HTTPXClientInstrumentor = _optional_import("opentelemetry.instrumentation.httpx", "HTTPXClientInstrumentor")
LoggingInstrumentor = _optional_import("opentelemetry.instrumentation.logging", "LoggingInstrumentor")
RedisInstrumentor = _optional_import("opentelemetry.instrumentation.redis", "RedisInstrumentor")
SQLAlchemyInstrumentor = _optional_import("opentelemetry.instrumentation.sqlalchemy", "SQLAlchemyInstrumentor")
RequestsInstrumentor = _optional_import("opentelemetry.instrumentation.requests", "RequestsInstrumentor")
AioHttpClientInstrumentor = _optional_import("opentelemetry.instrumentation.aiohttp_client", "AioHttpClientInstrumentor")
PrometheusMetricReader = _optional_import("opentelemetry.exporter.prometheus", "PrometheusMetricReader")
set_meter_provider = _optional_import("opentelemetry.metrics", "set_meter_provider")
MeterProvider = _optional_import("opentelemetry.sdk.metrics", "MeterProvider")

logger = logging.getLogger(__name__)

# Context variable for current trace ID
current_trace_id: ContextVar[str | None] = ContextVar('current_trace_id', default=None)

# Global tracer provider
_tracer_provider: TracerProvider | None = None
_tracer: trace.Tracer | None = None


def init_tracing(
    service_name: str = "mai-ai",
    otlp_endpoint: str | None = None,
    sample_rate: float = 0.1,
    enable_console_export: bool = False,
) -> trace.Tracer:
    """Initialize OpenTelemetry tracing.
    
    Args:
        service_name: Name of the service for tracing
        otlp_endpoint: OTLP collector endpoint (e.g., "http://localhost:4317")
        sample_rate: Sampling rate (0.0 to 1.0)
        enable_console_export: Whether to also export to console
    
    Returns:
        Configured tracer instance
    """
    global _tracer_provider, _tracer
    
    # Create resource with service information
    resource = Resource.create({
        SERVICE_NAME: service_name,
        "service.version": os.getenv("MAI_VERSION", "2.0.0"),
        "deployment.environment": os.getenv("DEPLOYMENT_ENV", "development"),
    })
    
    # Create tracer provider with sampling
    _tracer_provider = TracerProvider(
        resource=resource,
        sampler=TraceIdRatioBased(sample_rate),
    )
    
    # Add OTLP exporter if endpoint provided
    if otlp_endpoint:
        try:
            otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
            _tracer_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
            logger.info(f"OTLP tracing enabled: {otlp_endpoint}")
        except Exception as e:
            logger.warning(f"Failed to initialize OTLP exporter: {e}")
    
    # Add console exporter if requested
    if enable_console_export:
        console_exporter = ConsoleSpanExporter()
        _tracer_provider.add_span_processor(BatchSpanProcessor(console_exporter))
        logger.info("Console span exporter enabled")
    
    # Set global tracer provider
    trace.set_tracer_provider(_tracer_provider)
    
    # Get tracer
    _tracer = _tracer_provider.get_tracer(__name__)
    
    # Auto-instrument common libraries
    _auto_instrument()
    
    logger.info(f"OpenTelemetry tracing initialized for {service_name}")
    return _tracer


def _auto_instrument() -> None:
    """Auto-instrument common libraries. Missing optional packages are skipped."""
    for name, instrumentor, kwargs in (
        ("FastAPI", FastAPIInstrumentor, {}),
        ("HTTPX", HTTPXClientInstrumentor, {}),
        ("Requests", RequestsInstrumentor, {}),
        ("aiohttp", AioHttpClientInstrumentor, {}),
        ("SQLAlchemy", SQLAlchemyInstrumentor, {}),
        ("Redis", RedisInstrumentor, {}),
        ("Logging", LoggingInstrumentor, {"set_logging_format": True}),
    ):
        if instrumentor is None:
            logger.debug("[OTel] instrumentation package for %s not installed — skipped", name)
            continue
        try:
            instrumentor().instrument(**kwargs)
            logger.info("%s instrumentation enabled", name)
        except Exception as e:
            logger.warning("%s instrumentation failed: %s", name, e)


def get_tracer() -> trace.Tracer:
    """Get the global tracer instance."""
    global _tracer
    if _tracer is None:
        _tracer = trace.get_tracer(__name__)
    return _tracer


def get_trace_id() -> str | None:
    """Get current trace ID from context."""
    span = trace.get_current_span()
    if span and span.get_span_context().trace_id:
        return format(span.get_span_context().trace_id, '032x')
    return current_trace_id.get()


def set_trace_id(trace_id: str) -> None:
    """Set trace ID in context variable."""
    current_trace_id.set(trace_id)


def trace_function(name: str, attributes: dict = None):
    """Decorator to trace a function."""
    tracer = get_tracer()
    
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            with tracer.start_as_current_span(name, attributes=attributes) as span:
                return await func(*args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            with tracer.start_as_current_span(name, attributes=attributes) as span:
                return func(*args, **kwargs)
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    return decorator


def add_span_attributes(attributes: dict) -> None:
    """Add attributes to current span."""
    span = trace.get_current_span()
    if span:
        for key, value in attributes.items():
            span.set_attribute(key, value)


def add_span_event(name: str, attributes: dict = None) -> None:
    """Add an event to current span."""
    span = trace.get_current_span()
    if span:
        span.add_event(name, attributes=attributes or {})


def record_exception(exception: Exception) -> None:
    """Record exception in current span."""
    span = trace.get_current_span()
    if span:
        span.record_exception(exception)
        span.set_status(trace.Status(trace.StatusCode.ERROR, str(exception)))


# Context manager for manual span creation
class trace_span:
    """Context manager for creating spans manually."""
    
    def __init__(self, name: str, attributes: dict = None):
        self.name = name
        self.attributes = attributes or {}
        self.span = None
    
    def __enter__(self):
        self.span = get_tracer().start_span(self.name, attributes=self.attributes)
        return self.span
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_val:
            self.span.record_exception(exc_val)
            self.span.set_status(trace.Status(trace.StatusCode.ERROR, str(exc_val)))
        self.span.end()


def get_current_span() -> trace.Span:
    """Get the current active span."""
    return trace.get_current_span()


def inject_trace_context(headers: dict) -> dict:
    """Inject trace context into headers for propagation."""
    from opentelemetry.propagate import inject
    inject(headers)
    return headers


def extract_trace_context(headers: dict) -> dict:
    """Extract trace context from headers."""
    from opentelemetry.propagate import extract
    return extract(headers)


# Custom span attributes for Mai AI
class SpanAttributes:
    """Standard span attribute keys for Mai AI."""
    
    # LLM attributes
    LLM_PROVIDER = "llm.provider"
    LLM_MODEL = "llm.model"
    LLM_TOKENS_PROMPT = "llm.tokens.prompt"
    LLM_TOKENS_COMPLETION = "llm.tokens.completion"
    LLM_TEMPERATURE = "llm.temperature"
    
    # Memory attributes
    MEMORY_OPERATION = "memory.operation"
    MEMORY_TYPE = "memory.type"
    MEMORY_IMPORTANCE = "memory.importance"
    
    # Graph attributes
    GRAPH_OPERATION = "graph.operation"
    GRAPH_ENTITY_COUNT = "graph.entity_count"
    GRAPH_RELATION_COUNT = "graph.relation_count"
    
    # Tool attributes
    TOOL_NAME = "tool.name"
    TOOL_DURATION_MS = "tool.duration_ms"
    TOOL_SUCCESS = "tool.success"
    
    # HTTP attributes
    HTTP_METHOD = "http.method"
    HTTP_URL = "http.url"
    HTTP_STATUS = "http.status_code"
    
    # Database attributes
    DB_OPERATION = "db.operation"
    DB_TABLE = "db.table"
    DB_DURATION_MS = "db.duration_ms"
    
    # Cache attributes
    CACHE_OPERATION = "cache.operation"
    CACHE_HIT = "cache.hit"
    CACHE_KEY = "cache.key"
    
    # Agent attributes
    AGENT_TASK = "agent.task"
    AGENT_STEP = "agent.step"
    AGENT_TOOL = "agent.tool"


def record_llm_request(
    provider: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    duration_ms: float,
    success: bool = True,
    error: str = None
):
    """Record LLM request metrics and tracing."""
    from opentelemetry import trace

    from core.observability.prometheus_metrics import record_llm_request
    
    span = trace.get_current_span()
    if span:
        span.set_attribute("llm.provider", provider)
        span.set_attribute("llm.model", model)
        span.set_attribute("llm.tokens.prompt", prompt_tokens)
        span.set_attribute("llm.tokens.completion", completion_tokens)
        span.set_attribute("llm.duration_ms", duration_ms)
        span.set_attribute("llm.success", success)
        if error:
            span.set_attribute("llm.error", error)
            span.set_status(trace.Status(trace.StatusCode.ERROR, error))
    
    # Record metrics
    record_llm_request(
        provider=provider,
        model=model,
        status="success" if success else "error",
        duration=duration_ms / 1000.0,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens
    )


def record_tool_execution(tool_name: str, duration_ms: float, success: bool = True, error: str = None):
    """Record tool execution metrics and tracing."""
    from opentelemetry import trace

    from core.observability.prometheus_metrics import record_tool_execution
    
    span = trace.get_current_span()
    if span:
        span.set_attribute("tool.name", tool_name)
        span.set_attribute("tool.duration_ms", duration_ms)
        span.set_attribute("tool.success", success)
        if error:
            span.set_attribute("tool.error", error)
            span.set_status(trace.Status(trace.StatusCode.ERROR, error))
    
    record_tool_execution(tool_name, duration_ms / 1000.0, success=success, error=error)


def record_memory_operation(operation: str, duration_ms: float, success: bool = True):
    """Record memory operation metrics and tracing."""
    from opentelemetry import trace

    from core.observability.prometheus_metrics import record_memory_operation
    
    span = trace.get_current_span()
    if span:
        span.set_attribute("memory.operation", operation)
        span.set_attribute("memory.duration_ms", duration_ms)
        span.set_attribute("memory.success", success)
    
    record_memory_operation(operation, "success" if success else "error", duration_ms / 1000.0)


def record_tool_execution(tool_name: str, duration_ms: float, success: bool = True, error: str = None):
    """Record tool execution metrics and tracing."""
    from opentelemetry import trace

    from core.observability.prometheus_metrics import record_tool_execution
    
    span = trace.get_current_span()
    if span:
        span.set_attribute("tool.name", tool_name)
        span.set_attribute("tool.duration_ms", duration_ms)
        span.set_attribute("tool.success", success)
        if error:
            span.set_attribute("tool.error", error)
            span.set_status(trace.Status(trace.StatusCode.ERROR, error))
    
    record_tool_execution(tool_name, duration_ms / 1000.0, success=success, error=error)


def record_memory_operation(operation: str, duration_ms: float, success: bool = True):
    """Record memory operation metrics and tracing."""
    from opentelemetry import trace

    from core.observability.prometheus_metrics import record_memory_operation
    
    span = trace.get_current_span()
    if span:
        span.set_attribute("memory.operation", operation)
        span.set_attribute("memory.duration_ms", duration_ms)
        span.set_attribute("memory.success", success)
    
    record_memory_operation(operation, "success" if success else "error", duration_ms / 1000.0)


def init_observability(
    service_name: str = "mai-ai",
    otlp_endpoint: str = None,
    prometheus_port: int = 9090,
    enable_console: bool = False
):
    """Initialize full observability stack."""
    
    # Initialize tracing
    init_tracing(
        service_name=service_name,
        otlp_endpoint=otlp_endpoint,
        enable_console_export=enable_console,
    )
    
    # Initialize Prometheus metrics
    import threading
    
    def update_metrics_loop():
        import time
        while True:
            try:
                from core.observability.prometheus_metrics import update_system_metrics
                update_system_metrics()
            except Exception as e:
                logger.warning(f"Failed to update system metrics: {e}")
            time.sleep(10)
    
    metrics_thread = threading.Thread(target=update_metrics_loop, daemon=True)
    metrics_thread.start()
    
    logger.info("Observability stack initialized")


# FastAPI integration
def setup_tracing_middleware(app):
    """Setup FastAPI middleware for tracing."""
    if FastAPIInstrumentor is None:
        logger.warning(
            "opentelemetry-instrumentation-fastapi not installed — "
            "FastAPI app tracing skipped"
        )
    else:
        FastAPIInstrumentor.instrument_app(app)
    
    @app.middleware("http")
    async def add_trace_id_header(request, call_next):
        from opentelemetry import trace
        span = trace.get_current_span()
        trace_id = format(span.get_span_context().trace_id, '032x') if span.get_span_context().trace_id else "none"
        
        response = await call_next(request)
        response.headers["X-Trace-ID"] = trace_id
        return response


# Export key functions and classes
__all__ = [
    "SpanAttributes",
    "TraceAttributes",
    "add_span_attributes",
    "add_span_event",
    "extract_trace_context",
    "get_current_span",
    "get_trace_id",
    "get_tracer",
    "init_observability",
    "init_tracing",
    "inject_trace_context",
    "record_exception",
    "record_llm_request",
    "record_memory_operation",
    "record_tool_execution",
    "set_trace_id",
    "setup_tracing_middleware",
    "trace_function",
    "trace_span",
]