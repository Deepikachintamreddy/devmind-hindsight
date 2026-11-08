"""
DevMind — FastAPI Application Entry Point
"""
from contextlib import asynccontextmanager
from pathlib import Path
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.routes.debug import router as debug_router
from backend.routes.seed import router as seed_router
from backend.config import APP_PORT, get_app_mode

logger = logging.getLogger("devmind")


# ── Lifespan Events ───────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create Hindsight memory bank with acreate_bank in a try/except
    try:
        from backend.services.memory import init_memory_bank
        await init_memory_bank()
    except Exception as e:
        logger.warning(f"Startup Hindsight bank initialization notice: {e}")
    yield
    # Shutdown: clean up client sessions if open
    try:
        from backend.services.memory import close_client
        await close_client()
    except Exception:
        pass


# ── App Setup ────────────────────────────────────────────────────
app = FastAPI(
    title="DevMind — Developer Debugging Memory Agent",
    description=(
        "An AI agent that never forgets a bug. "
        "Powered by Hindsight persistent memory + Groq LLM."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow all origins for local development and demo
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ──────────────────────────────────────────────────────
app.include_router(debug_router)
app.include_router(seed_router)

# ── Static Frontend ──────────────────────────────────────────────
FRONTEND_DIR = Path(__file__).parent / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR / "static")), name="static")

    @app.get("/", include_in_schema=False)
    async def serve_frontend():
        return FileResponse(str(FRONTEND_DIR / "index.html"))


# ── Health Check ─────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {
        "status": "ok",
        "app": "DevMind",
        "version": "1.0.0",
        "mode": get_app_mode(),
    }


# ── Run ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=APP_PORT, reload=True)
