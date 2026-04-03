import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from .routes import router
from .db import engine, Base, ensure_scoring_columns


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create DB tables on startup; release engine on shutdown."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await ensure_scoring_columns()
    yield
    await engine.dispose()


app = FastAPI(title="TradingAgents API", lifespan=lifespan)

# Dev: allow Vite dev server origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes first — before any static mount
app.include_router(router)
from .screener_routes import screener_router
app.include_router(screener_router)
from .chart_routes import chart_router
app.include_router(chart_router)
from .trade_routes import trade_router
app.include_router(trade_router)
from .score_routes import score_router
app.include_router(score_router)

# Production: serve Vite dist if it exists
DIST_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
if os.path.isdir(DIST_DIR):
    assets_dir = os.path.join(DIST_DIR, "assets")
    if os.path.isdir(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}")
    async def spa_catch_all(full_path: str):
        return FileResponse(os.path.join(DIST_DIR, "index.html"))
