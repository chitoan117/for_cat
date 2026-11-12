import json,sys
from datetime import datetime,timezone,timedelta
from pathlib import Path
ROOT=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT/'candidate/backend'))
from app.analytics.preference import trend,PreferencePolicy
from app.storage.records import FeedingSession
from app.ai.models import Identity
now=datetime(2026,10,30,tzinfo=timezone.utc)
rows=[FeedingSession(session_id='SYN_'+str(n),food_type='SYNTHETIC_FOOD',cat_identity=Identity.OWNER_CAT,
    requested_at=now,source='SYNTHETIC_TEST_DATA',result='ERROR',dispensed_grams=35,estimated_consumed_grams=30,
    approach_delay_seconds=1,repeat_visits=1,eating_started_at=now,eating_finished_at=now+timedelta(seconds=1)) for n in range(3)]
value=trend('SYNTHETIC_FOOD',rows,PreferencePolicy(allow_synthetic_test_data=True))
label=sys.argv[1];path=ROOT/'evidence'/(label+'_preference.json')
with path.open('x') as f:json.dump({'source':'SIMULATED','result':value},f,indent=2)
print(json.dumps(value,indent=2))
