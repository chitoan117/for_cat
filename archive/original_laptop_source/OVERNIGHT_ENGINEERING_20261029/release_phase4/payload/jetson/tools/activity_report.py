"""Read supplied local records; never start a camera/model or actuate."""
import argparse
import json
from datetime import date
from pathlib import Path
from app.analytics.reports import FoodDefinition,FoodTrial,activity_report,preference_report
from app.storage.records import BehaviorRecord,DrinkingSession,FeedingSession


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("kind",choices=("preference","daily")); p.add_argument("--input",type=Path,required=True)
    p.add_argument("--date",type=date.fromisoformat); a=p.parse_args()
    try:
        if a.input.stat().st_size>5_000_000: raise ValueError("report input budget exceeded")
        data=json.loads(a.input.read_text(encoding="utf-8"))
        if a.kind=="preference": result=preference_report(FoodDefinition.model_validate(data["food"]),[FoodTrial.model_validate(x) for x in data["trials"]])
        else:
            if a.date is None: raise ValueError("explicit --date required")
            result=activity_report(a.date,eating=[BehaviorRecord.model_validate(x) for x in data.get("eating",[])],drinking=[DrinkingSession.model_validate(x) for x in data.get("drinking",[])],feeding=[FeedingSession.model_validate(x) for x in data.get("feeding",[])],recognition=data.get("recognition",[]),downtime_seconds=data.get("downtime_seconds"))
        print(json.dumps(result,indent=2,allow_nan=False))
    except (ValueError,OSError,KeyError,TypeError) as exc: p.exit(2,f"REPORT_FAILED: {exc}\n")


if __name__=="__main__": main()
