from __future__ import annotations

from fastapi import FastAPI

from app.api.runs import router as runs_router
from app.api.uploads import router as uploads_router

app = FastAPI(title="Paytly Backend API", version="0.1.0")

app.include_router(uploads_router)
app.include_router(runs_router)
