# api/ — HTTP Interface Layer

This package is the **interface** between MAI and the outside world. It owns
HTTP, nothing else.

```
api/
├── server.py            FastAPI application, middleware, page routes
├── auth.py              JWT issuance/validation, auth dependency
├── routes_*.py          Endpoint groups (memory, agency, voice, system, …)
├── middleware/          Rate limiting, security headers
├── stream_manager.py    SSE stream
├── ws_bridge.py         WebSocket bridge
├── static_serving.py    Static file delivery
├── static/              Served frontend (v3.x interface, still live)
└── web/                 MAI Cognitive Entity Interface (v4.0) — NEW
```

## The one thing to know

**`api/web/` is not part of the HTTP layer.** It is the new MAI entity interface
— Three.js, GLSL, and GSAP code that renders a sphere and has no relationship to
HTTP whatsoever. It lives here only because this package already owns static
delivery.

New presentation code goes in `api/web/`, governed by
[`api/web/README.md`](web/README.md). The Python intelligence stays in its own
subsystems (`core/`, `memory/`, `knowledge/`, `voice/`, `agency/`, …) and is
**not** relocated here.

## Do not

- Put entity or presentation logic in `server.py` or a route module.
- Import from `api/web/` into backend Python — the dependency only runs one way.
- Add a second state store, event bus, or HTTP client on the frontend. The
  interface consumes the existing `state.*` event fabric and `api-client.js`.

## Related

- [[MAI Cognitive Entity Interface Plan]] — v4.0 product and implementation plan
- [[ADR Presentation Layer Restructure]] — why `api/web/` and not a repo root
- [[08-API Native & Surface]] — served routes
- [[09-Events & Data Flow]] — event pipeline
