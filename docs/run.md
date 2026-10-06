# Pi Display Server — Backend

Server FastAPI: lấy thời tiết (Open-Meteo), giờ hiện tại, và danh sách
"sự kiện hôm nay" do admin nhập tay. Pi chỉ cần gọi `GET /api/display`.

## Cài đặt & chạy

```bash
cd pi-display-server
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# chạy (mọi thiết bị trong LAN truy cập được)
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

- API docs tương tác: `http://<ip-server>:8000/docs`
- SQLite tự tạo tại `data/pi_display.db` khi khởi động.
- Ảnh/video tải lên (nếu dùng sau này) lưu trong `uploads/` → serve qua `/static/`.

## Cấu hình

Đổi trực tiếp qua API (không cần sửa code):

```bash
# ví dụ: đổi địa điểm sang Đà Nẵng
curl -X PUT http://localhost:8000/api/settings \
  -H 'Content-Type: application/json' \
  -d '{"latitude": 16.0544, "longitude": 108.2022, "location_name": "Đà Nẵng"}'
```

| Key | Mặc định | Ý nghĩa |
|---|---|---|
| `latitude` / `longitude` | 21.0285 / 105.8542 | Tọa độ thời tiết (Hà Nội) |
| `location_name` | Hà Nội | Tên hiển thị |
| `timezone` | Asia/Ho_Chi_Minh | Múi giờ tính "hôm nay" |
| `weather_interval_minutes` | 10 | Chu kỳ tự refresh thời tiết |
| `purge_events_after_days` | 30 | Tự xóa sự kiện cũ hơn N ngày |
| `display_title` | Bảng thông tin | Tiêu đề màn hình |
| `poll_hint_seconds` | 30 | Gợi ý Pi poll lại sau bao nhiêu giây |

## API

### Cho Pi (gọi 1 lệnh là đủ)

```bash
curl http://localhost:8000/api/display
```

```json
{
  "title": "Bảng thông tin",
  "now": {"iso": "...", "date": "2026-10-05", "time": "09:30:12",
           "weekday": "Thứ Hai", "timestamp": 1770000000},
  "weather": {
    "location": "Hà Nội",
    "current": {"temperature_2m": 28.4, "weather_text": "Mây rải rác",
                 "weather_icon": "cloud-sun", "relative_humidity_2m": 70, ...},
    "daily": {"temperature_2m_max": 33.0, "temperature_2m_min": 24.0, ...},
    "stale": false, "age_minutes": 2.5, "fetched_at": "..."
  },
  "events": [ {"id": 1, "title": "...", "event_date": "2026-10-05",
                "start_time": "08:00", "end_time": "10:00", ...} ],
  "poll_hint_seconds": 30
}
```

- `weather.stale = true` → dữ liệu cũ (mất mạng API), vẫn hiển thị được.
- `weather = null` → chưa từng fetch được; gọi `POST /api/weather/refresh`.
- `events` chỉ trả sự kiện **hôm nay** (theo `timezone` cấu hình).

### Thời tiết

```bash
curl http://localhost:8000/api/weather              # cache gần nhất
curl http://localhost:8000/api/weather?refresh=true # ép fetch ngay
curl -X POST http://localhost:8000/api/weather/refresh
```

### Sự kiện hôm nay

```bash
# hôm nay (mặc định)
curl http://localhost:8000/api/events

# ngày khác / tất cả
curl "http://localhost:8000/api/events?date=2026-10-06"
curl "http://localhost:8000/api/events?date=all"

# thêm
curl -X POST http://localhost:8000/api/events \
  -H 'Content-Type: application/json' \
  -d '{"title": "Họp lớp", "description": "Tầng 2",
       "event_date": "2026-10-05", "start_time": "14:00", "end_time": "15:30"}'

# sửa / xóa
curl -X PUT http://localhost:8000/api/events/1 \
  -H 'Content-Type: application/json' -d '{"title": "Họp lớp (đổi lịch)"}'
curl -X DELETE http://localhost:8000/api/events/1
```

Định dạng: `event_date = YYYY-MM-DD`, `start_time/end_time = HH:MM` (24h).
Để trống `event_date` khi POST → tự gán hôm nay.

### Khác

```bash
curl http://localhost:8000/api/time     # giờ hiện tại theo timezone cấu hình
curl http://localhost:8000/api/settings # đọc cấu hình
curl http://localhost:8000/api/health   # kiểm tra sống
```

## Hành vi nền

- Task `weather_loop`: fetch thời tiết mỗi `weather_interval_minutes`, lỗi mạng
  thì giữ cache cũ (không crash).
- Task `maintenance_loop`: mỗi ngày xóa sự kiện đã cũ hơn
  `purge_events_after_days`.
