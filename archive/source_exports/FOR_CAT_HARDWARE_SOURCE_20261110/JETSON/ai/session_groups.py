"""Must-link source aliases and optional experiment pairs; no frame-level split."""


def source_groups(rows):
    parents = {row["session_id"]: row["session_id"] for row in rows}

    def find(value):
        while parents[value] != value:
            parents[value] = parents[parents[value]]
            value = parents[value]
        return value

    keys = {}
    for row in rows:
        identifier = row["session_id"]
        values = [("source", row["source_hash"])]
        if row.get("session_pair_or_group"):
            values.append(("experiment_group", row["session_pair_or_group"]))
        for key in values:
            if key in keys:
                left, right = find(identifier), find(keys[key])
                parents[max(left, right)] = min(left, right)
            else:
                keys[key] = identifier
    result = {}
    for identifier in sorted(parents):
        result.setdefault(find(identifier), []).append(identifier)
    return result
