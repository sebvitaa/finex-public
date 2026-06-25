from fastapi.testclient import TestClient

from backend.app.core.config import get_settings
from backend.app.main import create_app


def test_health(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_production_cors_allows_vercel_domains(monkeypatch) -> None:
    monkeypatch.setenv("FINEX_ENV", "production")
    get_settings.cache_clear()
    app = create_app(run_startup=False)

    with TestClient(app) as client:
        response = client.options(
            "/health",
            headers={
                "Origin": "https://finex-public-frontend.vercel.app",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "content-type,x-finex-session",
            },
        )

    get_settings.cache_clear()

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://finex-public-frontend.vercel.app"
