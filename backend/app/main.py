import os
import sys
from pathlib import Path
from contextlib import asynccontextmanager

# Configure project paths and headless matplotlib
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from backend.app.config import settings
from backend.app.database import engine, Base, SessionLocal
from backend.app.core.rule_engine import rule_engine
from ml.inference import ml_inference

# Import all API routers
from backend.app.api.routes.auth import router as auth_router
from backend.app.api.routes.dashboard import router as dashboard_router
from backend.app.api.routes.engines import router as engines_router
from backend.app.api.routes.alerts import router as alerts_router
from backend.app.api.routes.maintenance import router as maintenance_router
from backend.app.api.routes.spares import router as spares_router
from backend.app.api.routes.fleet import router as fleet_router
from backend.app.api.routes.reports import router as reports_router
from backend.app.api.routes.data import router as data_router
from backend.app.api.routes.system import router as system_router
from backend.app.api.routes.simulator import router as simulator_router
from backend.app.api.routes.settings import router as settings_router
from backend.app.api.routes.audit import router as audit_router
from backend.app.api.routes.health import router as health_router
from backend.app.api.routes.websocket import router as ws_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup actions
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        rule_engine.load_rules(db)
    finally:
        db.close()

    # Load ML models if enabled
    if settings.ML_ENABLED:
        ml_inference.load_models()

    yield

    # Shutdown actions
    from backend.app.services.simulator import sim_manager
    sim_manager.stop()

app = FastAPI(
    title="VAJRA: Predictive Maintenance & Fleet Availability Platform",
    description="Smart India Hackathon 2026 — Problem Statement 26249 (Ministry of Defence)",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS setup
origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(",") if origin.strip()]
if "http://localhost:3000" not in origins:
    origins.extend(["http://localhost:3000", "http://localhost:8000", "http://127.0.0.1:3000", "http://127.0.0.1:8000"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r".*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Consistent global error handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # Let FastAPI HTTPException pass through naturally
    from fastapi import HTTPException
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=getattr(exc, "headers", None)
        )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": f"Internal Server Error: {str(exc)}"}
    )

# Include API routes under /api
api_prefix = "/api"
app.include_router(auth_router, prefix=api_prefix)
app.include_router(dashboard_router, prefix=api_prefix)
app.include_router(engines_router, prefix=api_prefix)
app.include_router(alerts_router, prefix=api_prefix)
app.include_router(maintenance_router, prefix=api_prefix)
app.include_router(spares_router, prefix=api_prefix)
app.include_router(fleet_router, prefix=api_prefix)
app.include_router(reports_router, prefix=api_prefix)
app.include_router(data_router, prefix=api_prefix)
app.include_router(system_router, prefix=api_prefix)
app.include_router(simulator_router, prefix=api_prefix)
app.include_router(settings_router, prefix=api_prefix)
app.include_router(audit_router, prefix=api_prefix)
app.include_router(health_router, prefix=api_prefix)

# Include WebSocket routes
app.include_router(ws_router)

# Ensure glTF/GLB MIME types are properly recognized
import mimetypes
mimetypes.add_type("model/gltf-binary", ".glb")
mimetypes.add_type("model/gltf+json", ".gltf")

# Mount UI directory as static files (supporting frontend and stitch_vajra_fleet_maintenance_platform)
ui_candidates = [
    ROOT_DIR / "frontend",
    ROOT_DIR / "stitch_vajra_fleet_maintenance_platform",
]
ui_dir = next((p for p in ui_candidates if p.exists() and p.is_dir()), None)
if ui_dir:
    app.mount("/ui", StaticFiles(directory=str(ui_dir), html=True, follow_symlink=True), name="ui")

    @app.get("/", include_in_schema=False)
    async def root_redirect():
        return RedirectResponse(url="/ui/command_dashboard/code.html")

# Mount Assets directory for 3D models and media (supporting Assets, Assets , and lowercase assets)
assets_candidates = [
    ROOT_DIR / "Assets",
    ROOT_DIR / "Assets ",
    ROOT_DIR / "assets",
    ROOT_DIR.parent / "Assets",
    ROOT_DIR.parent / "Assets ",
]
assets_dir = next((p for p in assets_candidates if p.exists() and p.is_dir()), None)
if assets_dir:
    app.mount("/assets", StaticFiles(directory=str(assets_dir), html=False, follow_symlink=True), name="assets")
    app.mount("/Assets", StaticFiles(directory=str(assets_dir), html=False, follow_symlink=True), name="Assets")



