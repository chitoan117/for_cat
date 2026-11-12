"""Dependency-free label contracts; importable by the Nano's Python 3.6 tools.

Legacy identity/behavior labels are unchanged. Version 2 is single-cat offline
metadata, not an identity model and not actuator authorization.
"""
IDENTITY = ("OWNER_CAT", "OTHER_CAT", "OTHER_OBJECT", "UNKNOWN", "SKIP")
BEHAVIOR = ("EATING", "DRINKING", "NEAR_FOOD", "NEAR_WATER", "LEAVING", "OTHER", "UNSURE", "SKIP")
BEHAVIOR_V2 = ("EATING", "DRINKING", "IDLE")
SUBJECT_V2 = ("CAT", "NONE", "UNKNOWN", "UNSURE", "SKIP")
V2_REVIEW = ("NONE", "UNKNOWN", "UNSURE", "SKIP")
PREFERENCE_FIELDS = ("preference_trial_id", "food_variant", "trial_order", "food_bowl_position", "session_pair_or_group")


def preference_error(metadata):
    for name in PREFERENCE_FIELDS:
        value = metadata.get(name)
        if value is None:
            continue
        if name == "trial_order":
            if type(value) is not int or not 0 <= value <= 100000:
                return "invalid trial_order"
        elif not isinstance(value, str) or not value or len(value) > 128:
            return "invalid " + name
    position = metadata.get("food_bowl_position", "RED_FOOD_ROI")
    if isinstance(position, str) and ("BLUE" in position.upper() or "WATER" in position.upper()):
        return "normal Behavior V2 keeps RED=FOOD and BLUE=WATER; separate layouts need a future experimental mode"
    return None


def label_field(task):
    return "behavior_label" if task == "behavior_v2" else task + "_label"


def task_label(row, task):
    version = row.get("schema_version", 1)
    if task == "behavior_v2":
        return row.get("behavior_label") if version == 2 and row.get("subject_label") == "CAT" else None
    return row.get(label_field(task)) if version == 1 else None


def v2_pair_error(subject, behavior, usable):
    if subject not in SUBJECT_V2 + (None,):
        return "invalid subject_label"
    if behavior not in BEHAVIOR_V2 + V2_REVIEW + (None,):
        return "invalid behavior_label v2"
    if subject == "NONE" and behavior != "NONE":
        return "NONE subject requires NONE behavior, never IDLE"
    if subject == "CAT" and behavior == "NONE":
        return "CAT subject cannot have NONE behavior"
    if behavior == "NONE" and subject != "NONE":
        return "NONE behavior requires NONE subject"
    if subject != "CAT" and behavior in BEHAVIOR_V2:
        return "uncertain subject cannot have a confirmed behavior"
    if usable and not (subject == "CAT" and behavior in BEHAVIOR_V2):
        return "only confirmed CAT EATING/DRINKING/IDLE is usable for behavior v2"
    return None
