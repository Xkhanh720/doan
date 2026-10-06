from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from zoneinfo import ZoneInfo

from ..db import get_conn, get_settings
from ..models import EventCreate, EventOut, EventUpdate
from ..scheduler import get_now

router = APIRouter(prefix="/api/events", tags=["events"])

VALID_DATE_FMT = "%Y-%m-%d"
VALID_TIME_FMT = "%H:%M"


def _validate_date(value: str, field: str) -> str:
    try:
        return datetime.strptime(value, VALID_DATE_FMT).date().isoformat()
    except ValueError:
        raise HTTPException(422, f"{field} phải có định dạng YYYY-MM-DD")


def _validate_time(value: Optional[str], field: str) -> Optional[str]:
    if value in (None, ""):
        return None
    try:
        return datetime.strptime(value, VALID_TIME_FMT).strftime("%H:%M")
    except ValueError:
        raise HTTPException(422, f"{field} phải có định dạng HH:MM (24h)")


def _today() -> str:
    tz_name = str(get_settings().get("timezone", "Asia/Ho_Chi_Minh"))
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = ZoneInfo("UTC")
    return datetime.now(tz).date().isoformat()


def _row_to_event(row) -> dict:
    return dict(row)


@router.get("", response_model=list[EventOut])
def list_events(
    date: Optional[str] = Query(
        default=None,
        description="YYYY-MM-DD, mặc định là hôm nay; dùng 'all' để lấy tất cả",
    ),
) -> list[dict]:
    with get_conn() as conn:
        if date == "all":
            rows = conn.execute(
                "SELECT * FROM events ORDER BY event_date, sort_order, id"
            ).fetchall()
        else:
            target = _validate_date(date, "date") if date else _today()
            rows = conn.execute(
                "SELECT * FROM events WHERE event_date = ? "
                "ORDER BY sort_order, id",
                (target,),
            ).fetchall()
    return [_row_to_event(r) for r in rows]


@router.post("", response_model=EventOut, status_code=201)
def create_event(body: EventCreate) -> dict:
    event_date = _validate_date(body.event_date or _today(), "event_date")
    start = _validate_time(body.start_time, "start_time")
    end = _validate_time(body.end_time, "end_time")
    if start and end and end < start:
        raise HTTPException(422, "end_time phải lớn hơn start_time")
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO events (title, description, event_date, start_time, "
            "end_time, sort_order) VALUES (?, ?, ?, ?, ?, ?)",
            (body.title.strip(), body.description, event_date, start, end, body.sort_order),
        )
        row = conn.execute(
            "SELECT * FROM events WHERE id = ?", (cur.lastrowid,)
        ).fetchone()
    return _row_to_event(row)


@router.get("/{event_id}", response_model=EventOut)
def get_event(event_id: int) -> dict:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM events WHERE id = ?", (event_id,)
        ).fetchone()
    if row is None:
        raise HTTPException(404, "Không tìm thấy sự kiện")
    return _row_to_event(row)


@router.put("/{event_id}", response_model=EventOut)
def update_event(event_id: int, body: EventUpdate) -> dict:
    with get_conn() as conn:
        existing = conn.execute(
            "SELECT * FROM events WHERE id = ?", (event_id,)
        ).fetchone()
        if existing is None:
            raise HTTPException(404, "Không tìm thấy sự kiện")

        fields = {k: v for k, v in body.model_dump(exclude_unset=True).items()}
        if "event_date" in fields:
            fields["event_date"] = _validate_date(fields["event_date"], "event_date")
        if "start_time" in fields:
            fields["start_time"] = _validate_time(fields["start_time"], "start_time")
        if "end_time" in fields:
            fields["end_time"] = _validate_time(fields["end_time"], "end_time")

        start = fields.get("start_time", existing["start_time"])
        end = fields.get("end_time", existing["end_time"])
        if start and end and end < start:
            raise HTTPException(422, "end_time phải lớn hơn start_time")

        if "title" in fields:
            fields["title"] = fields["title"].strip()
            if not fields["title"]:
                raise HTTPException(422, "title không được để trống")

        sets = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values()) + [event_id]
        conn.execute(
            f"UPDATE events SET {sets}, updated_at = datetime('now') WHERE id = ?",
            values,
        )
        row = conn.execute(
            "SELECT * FROM events WHERE id = ?", (event_id,)
        ).fetchone()
    return _row_to_event(row)


@router.delete("/{event_id}", status_code=204)
def delete_event(event_id: int) -> None:
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM events WHERE id = ?", (event_id,))
        if cur.rowcount == 0:
            raise HTTPException(404, "Không tìm thấy sự kiện")


@router.post("/purge")
def purge_events() -> dict:
    from ..scheduler import purge_old_events

    removed = purge_old_events()
    return {"removed": removed, "now": get_now()}
