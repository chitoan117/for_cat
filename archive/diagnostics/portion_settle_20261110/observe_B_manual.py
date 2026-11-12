from pathlib import Path
import json,runpy,urllib.request
from label_manual_trials import mark
r=Path(__file__).parent
with urllib.request.urlopen('http://127.0.0.1:8000/api/meal-observation',timeout=2) as f:live=json.load(f)['live']
assert live['meal_id']=='meal_947ad5ff28780bb3' and live['meal_food']=='FOOD_B',live
namespace=runpy.run_path(str(r/'observe_meal.py'),run_name='__main__')
result=namespace['result']
if result.get('outcome')=='FINAL_MEASURED_RECORD_SAVED':
    note=mark(result['meal_id'])
    (r/'B_manual_annotation.json').write_text(json.dumps(note,indent=2))
    print(json.dumps({'manual_annotation':note},indent=2),flush=True)
