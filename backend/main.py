import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .config import UPLOAD_DIR
from .db import init_db
from .routers import display, events, settings, weather
from .scheduler import maintenance_loop, weather_loop

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    weather_task = asyncio.create_task(weather_loop())
    maintenance_task = asyncio.create_task(maintenance_loop())
    try:
        yield
    finally:
        weather_task.cancel()
        maintenance_task.cancel()
        for task in (weather_task, maintenance_task):
            try:
                await task
            except asyncio.CancelledError:
                pass


app = FastAPI(
    title="Pi Display Server",
    description="Backend cho hệ thống hiển thị qua Raspberry Pi",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(display.router)
app.include_router(events.router)
app.include_router(weather.router)
app.include_router(settings.router)

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(UPLOAD_DIR)), name="static")
