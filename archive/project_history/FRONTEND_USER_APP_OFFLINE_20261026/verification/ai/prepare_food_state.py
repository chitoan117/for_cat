from pathlib import Path
import shutil
import random
import hashlib

SRC = Path(r"D:\for_cat\ai\datasets\behavior_raw\catfood_dataset")
OUT = Path(r"D:\for_cat\ai\datasets\food_state_prepared")

# Old → new
MAPPING = {
    1: 0,  # empty-bowl -> EMPTY_BOWL
    3: 1,  # food_full  -> FOOD_FULL
}

if OUT.exists():
    shutil.rmtree(OUT)

records = []
seen = set()

for split in ("train", "valid", "test"):

    image_dir = SRC / split / "images"
    label_dir = SRC / split / "labels"

    if not image_dir.exists() or not label_dir.exists():
        continue

    for image_path in sorted(image_dir.iterdir()):

        if image_path.suffix.lower() not in {
            ".jpg", ".jpeg", ".png", ".bmp", ".webp"
        }:
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

            if old_id not in MAPPING:
                continue

            new_id = MAPPING[old_id]

            converted.append(
                str(new_id) + " " + " ".join(parts[1:])
            )

        if not converted:
            continue

        digest = hashlib.sha256(
            image_path.read_bytes()
        ).hexdigest()

        if digest in seen:
            continue

        seen.add(digest)

        classes = {int(x.split()[0]) for x in converted}

        # Audit already showed no image should contain both
        if 0 in classes and 1 in classes:
            print("WARNING BOTH:", image_path)
            continue

        category = 0 if 0 in classes else 1

        records.append({
            "image": image_path,
            "labels": converted,
            "category": category,
        })

rng = random.Random(42)

groups = {
    0: [],
    1: [],
}

for record in records:
    groups[record["category"]].append(record)

for group in groups.values():
    rng.shuffle(group)

print("===== AFTER CLEANING =====")
print("EMPTY_BOWL images:", len(groups[0]))
print("FOOD_FULL images :", len(groups[1]))
print("TOTAL            :", len(records))

splits = {
    "train": [],
    "valid": [],
    "test": [],
}

for category, items in groups.items():

    n = len(items)

    n_valid = round(n * 0.10)
    n_test = round(n * 0.10)

    splits["valid"].extend(items[:n_valid])
    splits["test"].extend(items[n_valid:n_valid + n_test])
    splits["train"].extend(items[n_valid + n_test:])

for split_name, items in splits.items():

    rng.shuffle(items)

    img_out = OUT / split_name / "images"
    lbl_out = OUT / split_name / "labels"

    img_out.mkdir(parents=True, exist_ok=True)
    lbl_out.mkdir(parents=True, exist_ok=True)

    counts = {
        0: 0,
        1: 0,
    }

    for i, record in enumerate(items):

        src = record["image"]

        stem = f"food_{i:05d}_{src.stem}"

        shutil.copy2(
            src,
            img_out / (stem + src.suffix.lower())
        )

        (lbl_out / (stem + ".txt")).write_text(
            "\n".join(record["labels"]) + "\n",
            encoding="utf-8"
        )

        for line in record["labels"]:
            counts[int(line.split()[0])] += 1

    print()
    print(split_name.upper())
    print("  images      :", len(items))
    print("  EMPTY_BOWL  :", counts[0])
    print("  FOOD_FULL   :", counts[1])

yaml = """path: D:/for_cat/ai/datasets/food_state_prepared
train: train/images
val: valid/images
test: test/images

nc: 2
names:
  0: EMPTY_BOWL
  1: FOOD_FULL
"""

(OUT / "data.yaml").write_text(
    yaml,
    encoding="utf-8"
)

print()
print("OUTPUT:", OUT)
