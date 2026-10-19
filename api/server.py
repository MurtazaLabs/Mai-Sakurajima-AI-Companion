import os
import sys
import time
import asyncio
import logging
import threading
import json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.getLogger("api.server").setLevel(logging.INFO)
logger = logging.getLogger("api.server")

from typing import Optional, Any

from fastapi import FastAPI, HTTPException, Request, Depends, Response, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from pydantic import BaseModel, field_validator
import uvicorn

from app.config_loader import (
    API_HOST, API_PORT, API_AUTH_TOKEN, API_REQUIRE_AUTH,
    API_RATE_LIMIT_PER_MINUTE, API_SSL_CERTFILE, API_SSL_KEYFILE,
    API_JWT_SECRET, API_JWT_ACCESS_EXPIRE_MINUTES, API_JWT_REFRESH_EXPIRE_DAYS,
    API_RATE_LIMIT_CHAT, API_RATE_LIMIT_AUTH, API_RATE_LIMIT_HEALTH,
    API_RATE_LIMIT_INGEST, API_RATE_LIMIT_GENERAL,
    API_CORS_ORIGINS, API_TRUSTED_HOSTS,
)

from api.certs import ensure_dev_certs
from api.routes_chat import ChatMixin
from api.routes_memory import MemoryMixin
from api.routes_knowledge import KnowledgeMixin
from api.routes_agency import AgencyMixin
from api.routes_reasoning import ReasoningMixin
from api.routes_voice import VoiceMixin
from api.routes_system import SystemMixin
from api.routes_dashboard import DashboardMixin
from api.routes_inspector import InspectorMixin
from api.routes_tasks import TasksMixin
from api.routes_permissions import PermissionsMixin
from api.routes_inspector import InspectorMixin
from api.routes_tasks import TasksMixin
from api.routes_permissions import PermissionsMixin
from api.routes_plugins import router as plugins_router
from api import auth as jwt_auth
from api import routes_auth
from api import routes_profile
from api.static_serving import make_html_response, static_dir
from api.stream_manager import StreamManager
from core.config_manager import ConfigManager
from api.ws_bridge import WSBridge
from api.middleware.rate_limiter import RateLimiter


class MaiAPI(
    ChatMixin,
    MemoryMixin,
    KnowledgeMixin,
    AgencyMixin,
    ReasoningMixin,
    VoiceMixin,
    SystemMixin,
    DashboardMixin,
    TasksMixin,
    PermissionsMixin,
    InspectorMixin,
):
    """FastAPI-facing façade for the Mai system.

    Domain logic lives in the ``routes_*`` mixins (one per subsystem) so this
    class stays a thin composition root. Public method names are unchanged.
    """

    def __init__(self, host="0.0.0.0", port=8000):
        self.host = host
        self.port = port
        self.brain: Any = None
        self.voice: Any = None
        self.voice_manager: Any = None
        self.event_bus: Any = None
        self.knowledge_builder: Any = None
        self.goal_manager: Any = None
        self.world_model: Any = None
        self.tool_registry: Any = None
        self.thought_journal: Any = None
        self.reasoning_engine: Any = None
        self.reflection_engine: Any = None
        self.wake: Any = None
        self.plugin_loader: Any = None
        self.hook_registry: Any = None
        self.health_registry: Any = None
        self.memory_hierarchy: Any = None
        self.vector_store: Any = None
        self.brain_graph: Any = None
        self.knowledge_graph: Any = None
        self.stream_manager: StreamManager = StreamManager()
        self.config_manager: ConfigManager = ConfigManager()
        self.belief_engine: Any = None
        self.procedural_memory: Any = None
        self.safe_executor: Any = None
        self.profile_store: Any = None
        self.notifier: Any = None
        self.ws_bridge: WSBridge = WSBridge()
        self.inspector: Any = None
        self._lock = threading.RLock()
        self._ready = False
        self._start_time = time.time()
        self._voice_worker: Optional[threading.Thread] = None
        self._voice_worker_stop = threading.Event()
        self.model_lifecycle: Any = None
        self.app: Any = None
        self.kernel: Any = None

    def cleanup(self):
        self._stop_voice_conversation()
        if self.notifier is not None:
            try:
                self.notifier.shutdown()
            except Exception as e:
                logger.exception("[API] Notifier shutdown: %s", e)
        if self.brain is not None:
            try:
                self.brain.shutdown(timeout=3.0)
            except Exception as e:
                logger.exception("[API] Brain shutdown: %s", e)
        logger.info("[API] Components shut down")

    def bootstrap(self):
        from core.profile_store import ProfileStore
        self.profile_store = ProfileStore()
        routes_auth.set_profile_store(self.profile_store)
        routes_profile.set_profile_store(self.profile_store)

        jwt_auth.configure(
            jwt_secret=API_JWT_SECRET,
            access_expire_minutes=API_JWT_ACCESS_EXPIRE_MINUTES,
            refresh_expire_days=API_JWT_REFRESH_EXPIRE_DAYS,
        )
        _rate_limiter.configure(
            chat=API_RATE_LIMIT_CHAT,
            auth=API_RATE_LIMIT_AUTH,
            health=API_RATE_LIMIT_HEALTH,
            ingest=API_RATE_LIMIT_INGEST,
            general=API_RATE_LIMIT_GENERAL,
        )
        from run import bootstrap_system
        try:
            components = bootstrap_system()
            self.brain = components.get("brain")
            self.voice = components.get("voice")
            self.voice_manager = components.get("voice_manager")
            self.wake = components.get("wake")
            self.event_bus = components.get("event_bus")
            self.goal_manager = components.get("goal_manager")
            self.world_model = components.get("world_model")
            self.knowledge_builder = components.get("knowledge_builder")
            self.tool_registry = components.get("tool_registry")
            self.thought_journal = components.get("thought_journal")
            self.reasoning_engine = components.get("reasoning_engine")
            self.reflection_engine = components.get("reflection_engine")
            self.plugin_loader = components.get("plugin_loader")
            self.hook_registry = components.get("hook_registry")
            self.health_registry = components.get("health_registry")
            self.memory_hierarchy = components.get("memory_hierarchy")
            self.vector_store = components.get("vector_store")
            self.brain_graph = components.get("brain_graph")
            self.knowledge_graph = components.get("knowledge_graph")
            self.belief_engine = components.get("belief_engine")
            self.procedural_memory = components.get("procedural_memory")
            self.safe_executor = components.get("safe_executor")
            self.inspector = components.get("event_inspector")
            self.orchestrator = components.get("orchestrator")
            self.directory_watcher = components.get("directory_watcher")
            self.dream_engine = components.get("dream_engine")
            self.session_manager = components.get("session_manager")
            self.model_lifecycle = components.get("model_lifecycle")
            self.app = components.get("app")
            self.kernel = getattr(self.app, "kernel", None)
            if self.session_manager:
                routes_profile.set_session_manager(self.session_manager)
            self._last_dream_report: dict = {}
            if self.event_bus and hasattr(self.event_bus, "on"):
                try:
                    self.event_bus.on("data.dream.completed", self._on_dream_completed)
                except Exception as e:
                    logger.exception("[API] dream event: %s", e)
                try:
                    self.stream_manager.wire(self.event_bus)
                except Exception as e:
                    logger.exception("[API] stream wire: %s", e)
                try:
                    self.ws_bridge.brain = self.brain
                    self.ws_bridge.voice_manager = self.voice_manager
                    self.ws_bridge.wire(self.event_bus)
                except Exception as e:
                    logger.exception("[API] WS bridge wire: %s", e)
                try:
                    from native.notifier import Notifier
                    self.notifier = Notifier(event_bus=self.event_bus, app_name="Mai AI")
                    self.notifier.wire(self.event_bus)
                    logger.info("[API] Notifier wired (%d topics)", len(self.notifier._subs))
                except Exception as e:
                    logger.exception("[API] Notifier wire: %s", e)
            self._ready = True
            logger.info("[API] System bootstrapped")
            return True
        except Exception as e:
            logger.error("[API] Bootstrap failed: %s", e)
            return False

    # ── Voice conversation worker ──────────────────────────────────────

    def _start_voice_conversation(self):
        if self._voice_worker and self._voice_worker.is_alive():
            return
        self._voice_worker_stop.clear()
        self._voice_worker = threading.Thread(
            target=self._voice_conversation_worker,
            daemon=True, name="voice-conversation",
        )
        self._voice_worker.start()
        logger.info("[API] Voice conversation worker started")

    def _stop_voice_conversation(self):
        self._voice_worker_stop.set()
        if self._voice_worker and self._voice_worker.is_alive():
            self._voice_worker.join(timeout=3.0)
            if self._voice_worker.is_alive():
                logger.warning("[API] Voice worker did not exit in 3s")
        self._voice_worker = None
        logger.info("[API] Voice conversation worker stopped")

    def _voice_conversation_worker(self):
        vm = self.voice_manager
        v = self.voice
        brain = self.brain
        if not vm or not v or not brain:
            logger.error("[VoiceWorker] Missing voice or brain components")
            return

        from voice.voice_state import VoiceState

        while not self._voice_worker_stop.is_set():
            # Wait for wake word
            while not vm._wake_event.wait(timeout=1.0):
                if self._voice_worker_stop.is_set() or not vm._running:
                    return

            if self._voice_worker_stop.is_set() or not vm._running:
                return

            logger.info("[VoiceWorker] Wake detected — starting conversation")
            vm._set_state(VoiceState.WAKE_DETECTED)

            # Greeting
            try:
                greeting = self._do_wake_greeting()
                if greeting and "response" in greeting:
                    v.speak_stream(iter([greeting["response"]]))
                    v.wait_until_done()
            except Exception as e:
                logger.exception("[VoiceWorker] Greeting: %s", e)

            # Conversation loop
            while vm._running and not self._voice_worker_stop.is_set():
                try:
                    event = vm.listen(wake_required=False)
                except Exception as e:
                    logger.error("[VoiceWorker] listen error: %s", e)
                    break

                if event is None:
                    break

                text = event.text.strip() if event.text else ""
                if not text:
                    continue

                logger.info("[VoiceWorker] Heard: %s", text)

                if text.lower() in ("goodbye", "bye", "see you", "exit", "quit"):
                    try:
                        v.speak_stream(iter(["Goodbye!"]))
                        v.wait_until_done()
                    except Exception as e:
                        logger.exception("[VoiceWorker] Goodbye: %s", e)
                    break

                vm.set_speaking(True, v.interrupt)
                try:
                    response = brain.think(text)
                    response_str = str(response)
                except Exception as e:
                    logger.exception("[VoiceWorker] Brain: %s", e)
                    response_str = "Sorry, I had trouble processing that."

                try:
                    v.speak_stream(iter([response_str]))
                    v.wait_until_done()
                except Exception as e:
                    logger.exception("[VoiceWorker] Speak: %s", e)

                vm.set_speaking(False)

            # Restart wake detection for next conversation
            vm._wake_event.clear()
            vm._set_state(VoiceState.LISTENING_FOR_WAKE)
            vm._start_wake_detection()


def _suppress_win_connection_reset(loop, context):
    """Suppress harmless ``ConnectionResetError`` on Windows ``ProactorEventLoop``.

    This is a well-known CPython issue — when a client disconnects abruptly,
    the internal ``_call_connection_lost`` callback tries to ``shutdown()`` the
    already-closed socket, raising ``ConnectionResetError``.  The error is
    harmless but noisy in the logs.
    """
    exc = context.get("exception")
    if isinstance(exc, ConnectionResetError) and "WinError 10054" in str(exc):
        return
    loop.default_exception_handler(context)


async def lifespan(app_lifespan):
    loop = asyncio.get_running_loop()
    loop.set_exception_handler(_suppress_win_connection_reset)
    success = mai.bootstrap()
    if not success:
        logger.warning("[API] System bootstrap failed (some features unavailable)")
    yield
    mai.cleanup()


# ── OpenTelemetry tracing — strictly opt-in (Phase 2b) ────────────────
def _maybe_init_otel() -> bool:
    """Initialize OpenTelemetry only when MAI_OTEL_ENABLED is truthy
    (1/true/yes/on). Default is OFF — boot behavior is unchanged.

    Optional env: MAI_OTEL_ENDPOINT (OTLP collector, e.g.
    http://localhost:4317) and MAI_OTEL_SAMPLE_RATE (default 0.1).
    Missing opentelemetry-instrumentation-* packages degrade to
    tracing-without-auto-instrumentation — never a boot failure.
    """
    if os.getenv("MAI_OTEL_ENABLED", "").strip().lower() not in ("1", "true", "yes", "on"):
        return False
    try:
        from core.observability.opentelemetry_tracing import init_tracing
        endpoint = (os.getenv("MAI_OTEL_ENDPOINT") or "").strip() or None
        try:
            sample_rate = max(0.0, min(1.0, float(os.getenv("MAI_OTEL_SAMPLE_RATE", "0.1"))))
        except ValueError:
            sample_rate = 0.1
        init_tracing(service_name="mai-ai", otlp_endpoint=endpoint, sample_rate=sample_rate)
        logger.info(
            "[API] OpenTelemetry tracing enabled (endpoint=%s, sample_rate=%.2f)",
            endpoint or "local-only", sample_rate,
        )
        return True
    except Exception as exc:
        logger.warning("[API] OpenTelemetry requested but unavailable: %s", exc)
        return False


# Runs before FastAPI() is constructed so global instrumentation hooks
# (when the opentelemetry-instrumentation extras are installed) see the app.
_otel_active = _maybe_init_otel()

app = FastAPI(title="Mai AI API", version="2.0.0", lifespan=lifespan)
app.include_router(routes_auth.router)
app.include_router(routes_profile.router)
app.include_router(plugins_router)

# ── CORS ──────────────────────────────────────────────────────────────────
_cors_origins = [o.strip() for o in API_CORS_ORIGINS.split(",") if o.strip()] if API_CORS_ORIGINS else ["*"]
# Browsers reject the wildcard + credentials combo outright; credentials are
# only meaningful with explicit origins (S-4).
_allow_credentials = _cors_origins != ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Trusted host filtering (only when explicit origins are set) ────────────
if _cors_origins != ["*"]:
    _trusted = [h.strip() for h in API_TRUSTED_HOSTS.split(",") if h.strip()]
    if "pytest" in sys.modules and "testserver" not in _trusted:
        _trusted.append("testserver")
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=_trusted)


# ── Prometheus HTTP metrics (Phase 2b) ────────────────────────────────────
try:
    from core.observability.prometheus_metrics import PrometheusMiddleware

    app.add_middleware(PrometheusMiddleware)
    _prometheus_active = True
except Exception as _prom_exc:  # prometheus_client missing — API still boots
    _prometheus_active = False
    logger.warning("[API] Prometheus metrics middleware unavailable: %s", _prom_exc)


_CSP = (
    "default-src 'self'; "
    "script-src 'self' https://cdn.jsdelivr.net https://unpkg.com; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; "
    "connect-src 'self'; "
    "font-src 'self'; "
    "media-src 'self'; "
    "object-src 'none'; "
    "frame-src 'none'; "
    "base-uri 'self'; "
    "form-action 'self'"
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Content-Security-Policy"] = _CSP
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = (
        "camera=(), microphone=(), geolocation=(), interest-cohort=()"
    )
    if request.url.scheme == "https":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


mai = MaiAPI(host=API_HOST, port=API_PORT)


# Backwards-compatible module-level alias for callers/tests that built the
# dashboard state directly (delegates to the running ``mai`` instance).
def _build_dashboard_state():
    return mai.build_dashboard_state()


# ── Security: optional bearer auth + simple rate limit ────────────────────
def _require_auth(request: Request):
    """Single-source auth dependency — delegates to ``api.auth`` so route
    protection and JWT/static-token logic cannot drift (S-4)."""
    from api.auth import get_current_user
    get_current_user(request)


def _resolve_user(request: Request) -> str:
    """Extract username from JWT or fall back to anonymous."""
    if not API_REQUIRE_AUTH:
        return "anonymous"
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return "anonymous"
    token = auth[len("Bearer "):]
    try:
        from api.auth import decode_token
        payload = decode_token(token)
        if payload.get("type") == "access":
            return payload.get("sub", "anonymous")
    except Exception:
        pass
    return "anonymous"


_rate_limiter = RateLimiter()


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    path = request.url.path
    if RateLimiter.is_static_path(path):
        return await call_next(request)
    client = request.client.host if request.client else "anon"
    try:
        info = _rate_limiter.check(client, path, request.method)
    except HTTPException:
        raise
    response = await call_next(request)
    response.headers["X-RateLimit-Limit"] = str(info["limit"])
    response.headers["X-RateLimit-Remaining"] = str(info["remaining"])
    response.headers["X-RateLimit-Reset"] = str(info["reset"])
    return response


class ChatRequest(BaseModel):
    message: str

    @field_validator("message")
    @classmethod
    def message_length(cls, v):
        if len(v) > 10000:
            raise ValueError("message exceeds 10000 characters")
        return v


class IngestRequest(BaseModel):
    source: str = "api"
    text: Optional[str] = None
    file_path: Optional[str] = None
    directory: Optional[str] = None

    @field_validator("text", "file_path", "directory")
    @classmethod
    def field_length(cls, v):
        if v is not None and len(v) > 50000:
            raise ValueError("field exceeds 50000 characters")
        return v


@app.get("/api/health")
def health():
    if not mai._ready:
        return {"status": "starting", "ready": False}
    return {"status": "ok", "ready": True}


@app.get("/api/health/metrics")
def health_metrics():
    try:
        import psutil
    except ImportError:
        psutil = None
    if psutil is None:
        metrics = {
            "uptime_seconds": round(time.time() - mai._start_time, 1) if hasattr(mai, "_start_time") else 0,
            "process": {
                "cpu_percent": None,
                "memory_rss_mb": None,
                "memory_vms_mb": None,
                "thread_count": None,
                "handle_count": None,
            },
            "system": {
                "cpu_percent": None,
                "memory_percent": None,
                "disk_percent": None,
            },
            "degraded": "psutil_unavailable",
        }
    else:
        process = psutil.Process()
        mem = process.memory_info()
        metrics = {
            "uptime_seconds": round(time.time() - mai._start_time, 1) if hasattr(mai, "_start_time") else 0,
            "process": {
                "cpu_percent": process.cpu_percent(interval=0),
                "memory_rss_mb": round(mem.rss / 1048576, 1),
                "memory_vms_mb": round(mem.vms / 1048576, 1),
                "thread_count": process.num_threads(),
                "handle_count": process.num_handles() if hasattr(process, "num_handles") else 0,
            },
            "system": {
                "cpu_percent": psutil.cpu_percent(interval=0),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": psutil.disk_usage(".").percent,
            },
        }
    # Collect component stats
    for ckey, cattr in [
        ("components", "health_registry"),
        ("vector_store", "vector_store"),
        ("brain_graph", "brain_graph"),
        ("knowledge_graph", "knowledge_graph"),
        ("belief_engine", "belief_engine"),
    ]:
        comp = getattr(mai, cattr, None)
        if comp is not None and hasattr(comp, "stats"):
            try:
                metrics[ckey] = comp.stats()
            except Exception:
                pass
    if getattr(mai, "profile_store", None) and hasattr(mai.profile_store, "count_users"):
        metrics["users"] = {"total": mai.profile_store.count_users()}
    return metrics


# ── Prometheus scrape endpoint (Phase 2b) ─────────────────────────────────
@app.get("/metrics")
def prometheus_metrics_endpoint(request: Request, _: None = Depends(_require_auth)):
    """Prometheus scrape endpoint — auth-gated via ``_require_auth``.

    Returns the text exposition format for the ``mai_*`` metric families.
    Degrades to 503 with a stable error when ``prometheus_client`` is not
    installed; the API itself always boots.
    """
    try:
        from core.observability.prometheus_metrics import (
            get_metrics,
            update_system_metrics,
        )
        try:
            update_system_metrics()  # refresh CPU/memory gauges (psutil optional)
        except Exception as exc:
            logger.debug("[API] system metrics refresh skipped: %s", exc)
        return get_metrics()
    except Exception as exc:
        logger.warning("[API] /metrics unavailable: %s", exc)
        return JSONResponse(status_code=503, content={"error": "metrics_unavailable"})


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await mai.ws_bridge.handle_ws(websocket)


@app.get("/api/stream")
async def event_stream(request: Request):
    queue: asyncio.Queue = asyncio.Queue()
    sm = mai.stream_manager
    sm.add_queue(queue, loop=asyncio.get_running_loop())
    async def generate():
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    data = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield f"data: {data}\n\n"
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            sm.remove_queue(queue)
    return StreamingResponse(generate(), media_type="text/event-stream")


@app.post("/api/chat")
def chat(req: ChatRequest, request: Request, _: None = Depends(_require_auth)):

    if not req.message:
        return JSONResponse(status_code=400, content={"error": "message_required"})
    user_id = _resolve_user(request)
    result = mai.chat(req.message, user_id=user_id)
    if "error" in result:
        return JSONResponse(status_code=500, content={"error": result["error"]})
    return result


@app.post("/api/chat/stream")
def chat_stream(req: ChatRequest, request: Request, _: None = Depends(_require_auth)):

    if not req.message or not mai.brain:
        return JSONResponse(status_code=400, content={"error": "message_required"})
    user_id = _resolve_user(request)
    async def generate():
        for token in mai.brain.think_stream(req.message, user_id=user_id):
            yield f"data: {json.dumps({'token': token})}\n\n"
    return StreamingResponse(generate(), media_type="text/event-stream")


@app.post("/api/chat/wake")
def chat_wake(request: Request, _: None = Depends(_require_auth)):

    result = mai.chat_wake()
    if "error" in result:
        return JSONResponse(status_code=500, content={"error": result["error"]})
    return result


@app.get("/api/status")
def status(request: Request):

    return mai.status()


@app.get("/api/memory")
def memory(request: Request, query: str = "", top_k: int = 5):

    result = mai.memory_query(query, top_k)
    if "error" in result:
        return JSONResponse(status_code=500, content={"error": result["error"]})
    return result


@app.get("/api/memory/stats")
def memory_stats(request: Request):

    return mai.memory_stats()


@app.get("/api/memory/timeline")
def memory_timeline(request: Request, limit: int = 50):

    result = mai.memory_timeline(limit)
    if "error" in result:
        return JSONResponse(status_code=500, content={"error": result["error"]})
    return result


@app.post("/api/knowledge/ingest")
def ingest(req: IngestRequest, request: Request,
           _: None = Depends(_require_auth)):

    result = mai.knowledge_ingest(req.source, text=req.text, file_path=req.file_path, directory=req.directory)
    if "error" in result:
        return JSONResponse(status_code=400, content={"error": result["error"]})
    return result


@app.get("/api/state")
def api_state(request: Request):

    return mai.build_dashboard_state()


@app.get("/api/consciousness")
def api_consciousness(request: Request):

    return mai.consciousness_state()


@app.get("/api/goals")
def agency_goals(request: Request, _: None = Depends(_require_auth)):

    return mai.agency_goals()


@app.get("/api/tools")
def agency_tools(request: Request, _: None = Depends(_require_auth)):

    return mai.agency_tools()


@app.get("/api/world/entities")
def agency_world(request: Request, _: None = Depends(_require_auth)):

    return mai.agency_world()


@app.get("/api/reasoning/thoughts")
def reasoning_thoughts(request: Request, limit: int = 50, _: None = Depends(_require_auth)):

    return mai.reasoning_thoughts(max(1, min(limit, 100)))


@app.get("/api/reasoning/reflect")
def reasoning_reflect(request: Request, _: None = Depends(_require_auth)):

    return mai.reasoning_reflect()


@app.get("/api/reasoning/reflect/history")
def reasoning_reflect_history(request: Request, _: None = Depends(_require_auth)):

    return mai.reasoning_reflect_history()


@app.get("/api/voice/status")
def voice_status(request: Request, _: None = Depends(_require_auth)):

    return mai.voice_status()


@app.get("/api/voice/details")
def voice_details(request: Request, _: None = Depends(_require_auth)):

    return mai.voice_details()


@app.post("/api/voice/toggle")
def voice_toggle(request: Request, _: None = Depends(_require_auth)):

    return mai.voice_toggle()


@app.get("/api/system/health")
def system_health(request: Request, _: None = Depends(_require_auth)):

    return mai.system_health()


@app.get("/api/system/plugins")
def system_plugins(request: Request, _: None = Depends(_require_auth)):

    return mai.system_plugins()


@app.post("/api/system/plugins/{name}/load")
def system_plugin_load(name: str, request: Request, _: None = Depends(_require_auth)):

    return mai.system_plugin_load(name)


@app.post("/api/system/plugins/{name}/unload")
def system_plugin_unload(name: str, request: Request, _: None = Depends(_require_auth)):

    return mai.system_plugin_unload(name)


@app.get("/api/system/about")
def system_about(request: Request, _: None = Depends(_require_auth)):

    return mai.system_about()


@app.get("/api/system/orchestrator")
def system_orchestrator(request: Request, _: None = Depends(_require_auth)):

    return mai.system_orchestrator()


@app.get("/api/config")
def system_config(request: Request, _: None = Depends(_require_auth)):

    return mai.system_config_all()


@app.post("/api/config/update")
def system_config_update(body: dict, request: Request, _: None = Depends(_require_auth)):

    return mai.system_config_update(body)


# ── Clipboard Bridge ────────────────────────────────────────────────────────


@app.get("/api/system/clipboard")
def clipboard_read(request: Request):

    return mai.system_clipboard_read()


class ClipboardWriteRequest(BaseModel):
    text: str


@app.post("/api/system/clipboard")
def clipboard_write(body: ClipboardWriteRequest, request: Request):

    return mai.system_clipboard_write(body.text)


# ── File System Bridge ─────────────────────────────────────────────────────


@app.get("/api/system/fs/list")
def fs_list(path: str = "", request: Request = None):

    return mai.system_fs_list(path)


@app.get("/api/system/fs/read")
def fs_read(path: str = "", request: Request = None):

    return mai.system_fs_read(path)


class FsWriteRequest(BaseModel):
    path: str
    content: str


@app.post("/api/system/fs/write")
def fs_write(body: FsWriteRequest, request: Request):

    return mai.system_fs_write(body.path, body.content)


@app.get("/api/tasks")
def tasks_list(request: Request):

    return mai.tasks_list()


@app.post("/api/tasks/create")
def tasks_create(body: dict, request: Request, _: None = Depends(_require_auth)):

    return mai.tasks_create(body)


@app.post("/api/tasks/{goal_id}/complete")
def tasks_complete(goal_id: str, request: Request, _: None = Depends(_require_auth)):

    return mai.tasks_complete(goal_id)


@app.post("/api/tasks/{goal_id}/cancel")
def tasks_cancel(goal_id: str, request: Request, _: None = Depends(_require_auth)):

    return mai.tasks_cancel(goal_id)


@app.post("/api/tasks/{goal_id}/activate")
def tasks_activate(goal_id: str, request: Request, _: None = Depends(_require_auth)):

    return mai.tasks_activate(goal_id)


@app.post("/api/tasks/{goal_id}/subtasks")
def tasks_add_subtask(goal_id: str, body: dict, request: Request, _: None = Depends(_require_auth)):

    return mai.tasks_add_subtask(goal_id, body)


@app.post("/api/tasks/{goal_id}/subtasks/{subtask_id}/complete")
def tasks_complete_subtask(goal_id: str, subtask_id: str, request: Request, _: None = Depends(_require_auth)):

    return mai.tasks_complete_subtask(goal_id, subtask_id)


@app.get("/api/tasks/procedural")
def tasks_procedural(request: Request):

    return mai.tasks_procedural()


@app.get("/api/permissions")
def permissions_all(request: Request, _: None = Depends(_require_auth)):

    return mai.permissions_all()


@app.post("/api/permissions/mode")
def permissions_set_mode(body: dict, request: Request, _: None = Depends(_require_auth)):

    return mai.permissions_set_mode(body)


@app.get("/api/graph")
def dashboard_graph(request: Request, _: None = Depends(_require_auth)):

    return mai.dashboard_graph()


@app.post("/api/graph/prune")
def dashboard_graph_prune(request: Request, _: None = Depends(_require_auth)):

    return mai.dashboard_graph_prune()


# ── Event Inspector ──────────────────────────────────────────────

@app.get("/api/inspector/records")
def inspector_records(request: Request, type: str = "", source: str = "",
                      outcome: str = "", priority: str = "",
                      correlation_id: str = "", since: float = 0.0,
                      retries: int = 0, limit: int = 100, offset: int = 0,
                      _: None = Depends(_require_auth)):

    filters = {
        "type": type or None,
        "source": source or None,
        "outcome": outcome or None,
        "priority": priority or None,
        "correlation_id": correlation_id or None,
        "since": since if since > 0 else None,
        "retries": retries if retries else None,
    }
    return mai.inspector_records(filters=filters, limit=limit, offset=offset)


@app.get("/api/inspector/record/{record_id}")
def inspector_record(record_id: str, request: Request, _: None = Depends(_require_auth)):

    return mai.inspector_record(record_id)


@app.get("/api/inspector/trace/{correlation_id}")
def inspector_trace(correlation_id: str, request: Request, _: None = Depends(_require_auth)):

    return mai.inspector_trace(correlation_id)


@app.get("/api/inspector/subscribers")
def inspector_subscribers(request: Request, _: None = Depends(_require_auth)):

    return mai.inspector_subscribers()


@app.get("/api/inspector/queues")
def inspector_queues(request: Request, _: None = Depends(_require_auth)):

    return mai.inspector_queues()


@app.get("/api/inspector/dead_letters")
def inspector_dead_letters(request: Request, since: float = 0.0,
                           _: None = Depends(_require_auth)):

    return mai.inspector_dead_letters(since=since if since > 0 else None)


@app.get("/api/inspector/latency")
def inspector_latency(request: Request, scope: str = "type", _: None = Depends(_require_auth)):

    return mai.inspector_latency(scope=scope)


@app.get("/api/inspector/health")
def inspector_health(request: Request, _: None = Depends(_require_auth)):

    return mai.inspector_health()


@app.get("/api/inspector/summary")
def inspector_summary(request: Request, _: None = Depends(_require_auth)):

    return mai.inspector_summary()


@app.post("/api/inspector/export")
def inspector_export(request: Request, _: None = Depends(_require_auth)):

    return mai.inspector_export()


# ── Model Lifecycle ──────────────────────────────────────────────────────────

@app.get("/api/model/lifecycle")
def model_lifecycle_summary(request: Request, _: None = Depends(_require_auth)):
    return mai.model_lifecycle_summary()

@app.get("/api/model/{model_id}")
def model_lifecycle_model(model_id: str, request: Request, _: None = Depends(_require_auth)):
    return mai.model_lifecycle_model(model_id)

@app.post("/api/model/{model_id}/register")
def model_lifecycle_register(
    model_id: str,
    version: str,
    model_type: str,
    name: str,
    description: str,
    file_path: str,
    source_url: str = "",
    framework: str = "unknown",
    framework_version: str = "unknown",
    input_schema: dict = None,
    output_schema: dict = None,
    tags: list = None,
    config: dict = None,
    request: Request = None,
    _: None = Depends(_require_auth)
):
    return mai.model_lifecycle_register(
        model_id, version, model_type, name, description, file_path,
        source_url, framework, framework_version, input_schema, output_schema, tags, config
    )

@app.post("/api/model/{model_id}/{version}/rollout")
def model_lifecycle_rollout_start(
    model_id: str, version: str,
    strategy: str = "canary",
    canary_percentage: float = 5.0,
    canary_duration: int = 300,
    progressive_steps: list = None,
    step_duration: int = 300,
    error_threshold: float = 0.01,
    latency_threshold: float = 2.0,
    request: Request = None,
    _: None = Depends(_require_auth)
):
    return mai.model_lifecycle_rollout_start(
        model_id, version, strategy, canary_percentage, canary_duration,
        progressive_steps, step_duration, error_threshold, latency_threshold
    )

@app.get("/api/model/{model_id}/{version}/rollout")
def model_lifecycle_rollout_status(model_id: str, version: str, request: Request, _: None = Depends(_require_auth)):
    return mai.model_lifecycle_rollout_status(model_id, version)

@app.post("/api/model/{model_id}/{version}/rollout/pause")
def model_lifecycle_rollout_pause(model_id: str, version: str, request: Request, _: None = Depends(_require_auth)):
    return mai.model_lifecycle_rollout_pause(model_id, version)

@app.post("/api/model/{model_id}/{version}/rollout/resume")
def model_lifecycle_rollout_resume(model_id: str, version: str, request: Request, _: None = Depends(_require_auth)):
    return mai.model_lifecycle_rollout_resume(model_id, version)

@app.post("/api/model/{model_id}/{version}/rollout/abort")
def model_lifecycle_rollout_abort(model_id: str, version: str, reason: str = "Manual abort", request: Request = None, _: None = Depends(_require_auth)):
    return mai.model_lifecycle_rollout_abort(model_id, version, reason)

@app.post("/api/model/{model_id}/{version}/rollback")
def model_lifecycle_rollback(model_id: str, version: str, reason: str = "Manual trigger", request: Request = None, _: None = Depends(_require_auth)):
    return mai.model_lifecycle_rollback(model_id, version, reason)

@app.get("/api/model/rollbacks")
def model_lifecycle_rollback_history(model_id: str = None, limit: int = 100, request: Request = None, _: None = Depends(_require_auth)):
    return mai.model_lifecycle_rollback_history(model_id, limit)

@app.post("/api/model/{model_id}/{version}/promote")
def model_lifecycle_promote(model_id: str, version: str, request: Request, _: None = Depends(_require_auth)):
    return mai.model_lifecycle_promote(model_id, version)

@app.post("/api/model/{model_id}/{version}/deprecate")
def model_lifecycle_deprecate(model_id: str, version: str, request: Request, _: None = Depends(_require_auth)):
    return mai.model_lifecycle_deprecate(model_id, version)

@app.post("/api/model/{model_id}/{version}/archive")
def model_lifecycle_archive(model_id: str, version: str, request: Request, _: None = Depends(_require_auth)):
    return mai.model_lifecycle_archive(model_id, version)

@app.get("/api/model/{model_id}/{version}/metrics")
def model_lifecycle_metrics(model_id: str, version: str, request: Request, _: None = Depends(_require_auth)):
    return mai.model_lifecycle_metrics(model_id, version)

@app.get("/api/model/{model_id}/{version}/verify")
def model_lifecycle_verify(model_id: str, version: str, request: Request, _: None = Depends(_require_auth)):
    return mai.model_lifecycle_verify(model_id, version)


@app.get("/")
def index():
    return make_html_response("presence")


@app.get("/desktop")
def desktop():
    # The M0 dashboard lives at /desktop and is served as index.html. The v3.x
    # Cognitive Desktop retired this entry point by redirecting to /presence;
    # that redirect was reverted when api/static was restored, so the original
    # dashboard URL works again.
    return make_html_response("index")


# Register all subsystem pages — handle both /page and /page/ (browsers add trailing slashes)
from functools import partial

_page_files = ["consciousness", "chat", "memory", "graph", "reasoning", "agency", "voice", "system", "tasks", "permissions", "inspector", "marketplace", "login", "presence"]

for _pf in _page_files:
    # Without trailing slash
    app.get(f"/{_pf}", response_class=HTMLResponse)(
        partial(make_html_response, _pf)
    )
    # With trailing slash — redirect to non-slash version
    app.get(f"/{_pf}/", response_class=HTMLResponse)(
        partial(make_html_response, _pf)
    )

# Static files mount at root — must be AFTER page routes so routes take priority
if os.path.isdir(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")


def run(host=None, port=None):
    host = host or mai.host or API_HOST
    port = port or mai.port or API_PORT
    mai.host = host
    mai.port = port

    ssl_certfile = API_SSL_CERTFILE or os.environ.get("API_SSL_CERTFILE", "")
    ssl_keyfile = API_SSL_KEYFILE or os.environ.get("API_SSL_KEYFILE", "")
    ssl_enabled = bool(ssl_certfile and ssl_keyfile)

    if not ssl_enabled:
        cert_path, key_path = ensure_dev_certs()
        if cert_path and key_path:
            ssl_certfile = cert_path
            ssl_keyfile = key_path
            ssl_enabled = True

    protocol = "https" if ssl_enabled else "http"
    url = f"{protocol}://{host if host != '0.0.0.0' else 'localhost'}:{port}"
    print(f"\n  ~~ Mai OS ~~ {url}\n", flush=True)
    logger.info("[API] Starting on %s (auth=%s, ssl=%s)", url, bool(API_REQUIRE_AUTH and API_AUTH_TOKEN), ssl_enabled)

    # SEC-002/SEC-003: enforce auth on non-localhost binding
    on_non_localhost = host not in ("127.0.0.1", "localhost")
    if on_non_localhost and not (API_REQUIRE_AUTH and API_AUTH_TOKEN):
        logger.warning(
            "[API] SECURITY: binding on %s without API_REQUIRE_AUTH/API_AUTH_TOKEN. "
            "The API will be reachable from the network. Set API_REQUIRE_AUTH=True and "
            "API_AUTH_TOKEN to a secret value, or bind to 127.0.0.1.",
            host,
        )

    uvicorn_kwargs = dict(host=host, port=port, log_level="info")
    if ssl_enabled:
        uvicorn_kwargs["ssl_certfile"] = ssl_certfile
        uvicorn_kwargs["ssl_keyfile"] = ssl_keyfile
    uvicorn.run(app, **uvicorn_kwargs)


if __name__ == "__main__":
    run()
