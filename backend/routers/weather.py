import logging

from fastapi import APIRouter, HTTPException, Query

from ..scheduler import get_now
from ..sources.weather import fetch_weather, load_cache

logger = logging.getLogger("pi_display.weather")

router = APIRouter(prefix="/api/weather", tags=["weather"])


@router.get("")
async def get_weather(refresh: bool = Query(default=False)) -> dict:
    if refresh:
        try:
            payload = await fetch_weather()
            return {**payload, "stale": False, "age_minutes": 0}
        except Exception as exc:
            logger.exception("weather refresh via GET failed")
            cache = load_cache()
            if cache is None:
                raise HTTPException(502, f"Không lấy được thời tiết: {exc}") from exc
            return {**cache, "refresh_error": str(exc)}
    cache = load_cache()
    if cache is None:
        raise HTTPException(
            503, "Chưa có dữ liệu thời tiết, thử GET /api/weather?refresh=true"
        )
    return cache


@router.post("/refresh")
async def refresh_weather() -> dict:
    try:
        payload = await fetch_weather()
    except Exception as exc:
        logger.exception("manual weather refresh failed")
        cache = load_cache()
        if cache is not None:
            return {**cache, "refresh_error": str(exc)}
        raise HTTPException(502, f"Không lấy được thời tiết: {exc}") from exc
    return {**payload, "stale": False, "age_minutes": 0, "now": get_now()}
