"""Offline public-data provenance gate. Never downloads/imports/labels owner data."""
from datetime import datetime
from urllib.parse import urlparse


def validate_provenance(record):
    if not isinstance(record,dict): return {"status":"REJECTED","errors":["provenance must be an object"]}
    required=("dataset_id","publisher","version","source_url","license_name","license_url","accessed_at","source_grouping")
    errors=["missing "+name for name in required if not isinstance(record.get(name),str) or not record[name].strip() or len(record[name])>512]
    if record.get("schema_version")!=1: errors.append("unsupported provenance schema")
    for key in ("source_url","license_url"):
        if isinstance(record.get(key),str):
            url=urlparse(record[key])
            if url.scheme not in ("http","https") or not url.netloc or url.username or url.password: errors.append("invalid "+key)
    try:
        timestamp=datetime.fromisoformat(record.get("accessed_at",""))
        if timestamp.tzinfo is None: errors.append("accessed_at requires timezone")
    except (ValueError,TypeError): errors.append("invalid accessed_at")
    if record.get("license_reviewed") is not True: errors.append("license/provenance review incomplete")
    if record.get("use_for_final_test") is not False: errors.append("public data cannot stand in for owner-camera final test")
    mapping=record.get("label_mapping",{})
    if not isinstance(mapping,dict) or any(not isinstance(value,str) or value not in ("CAT","OTHER_CAT","OTHER_OBJECT","EATING","DRINKING","OTHER","UNKNOWN","UNSURE","SKIP") for value in mapping.values()):
        errors.append("invalid mapping/public OWNER_CAT forbidden")
    return {"status":"REJECTED" if errors else "BOOTSTRAP_PROVENANCE_RECORDED_REQUIRES_SAMPLE_VALIDATION",
            "errors":errors,"downloaded":False,"owner_domain_validated":False,"production_accuracy_claim_allowed":False}
