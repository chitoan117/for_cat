# Food and activity reports

`app/analytics/reports.py` is read-only and accepts supplied typed records; `tools.activity_report` never opens camera/serial or actuates. It does not change the existing frontend/API contract or migrate the database.

FoodDefinition: food_id/display_name/optional batch_variant/notes. FoodTrial: existing FeedingSession plus subject track, CLEAN/AMBIGUOUS attribution and confounders (time since last feed, portion size, time of day, freshness, bowl position, environmental disturbance). These are recorded facts, not hunger estimates.

Preference report heading is **BEHAVIORAL PREFERENCE TREND**. It excludes ambiguous/non-owner/unvalidated-weight/incomplete/duplicate sessions and reports valid sample count, consumption ratio, approach latency, eating duration, leftover, repeat visits, missing-data reasons and confounders. Confidence stays null: no statistical certainty is invented. Existing weighted trend is experimental; its min-session/weight choices are configurable heuristics, not biological proof.

Drinking report: event count/start times/durations/daily frequency and source counts. Water volume remains null. Daily activity: eating/drinking sessions, validated food estimates without double-counting associated feeding/visit estimates, feeding requests/results, supplied recognition summary, unknown/ambiguous events, and measured downtime or null. No health diagnosis.

From `jetson/`:

```text
python -m tools.activity_report preference --input SUPPLIED_FOOD_TRIALS.json
python -m tools.activity_report daily --input SUPPLIED_ACTIVITY_RECORDS.json --date YYYY-MM-DD
```

Preference input contains food/trials; daily input contains optional eating/drinking/feeding/recognition/downtime_seconds. VALIDATED_SENSOR is caller-supplied provenance requiring independent review, not a certification granted by the reporting tool. Missing values stay unknown. No real behavioral trend or water consumption result exists yet.
