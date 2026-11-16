import asyncio
import contextlib
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import database
from app.live_devices import run_live_devices
from app.routers import astronauts, devices, indicators
from scripts.generate_data import seed_if_empty


@asynccontextmanager
async def lifespan(_: FastAPI):
    database.init_db()
    # Fresh checkout → simulated demo data. Existing data (incl. manual entries) is never touched.
    if os.environ.get("HOUSTON_PULSE_NO_SEED") != "1":
        seed_if_empty(database.engine)
    # Optional demo mode: smart shirts stream a simulated heart rate every 5 s. Off by default.
    task = asyncio.create_task(run_live_devices()) if os.environ.get("HP_SIMULATE_DEVICES") == "1" else None
    yield
    if task:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


app = FastAPI(title="Houston Pulse API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(astronauts.router)
app.include_router(indicators.router)
app.include_router(indicators.env_router)
app.include_router(devices.router)


@app.get("/health")
def health():
    return {"status": "ok"}
