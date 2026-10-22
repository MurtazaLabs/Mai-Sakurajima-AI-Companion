from fastapi import HTTPException
from fastapi.testclient import TestClient

from api.server import _require_auth, app


def test_phase_three_read_routes_use_auth_dependency():
    def deny():
        raise HTTPException(status_code=401, detail="denied")

    app.dependency_overrides[_require_auth] = deny
    try:
        with TestClient(app) as client:
            for path in (
                "/api/goals",
                "/api/graph",
                "/api/voice/status",
                "/api/system/health",
                "/api/permissions",
            ):
                response = client.get(path)
                assert response.status_code == 401, path
    finally:
        app.dependency_overrides.pop(_require_auth, None)
