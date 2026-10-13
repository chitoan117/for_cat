# Daily behavior report contract for future Web/App

The existing frontend remains a separate project. Today the versioned backend offers `GET /api/v1/daily-summary?day=YYYY-MM-DD` in UTC, `GET /api/v1/behavior` (recent generic behavior events), `GET /api/v1/sessions/feeding`, `/sessions/drinking`, and `GET /api/v1/preferences`. No new frontend is created.

**Current `/daily-summary` JSON fields and types (empty database example, not a recorded observation):**

```json
{
  "date": "YYYY-MM-DD",
  "feeding_sessions": 0,
  "feeding_requests": 0,
  "drinking_sessions": 0,
  "session_details_truncated": false,
  "eating_times": [],
  "eating_visits": [],
  "drinking_times": [],
  "eating_duration_seconds": [],
  "drinking_duration_seconds": [],
  "reliable_food_consumed_grams": null,
  "strongest_observed_preference_trend": null,
  "preference_status": "INSUFFICIENT_DATA"
}
```

`feeding_sessions` counts SUCCESS records, while `feeding_requests` counts attempts; `drinking_sessions` counts typed drinking visits. Eating/drinking times are UTC ISO-8601 strings; durations are seconds. `eating_visits` entries contain `identity`, `started_at`, `duration_seconds` (null if unknown). Recent behavior is **not embedded** in this endpoint: the future client should read `/api/v1/behavior` separately (an empty list until observations exist) and correlate by UTC timestamp/session ID. Preference evidence comes from `/api/v1/preferences`, not a certainty label. Missing weight evidence must be `null`, not zero. If detail windows exceed 1,000, `session_details_truncated=true`, potentially incomplete totals become null, and the client should not display partial lists as complete history.
