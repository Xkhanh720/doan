from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class EventBase(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    description: str = ""
    event_date: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    sort_order: int = 0


class EventCreate(EventBase):
    pass


class EventUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=300)
    description: Optional[str] = None
    event_date: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    sort_order: Optional[int] = None


class EventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    event_date: str
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    sort_order: int
    created_at: str
    updated_at: str


class SettingsUpdate(BaseModel):
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)
    location_name: Optional[str] = None
    timezone: Optional[str] = None
    weather_interval_minutes: Optional[int] = Field(default=None, ge=1, le=1440)
    purge_events_after_days: Optional[int] = Field(default=None, ge=1, le=3650)
    display_title: Optional[str] = None
    poll_hint_seconds: Optional[int] = Field(default=None, ge=5, le=3600)


class NowInfo(BaseModel):
    iso: str
    date: str
    time: str
    weekday: str
    timestamp: float


class DisplayResponse(BaseModel):
    title: str
    now: NowInfo
    weather: Optional[dict[str, Any]] = None
    events: list[dict[str, Any]]
    poll_hint_seconds: int
