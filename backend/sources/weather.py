import json
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from ..config import HTTP_TIMEOUT_SECONDS, WEATHER_API_URL
from ..db import get_conn, get_settings

WMO_CODES: dict[int, tuple[str, str]] = {
    0: ("Trời quang", "sun"),
    1: ("Ít mây", "sun"),
    2: ("Mây rải rác", "cloud-sun"),
    3: ("Nhiều mây", "cloud"),
    45: ("Sương mù", "fog"),
    48: ("Sương mù đóng băng", "fog"),
    51: ("Mưa phùn nhẹ", "drizzle"),
    53: ("Mưa phùn vừa", "drizzle"),
    55: ("Mưa phùn dày", "drizzle"),
    56: ("Mưa phùn đóng băng", "sleet"),
    57: ("Mưa phùn đóng băng dày", "sleet"),
    61: ("Mưa nhẹ", "rain"),
    63: ("Mưa vừa", "rain"),
    65: ("Mưa to", "rain"),
    66: ("Mưa đóng băng", "sleet"),
    67: ("Mưa đóng băng to", "sleet"),
    71: ("Tuyết nhẹ", "snow"),
    73: ("Tuyết vừa", "snow"),
    75: ("Tuyết to", "snow"),
    77: ("Hạt tuyết", "snow"),
    80: ("Mưa rào nhẹ", "rain"),
    81: ("Mưa rào", "rain"),
    82: ("Mưa rào mạnh", "rain"),
    85: ("Mưa tuyết nhẹ", "snow"),
    86: ("Mưa tuyết to", "snow"),
    95: ("Dông", "thunder"),
    96: ("Dông kèm mưa đá", "thunder"),
    99: ("Dông mạnh kèm mưa đá", "thunder"),
}


def describe_code(code: Optional[int]) -> tuple[str, str]:
    if code is None:
        return ("Không rõ", "cloud")
    return WMO_CODES.get(int(code), ("Không rõ", "cloud"))


def location_key(latitude: float, longitude: float) -> str:
    return f"{round(float(latitude), 4)}:{round(float(longitude), 4)}"


async def fetch_weather() -> dict[str, Any]:
    settings = get_settings()
    latitude = float(settings["latitude"])
    longitude = float(settings["longitude"])
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": (
            "temperature_2m,relative_humidity_2m,apparent_temperature,"
            "weather_code,wind_speed_10m,precipitation"
        ),
        "daily": (
            "weather_code,temperature_2m_max,temperature_2m_min,"
            "precipitation_probability_max"
        ),
        "timezone": "auto",
        "forecast_days": 1,
    }
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SECONDS) as client:
        resp = await client.get(WEATHER_API_URL, params=params)
        resp.raise_for_status()
        data = resp.json()

    current = data.get("current", {})
    daily = data.get("daily", {})
    current_text, current_icon = describe_code(current.get("weather_code"))
    daily_code = (daily.get("weather_code") or [None])[0]
    daily_text, daily_icon = describe_code(daily_code)

    payload = {
        "location": settings.get("location_name", ""),
        "latitude": data.get("latitude", latitude),
        "longitude": data.get("longitude", longitude),
        "timezone": data.get("timezone", settings.get("timezone")),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "current": {
            "temperature_2m": current.get("temperature_2m"),
            "relative_humidity_2m": current.get("relative_humidity_2m"),
            "apparent_temperature": current.get("apparent_temperature"),
            "weather_code": current.get("weather_code"),
            "weather_text": current_text,
            "weather_icon": current_icon,
            "wind_speed_10m": current.get("wind_speed_10m"),
            "precipitation": current.get("precipitation"),
            "time": current.get("time"),
        },
        "daily": {
            "temperature_2m_max": (daily.get("temperature_2m_max") or [None])[0],
            "temperature_2m_min": (daily.get("temperature_2m_min") or [None])[0],
            "weather_code": daily_code,
            "weather_text": daily_text,
            "weather_icon": daily_icon,
            "precipitation_probability_max": (
                daily.get("precipitation_probability_max") or [None]
            )[0],
        },
    }
    save_cache(payload, location_key(latitude, longitude))
    return payload


def save_cache(payload: dict[str, Any], loc_key: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO weather_cache (id, location_key, payload, fetched_at) "
            "VALUES (1, ?, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET location_key = excluded.location_key, "
            "payload = excluded.payload, fetched_at = excluded.fetched_at",
            (loc_key, json.dumps(payload, ensure_ascii=False), payload["fetched_at"]),
        )


def load_cache() -> Optional[dict[str, Any]]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT payload, location_key FROM weather_cache WHERE id = 1"
        ).fetchone()
    if row is None:
        return None
    try:
        payload = json.loads(row["payload"])
    except json.JSONDecodeError:
        return None

    settings = get_settings()
    current_key = location_key(settings["latitude"], settings["longitude"])
    age_minutes = _age_minutes(payload.get("fetched_at"))
    interval = int(settings.get("weather_interval_minutes", 10))
    payload["stale"] = age_minutes is None or age_minutes > interval * 2
    payload["age_minutes"] = age_minutes
    payload["location_mismatch"] = row["location_key"] != current_key
    return payload


def _age_minutes(fetched_at: Optional[str]) -> Optional[float]:
    if not fetched_at:
        return None
    try:
        fetched = datetime.fromisoformat(fetched_at)
    except ValueError:
        return None
    if fetched.tzinfo is None:
        fetched = fetched.replace(tzinfo=timezone.utc)
    delta = datetime.now(timezone.utc) - fetched
    return round(delta.total_seconds() / 60, 1)
