import asyncio
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from .db import get_conn, get_settings
from .sources.weather import fetch_weather

logger = logging.getLogger("pi_display.scheduler")


async def weather_loop() -> None:
    while True:
        interval = int(get_settings().get("weather_interval_minutes", 10))
        try:
            payload = await fetch_weather()
            logger.info(
                "weather refreshed: %.1f°C %s",
                payload["current"].get("temperature_2m") or 0,
                payload["current"].get("weather_text"),
            )
        except Exception:
            logger.exception("weather fetch failed, keeping cached data")
        await asyncio.sleep(max(interval, 1) * 60)


def purge_old_events() -> int:
    days = int(get_settings().get("purge_events_after_days", 30))
    tz = _get_timezone()
    cutoff = (datetime.now(tz) - timedelta(days=days)).date().isoformat()
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM events WHERE event_date < ?", (cutoff,))
        return cur.rowcount


def _get_timezone() -> ZoneInfo:
    name = str(get_settings().get("timezone", "Asia/Ho_Chi_Minh"))
    try:
        return ZoneInfo(name)
    except Exception:
        logger.warning("invalid timezone %r, falling back to UTC", name)
        return ZoneInfo("UTC")


def _last_purge_day() -> str:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT value FROM settings WHERE key = '_last_purge'"
        ).fetchone()
    return row["value"] if row else ""


def daily_purge_if_needed() -> None:
    tz = _get_timezone()
    today = datetime.now(tz).date().isoformat()
    if _last_purge_day() == today:
        return
    removed = purge_old_events()
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO settings (key, value) VALUES ('_last_purge', ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (today,),
        )
    if removed:
        logger.info("purged %d expired events", removed)


async def maintenance_loop() -> None:
    while True:
        try:
            daily_purge_if_needed()
        except Exception:
            logger.exception("purge failed")
        await asyncio.sleep(3600)


def get_now() -> dict:
    tz = _get_timezone()
    now = datetime.now(tz)
    weekdays = [
        "Thứ Hai",
        "Thứ Ba",
        "Thứ Tư",
        "Thứ Năm",
        "Thứ Sáu",
        "Thứ Bảy",
        "Chủ Nhật",
    ]
    return {
        "iso": now.isoformat(),
        "date": now.date().isoformat(),
        "time": now.strftime("%H:%M:%S"),
        "weekday": weekdays[now.weekday()],
        "timestamp": now.timestamp(),
    }
