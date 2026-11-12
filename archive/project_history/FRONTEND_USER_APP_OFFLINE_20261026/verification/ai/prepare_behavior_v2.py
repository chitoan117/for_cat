from pathlib import Path
import shutil
import random
import hashlib

RAW = Path(r"D:\for_cat\ai\datasets\behavior_raw")
OUT = Path(r"D:\for_cat\ai\datasets\behavior_prepared_v2")

# Final classes:
# 0 = EATING
# 1 = DRINKING
# 2 = OTHER

MAPPINGS = {
    "behavior_01": {
        7: 1,   # drinking
        8: 0,   # eating
        9: 2,
        10: 2,
        11: 2,
        12: 2,
        13: 2,
        # IDs 0-6 intentionally ignored
    },

    "behavior_02": {
        0: 0,   # eating
        1: 2,   # sitting
        2: 2,   # sleeping
        3: 2,   # standing
    },

    "behavior_03": {
        0: 0,   # eating
        1: 2,   # play
        2: 2,   # sitting
        3: 2,   # sleep
        4: 2,   # walk-run
    },

    "behavior_04": {
        0: 1,   # Cat Drinking
        1: 0,   # Cat eating
        2: 2,   # Cat happy
        3: 2,   # Cat vs cat
        4: 2,   # Cat vs dog
        5: 2,   # Cat vs human
        6: 2,   # Cat vs object
    },
}

if OUT.exists():
    shutil.rmtree(OUT)

rng = random.Random(42)
records = []
seen_hashes = set()

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

for dataset_name, mapping in MAPPINGS.items():

    ds_root = RAW / dataset_name

    for split in ("train", "valid", "test"):

        image_dir = ds_root / split / "images"
        label_dir = ds_root / split / "labels"

        if not image_dir.exists() or not label_dir.exists():
            continue

        for image_path in sorted(image_dir.iterdir()):

            if image_path.suffix.lower() not in IMAGE_EXTS:
                continue

            label_path = label_dir / (image_path.stem + ".txt")

            if not label_path.exists():
                continue

            converted = []

            for line in label_path.read_text(
                encoding="utf-8",
                errors="ignore"
            ).splitlines():

                parts = line.strip().split()

                if len(parts) < 5:
                    continue

                try:
                    old_id = int(float(parts[0]))
                except ValueError:
                    continue

                if old_id not in mapping:
                    continue

                new_id = mapping[old_id]

                converted.append(
                    str(new_id) + " " + " ".join(parts[1:])
                )

            if not converted:
                continue

            # Remove exact duplicate images
            digest = hashlib.sha256(
                image_path.read_bytes()
            ).hexdigest()

            if digest in seen_hashes:
                continue

            seen_hashes.add(digest)

            classes = {int(x.split()[0]) for x in converted}

            # Image category used only for stratified splitting/sampling
            if 1 in classes:
                category = 1       # DRINKING priority
            elif 0 in classes:
                category = 0       # EATING
            else:
                category = 2       # OTHER

            records.append({
                "dataset": dataset_name,
                "image": image_path,
                "lines": converted,
                "category": category,
            })

groups = {
    0: [],
    1: [],
    2: [],
}

for record in records:
    groups[record["category"]].append(record)

for group in groups.values():
    rng.shuffle(group)

print("===== BEFORE BALANCING =====")
print("EATING images   :", len(groups[0]))
print("DRINKING images :", len(groups[1]))
print("OTHER images    :", len(groups[2]))

# Keep every EATING and DRINKING sample.
# Limit OTHER so it does not dominate training.
max_other = len(groups[0]) + len(groups[1])

if len(groups[2]) > max_other:
    groups[2] = groups[2][:max_other]

print()
print("===== AFTER BALANCING =====")
print("EATING images   :", len(groups[0]))
print("DRINKING images :", len(groups[1]))
print("OTHER images    :", len(groups[2]))

splits = {
    "train": [],
    "valid": [],
    "test": [],
}

# 80 / 10 / 10 per category
for category, items in groups.items():

    rng.shuffle(items)

    n = len(items)

    n_test = round(n * 0.10)
    n_valid = round(n * 0.10)

    if n >= 10:
        n_test = max(1, n_test)
        n_valid = max(1, n_valid)

    splits["test"].extend(items[:n_test])
    splits["valid"].extend(
        items[n_test:n_test + n_valid]
    )
    splits["train"].extend(
        items[n_test + n_valid:]
    )

for split_name, items in splits.items():

    rng.shuffle(items)

    image_out = OUT / split_name / "images"
    label_out = OUT / split_name / "labels"

    image_out.mkdir(parents=True, exist_ok=True)
    label_out.mkdir(parents=True, exist_ok=True)

    for index, record in enumerate(items):

        source = record["image"]

        new_stem = (
            f"{record['dataset']}_{index:06d}_{source.stem}"
        )

        destination_image = (
            image_out /
            (new_stem + source.suffix.lower())
        )

        destination_label = (
            label_out /
            (new_stem + ".txt")
        )

        shutil.copy2(source, destination_image)

        destination_label.write_text(
            "\n".join(record["lines"]) + "\n",
            encoding="utf-8",
        )

yaml = """path: D:/for_cat/ai/datasets/behavior_prepared_v2
train: train/images
val: valid/images
test: test/images

nc: 3
names:
  0: EATING
  1: DRINKING
  2: OTHER
"""

(OUT / "data.yaml").write_text(
    yaml,
    encoding="utf-8"
)

print()
print("===== FINAL DATASET =====")

for split_name in ("train", "valid", "test"):

    image_dir = OUT / split_name / "images"
    label_dir = OUT / split_name / "labels"

    images = list(image_dir.glob("*"))
    labels = list(label_dir.glob("*.txt"))

    counts = {
        0: 0,
        1: 0,
        2: 0,
    }

    for label in labels:

        for line in label.read_text(
            encoding="utf-8"
        ).splitlines():

            if not line.strip():
                continue

            class_id = int(line.split()[0])
            counts[class_id] += 1

    print(split_name.upper())
    print("  images   :", len(images))
    print("  labels   :", len(labels))
    print("  EATING   :", counts[0])
    print("  DRINKING :", counts[1])
    print("  OTHER    :", counts[2])

print()
print("OUTPUT:", OUT)
