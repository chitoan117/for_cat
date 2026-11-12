# API tham khảo — xuất từ Jetson ngày08/11/2026

Hợp đồng chi tiết nằm trong `openapi.json`. Swagger ở `/docs` khi backend chạy.

| HTTP | Endpoint | Mô tả từ source |
|---|---|---|
| GET | `/api/v1/health` | Health |
| GET | `/api/v1/status` | Status |
| GET | `/api/v1/readiness` | Readiness |
| GET | `/api/v1/events` | Events |
| POST | `/api/v1/feed/manual` | Feed Manual |
| GET | `/api/v1/feed/manual/{request_id}` | Feed Result |
| GET | `/api/v1/behavior` | Behavior |
| GET | `/api/v1/feeding-history` | Feeding History |
| GET | `/api/v1/drinking-history` | Drinking History |
| GET | `/api/v1/sessions/feeding` | Feeding Sessions |
| GET | `/api/v1/sessions/drinking` | Drinking Sessions |
| GET | `/api/v1/preferences` | Preferences |
| GET | `/api/v1/food-types` | Food Types |
| GET | `/api/v1/daily-summary` | Summary |
| GET | `/api/v1/esp32/status` | Esp32 Status |
| GET | `/api/v1/esp32/events` | Esp32 Events |
| POST | `/api/feed/preview` | Manual Preview |
| GET | `/api/feed/preview/{request_id}` | Preview Result |
| GET | `/api/status` | System Status |
| GET | `/api/meal-plans` | List Plans |
| POST | `/api/meal-plans` | Create Plan |
| GET | `/api/meal-plans/worker` | Worker Status |
| PUT | `/api/meal-plans/{plan_id}` | Update Plan |
| DELETE | `/api/meal-plans/{plan_id}` | Delete Plan |
| POST | `/api/meal-plans/{plan_id}/preview` | Preview |
| GET | `/api/hx711/status` | Status |
| GET | `/api/hx711/calibration` | Calibration |

## Luồng trạng thái và giao diện

- WebSocket `/api/ws/state`: truyền trạng thái hệ thống; không nằm trong OpenAPI REST.
- `/app`, `/kiosk`: giao diện Flutter cùng backend.
- `/flutter/`: tài nguyên static đã build.

Hai nhóm endpoint `/api/v1/...` và `/api/...` cùng tồn tại. Đối chiếu `frontend/lib/real_backend.dart` và `meal_plans.dart` để biết endpoint frontend gọi thực tế. Tên `preview`/`DRY_RUN` là tên hợp đồng cũ; bridge Jetson có thể tiêu thụ yêu cầu để điều khiển phần cứng thực.
