from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.v1.router import api_router
from backend.app.core.config import get_settings
from backend.app.db.init_db import init_db, init_demo_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    # Keep the demo session migrated + seeded so switching to it always shows data.
    init_demo_db()
    yield


def create_app(run_startup: bool = True) -> FastAPI:
    settings = get_settings()
    allowed_origins = [origin.strip() for origin in settings.allowed_origins.split(",") if origin.strip()]
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        lifespan=lifespan if run_startup else None,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", tags=["health"])
    def health() -> dict[str, str]:
        return {
            "status": "ok",
            "service": "finex",
            "environment": settings.env,
            "version": "0.1.0",
        }

    app.include_router(api_router, prefix="/api/v1")
    return app


app = create_app()
