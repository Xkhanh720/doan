from fastapi import APIRouter, Response
from fastapi.responses import JSONResponse

from ..db import get_settings
from ..models import DisplayResponse
from ..scheduler import get_now
from ..sources.weather import load_cache

router = APIRouter(tags=["display"])


def _today_events() -> list[dict]:
    from ..db import get_conn

    today = get_now()["date"]
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM events WHERE event_date = ? ORDER BY sort_order, id",
            (today,),
        ).fetchall()
    return [dict(r) for r in rows]


@router.get("/api/display", response_model=DisplayResponse)
def display() -> dict:
    settings = get_settings()
    return {
        "title": settings.get("display_title", "Bảng thông tin"),
        "now": get_now(),
        "weather": load_cache(),
        "events": _today_events(),
        "poll_hint_seconds": int(settings.get("poll_hint_seconds", 30)),
    }


@router.get("/api/time")
def time_now() -> dict:
    return get_now()


@router.get("/api/health")
def health() -> JSONResponse:
    return JSONResponse({"status": "ok", "now": get_now()})


@router.get("/")
def root(response: Response) -> dict:
    response.headers["Cache-Control"] = "no-store"
    return {
        "service": "pi-display-server",
        "endpoints": [
            "GET /api/display",
            "GET /api/time",
            "GET /api/weather?refresh=true",
            "POST /api/weather/refresh",
            "GET|POST /api/events",
            "GET|PUT|DELETE /api/events/{id}",
            "GET|PUT /api/settings",
            "GET /api/health",
            "GET /docs",
        ],
    }
