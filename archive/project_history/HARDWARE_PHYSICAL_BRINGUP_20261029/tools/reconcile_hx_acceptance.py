"""Read ONLY archived HX files, preserve originals, record OWNER static acceptance.
Never visits the running flash-backup directory, imports serial or changes coefficients.
"""
from datetime import datetime
from decimal import Decimal
import json
import math
from pathlib import Path
import statistics
from image_layout import sha

KIT=Path(__file__).resolve().parents[1];ROOT=KIT.parent
ARCHIVE=ROOT/'HX711_REFERENCE_PORT_20261028/physical'
SESSIONS={5:'20261028T030939080655Z_observe_5g',10:'20261028T031409929796Z_observe_10g',
          20:'20261028T031718816708Z_observe_20g',35:'20261028T032243356311Z_observe_35g'}
FLAGS={'HX711_PHYSICAL_STATIC_TEST':'PASS','HX711_STATIC_MEASUREMENT_PHYSICAL_PASS':'YES',
       'HX711_35G_REFERENCE_MEASUREMENT':'PASS','HX711_MEASUREMENT_ACCURACY_ACCEPTED':'YES',
       'HX711_RETEST_REQUIRED':'NO','HX711_CALIBRATION_PERSISTENCE':'NOT_VERIFIED',
       'HX711_CLOSED_LOOP_DISPENSE_35G':'NOT_VERIFIED'}
def review_archive(folder,mass):
    summary=json.loads((folder/'summary.json').read_text(encoding='utf-8'))
    if summary.get('kind')!='HX711_REFERENCE_PHYSICAL_OBSERVATION' or summary.get('operator_mass_g')!=mass:raise ValueError('wrong original physical observation')
    checked={}
    for name,digest in summary['artifacts_sha256'].items():
        if Path(name).name!=name:raise ValueError('unsafe archive artifact name')
        if sha(folder/name)!=digest:raise ValueError('original evidence checksum mismatch '+name)
        checked[name]=digest
    samples=[]
    for line in (folder/'messages.jsonl').read_text(encoding='utf-8').splitlines():
        row=json.loads(line);m=row.get('message',{})
        if row.get('phase')=='WEIGHT_WINDOW' and m.get('valid') is True and 'calibration_source' not in m:
            samples.append(m)
    unique={m['monotonic_ms']:m['measurement_grams'] for m in samples}
    all_values=list(unique.values());stats=summary['weight_window']['measurement_grams']
    # Original physical_session.py freezes the30s summary BEFORE final_status(),
    # which appends extra same-phase tail records. Reconstruct that exact prefix;
    # retain/report tail count, never alter the raw source or select by error.
    values=all_values[:stats['count']]
    if len(values)!=stats['count'] or not math.isclose(statistics.mean(values),stats['mean'],abs_tol=1e-9) or min(values)!=stats['min'] or max(values)!=stats['max'] or values[0]!=stats['first'] or values[-1]!=stats['last']:raise ValueError('raw window and original summary disagree')
    return {'mass_g':mass,'scope':'EARLIER_REAL_HARDWARE_RAM_SESSION_NOT_LATEST_INOX_POINT',
        'directory':str(folder),'summary_sha256':sha(folder/'summary.json'),'original_artifacts_sha256':checked,
        'raw_sample_count':len(values),'post_summary_tail_samples_retained':len(all_values)-len(values),'signed_mean_g':statistics.mean(values),
        'historical_window_pass':summary['weight_window_pass'],
        'offset_counts':summary['initial_status']['offset'],
        'counts_per_g':summary['initial_status']['scale_factor_counts_per_gram'],
        'original_files_modified':False}
def main():
    records=[review_archive(ARCHIVE/name,mass) for mass,name in SESSIONS.items()]
    error=abs(Decimal('35')-Decimal('34.981'))
    result={'kind':'HX711_SCOPED_PHYSICAL_ACCEPTANCE','recorded_at':datetime.now().astimezone().isoformat(),
        'decision_authority':'OWNER_EXPLICIT_STATIC_ACCEPTANCE_CORRECTION_20261029',**FLAGS,
        'accepted_scope':['ESP32S3 HX711 DOUT4 SCK5 real communication','real loadcell1kg with inox bowl',
            'empty bowl tare','5/10/20/35g physical load response','35g static measurement and accepted accuracy'],
        'latest_owner_confirmed_physical_trial':{'reference_g':35,'measured_g':34.981,'absolute_error_g':float(error),
            'relative_error_percent':float(error/Decimal('35')*100),'empty_bowl_g':-.009,'added_delta_g':34.990,
            'return_approximately_g':-.077,'observed_30s_sample_count':109,'first_g':-.131398,'last_g':-.122004,
            'endpoint_difference_g':float(abs(Decimal('-.122004')-Decimal('-.131398'))),
            'endpoint_difference_is_full_range_or_sigma':False,'counts_per_g_recorded':-1064.4473,
            'historical_tare_offset_approximately':-698922.87,'coefficient_or_tare_changed_by_this_tool':False,
            'provenance':'OWNER_SUPPLIED_REAL_HARDWARE_RESULTS_AND_ACCEPTANCE',
            'matching_latest_raw_attachment_in_reviewed_local_archives':'NOT_LOCATED_NO_RETEST_REQUESTED',
            'traceability_followup':'Attach existing original latest log when available; do NOT repeat weights or optimize accuracy'},
        'earlier_original_physical_log_review':records,
        'not_granted':['current RAM calibration after reset','NVS persistence','servo closed-loop35g','actuator unlock','production integration pass'],
        'current_ram_calibration':'UNKNOWN_AFTER_RESETS','servo':'LOCKED','pump':'LOCKED',
        'accuracy_optimization_required':False,'weight_series_repeat_required':False,
        'integration_followup':'Check current calibration context/persistence separately after authorized firmware change; no full initial weight-series replay',
        'production_protocol_changed':False,'hardware_actions_performed':False,'active_backup_accessed':False}
    target=KIT/'HX711_ACCEPTANCE.json';target.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'archived_physical_sessions_verified':len(records),'archived_valid_samples':sum(r['raw_sample_count'] for r in records),
        **FLAGS,'latest_35g_exact_raw_file':'NOT_LOCATED_IN_REVIEWED_ARCHIVES_OWNER_ACCEPTANCE_RECORDED','hardware_actions_performed':False}))
if __name__=='__main__':main()
