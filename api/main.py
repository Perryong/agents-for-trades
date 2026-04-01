import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from .routes import router

app = FastAPI(title="TradingAgents API")

# Dev: allow Vite dev server origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes first — before any static mount
app.include_router(router)

# Production: serve Vite dist if it exists
DIST_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
if os.path.isdir(DIST_DIR):
    assets_dir = os.path.join(DIST_DIR, "assets")
    if os.path.isdir(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}")
    async def spa_catch_all(full_path: str):
        return FileResponse(os.path.join(DIST_DIR, "index.html"))
