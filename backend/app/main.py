"""FastAPI Application Entry Point & Lifespan Management.

Includes:
- CSRF & CORS Middlewares
- Database Lifespan initialization
- v1 REST API routes
- Static Frontend File Serving & SPA Catch-All Route (Milestone 4 Remediation)
"""
from contextlib import asynccontextmanager
import os
from pathlib import Path
from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.v1.api import api_router
from app.core.config import ensure_data_directories, settings
from app.core.database import engine
from app.models.base import Base


class CSRFMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method in ("POST", "PATCH", "PUT", "DELETE"):
            path = request.url.path.rstrip("/") or "/"
            exempt_prefixes = [
                f"{settings.API_V1_STR}/auth/login",
                f"{settings.API_V1_STR}/intake",
                f"{settings.API_V1_STR}/email",
                f"{settings.API_V1_STR}/portal",
                "/api/v1/auth/login",
                "/api/v1/intake",
                "/api/v1/email",
                "/api/v1/portal",
            ]
            if not any(path.startswith(ex.rstrip("/")) for ex in exempt_prefixes):
                csrf_cookie = request.cookies.get(settings.CSRF_COOKIE_NAME)
                csrf_header = request.headers.get(settings.CSRF_HEADER_NAME)
                if not csrf_cookie or not csrf_header or csrf_cookie != csrf_header:
                    return JSONResponse(
                        status_code=status.HTTP_403_FORBIDDEN,
                        content={"detail": "CSRF validation failed: token missing or mismatched"},
                    )
        return await call_next(request)


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_data_directories()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        lifespan=lifespan,
    )

    # Middleware order: inner CSRFMiddleware, outer CORSMiddleware
    app.add_middleware(CSRFMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount v1 REST API
    app.include_router(api_router, prefix=settings.API_V1_STR)

    @app.get("/health", tags=["Health"])
    async def health():
        return {
            "status": "healthy",
            "version": settings.VERSION,
            "environment": settings.ENVIRONMENT,
        }

    # Locate Frontend Directory
    base_dir = Path(__file__).resolve().parent.parent.parent
    frontend_dir = base_dir / "frontend"
    if not frontend_dir.exists():
        # Fallback check inside backend or relative
        frontend_dir = Path(__file__).resolve().parent.parent / "frontend"

    index_html = frontend_dir / "index.html"
    if not index_html.exists() and (frontend_dir / "dist" / "index.html").exists():
        index_html = frontend_dir / "dist" / "index.html"

    # Mount static assets if frontend directory exists
    if frontend_dir.exists():
        # Mount assets/dist if available
        assets_dir = frontend_dir / "dist" / "assets"
        if assets_dir.exists():
            app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    # SPA Fallback & Static Serving
    @app.get("/", include_in_schema=False)
    async def serve_root():
        if index_html.is_file():
            return FileResponse(str(index_html))
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "CKYC API running. Frontend index.html not found.", "status": "active"},
        )

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(request: Request, full_path: str):
        # 1. Directory traversal & path escape guard: reject traversal attempts immediately with 404 JSON
        if (
            ".." in full_path
            or "%2e" in full_path.lower()
            or ":" in full_path
            or full_path == "backend"
            or full_path.startswith("backend/")
            or full_path == "tests"
            or full_path.startswith("tests/")
            or any(full_path.endswith(ext) for ext in [".py", ".pyc", ".db", ".env", ".log", ".sh", ".ini"])
        ):
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"detail": "Resource not found"})

        # 2. Do not hijack API, health, docs, or schema routes (including bare /api)
        if (
            full_path == "api"
            or full_path.startswith("api/")
            or full_path == "health"
            or full_path.startswith("health/")
            or full_path == "docs"
            or full_path.startswith("docs/")
            or full_path.startswith("openapi.json")
        ):
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"detail": "Not Found"})

        # 3. Serve existing static file if requested (with strict path containment check)
        if frontend_dir.exists() and full_path:
            try:
                candidate = (frontend_dir / full_path).resolve()
                if not candidate.is_relative_to(frontend_dir.resolve()):
                    return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"detail": "Resource not found"})
                if candidate.is_file():
                    return FileResponse(str(candidate))

                dist_candidate = (frontend_dir / "dist" / full_path).resolve()
                if not dist_candidate.is_relative_to((frontend_dir / "dist").resolve()):
                    return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"detail": "Resource not found"})
                if dist_candidate.is_file():
                    return FileResponse(str(dist_candidate))
            except (ValueError, RuntimeError):
                return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"detail": "Resource not found"})

        # 4. Fallback to SPA index.html for client-side routing
        if index_html.is_file():
            return FileResponse(str(index_html))

        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"detail": "Resource not found"})

    return app


app = create_app()
