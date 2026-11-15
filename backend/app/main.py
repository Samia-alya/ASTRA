import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import database
from app.routers import astronauts, indicators
from scripts.generate_data import seed_if_empty


@asynccontextmanager
async def lifespan(_: FastAPI):
    database.init_db()
    # Fresh checkout → simulated demo data. Existing data (incl. manual entries) is never touched.
    if os.environ.get("HOUSTON_PULSE_NO_SEED") != "1":
        seed_if_empty(database.engine)
    yield


app = FastAPI(title="Houston Pulse API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(astronauts.router)
app.include_router(indicators.router)


@app.get("/health")
def health():
    return {"status": "ok"}
