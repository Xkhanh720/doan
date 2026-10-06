import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = Path(os.environ.get("PI_DISPLAY_DB", BASE_DIR / "data" / "pi_display.db"))
UPLOAD_DIR = BASE_DIR / "uploads"

DEFAULT_SETTINGS = {
    "latitude": 21.0285,
    "longitude": 105.8542,
    "location_name": "Hà Nội",
    "timezone": "Asia/Ho_Chi_Minh",
    "weather_interval_minutes": 10,
    "purge_events_after_days": 30,
    "display_title": "Bảng thông tin",
    "poll_hint_seconds": 30,
}

WEATHER_API_URL = "https://api.open-meteo.com/v1/forecast"
HTTP_TIMEOUT_SECONDS = 10.0
