import json
import asyncio
import logging
from typing import Any, Optional

from fastapi import WebSocket, WebSocketDisconnect

from api.stream_manager import STREAM_TOPICS
from api.errors import safe_error

logger = logging.getLogger("api.server")


class WSBridge:
    """WebSocket bridge — pushes EventBus events to connected WS clients.

    Clients connect via ``GET /ws`` and can:
    - Subscribe to specific topics: ``{"type": "subscribe", "topics": [...]}``
    - Send commands: ``{"type": "command", "action": "wake", "payload": {...}}``
    - Receive events: ``{"topic": "emotion.changed", "data": {...}}``
    """

    def __init__(self, event_bus=None, brain=None, voice_manager=None):
        self.event_bus = event_bus
        self.brain = brain
        self.voice_manager = voice_manager
        self._connections: list[WebSocket] = []
        self._subs: list[Any] = []
        self._lock = asyncio.Lock()
        self._loop = None

    @property
    def client_count(self) -> int:
        return len(self._connections)

    def wire(self, event_bus):
        """Subscribe to all EventBus topics and relay to WS clients.

        Synchronous — safe to call from ``MaiAPI.bootstrap()``
        without creating a new event loop.
        """
        self.event_bus = event_bus
        if not event_bus:
            return

        topics = STREAM_TOPICS
        for topic in topics:
            try:
                sub = event_bus.on(topic, self._make_handler(topic))
                self._subs.append(sub)
            except Exception as e:
                logger.debug("[WS] Subscribe %s: %s", topic, e)
        logger.info("[WS] Wired to event bus (%d topics)", len(topics))

    def _make_handler(self, topic):
        topic_str = str(topic)
        def handler(data):
            payload = json.dumps({"topic": topic_str, "data": data}, default=str)
            self._broadcast(payload)
        return handler

    def _broadcast(self, payload: str):
        """Safely broadcast to all connected clients."""
        if not self._connections:
            return
        loop = self._loop
        if loop is None:
            logger.warning("[WS] no event loop captured — events are being dropped")
            return
        for ws in list(self._connections):
            try:
                asyncio.run_coroutine_threadsafe(
                    ws.send_text(payload), loop
                )
            except Exception as e:
                logger.debug("[WS] Broadcast error: %s", e)

    async def handle_ws(self, websocket: WebSocket):
        """Accept a WebSocket connection and handle messages."""
        await websocket.accept()
        self._loop = asyncio.get_running_loop()
        async with self._lock:
            self._connections.append(websocket)
        logger.info("[WS] Client connected (%d total)", len(self._connections))
        try:
            while True:
                data = await websocket.receive_text()
                await self._handle_message(websocket, data)
        except WebSocketDisconnect:
            pass
        except Exception as e:
            logger.debug("[WS] Connection error: %s", e)
        finally:
            async with self._lock:
                if websocket in self._connections:
                    self._connections.remove(websocket)
            logger.info("[WS] Client disconnected (%d remain)", len(self._connections))

    async def _handle_message(self, websocket: WebSocket, data: str):
        """Process an incoming WS message."""
        try:
            msg = json.loads(data)
        except json.JSONDecodeError:
            await websocket.send_json({"error": "invalid_json"})
            return

        msg_type = msg.get("type")

        if msg_type == "command":
            action = msg.get("action")
            payload = msg.get("payload", {})
            result = await self._execute_command(action, payload)
            if result is not None:
                await websocket.send_json(result)

        elif msg_type == "ping":
            await websocket.send_json({"type": "pong"})

        else:
            await websocket.send_json({"error": f"unknown_type: {msg_type}"})

    async def _execute_command(self, action: str, payload: dict):
        """Execute a command received via WebSocket."""
        actions = {
            "wake": self._cmd_wake,
            "status": self._cmd_status,
        }
        handler = actions.get(action)
        if handler:
            return await handler(payload)
        return {"error": f"unknown_action: {action}"}

    async def _cmd_wake(self, payload: dict) -> dict:
        """Simulate a wake event — triggers voice conversation if voice_manager available."""
        if self.voice_manager:
            try:
                if hasattr(self.voice_manager, "_wake_event"):
                    self.voice_manager._wake_event.set()
                    return {"status": "wake_signal_sent"}
            except Exception as e:
                return {"error": safe_error(e)}
        if self.brain:
            return {"status": "brain_ready"}
        return {"status": "no_voice_manager"}

    async def _cmd_status(self, payload: dict) -> dict:
        """Return a brief system status."""
        status = {"status": "ok"}
        if self.brain:
            try:
                emo = self.brain.state.emotion
                status["emotion"] = {
                    "happy": getattr(emo, "happy", 0),
                    "energy": getattr(emo, "energy", 0),
                }
            except Exception as e:
                status["emotion_error"] = safe_error(e)
        return status

    def shutdown(self):
        """Clean up subscriptions."""
        self._subs.clear()
        self._connections.clear()
