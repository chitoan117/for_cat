from pathlib import Path
import shutil
import random
import hashlib

RAW = Path(r"D:\for_cat\ai\datasets\behavior_raw")
OUT = Path(r"D:\for_cat\ai\datasets\behavior_prepared")

if OUT.exists():
    shutil.rmtree(OUT)

# class cuối:
# 0 = EATING
# 1 = DRINKING
# 2 = OTHER

MAPPINGS = {
    "behavior_01": {
        7: 1,   # cat_drinking
        8: 0,   # cat_eating
        9: 2,   # fighting
        10: 2,  # laying
        11: 2,  # playing
        12: 2,  # sitting
        13: 2,  # scratching
        # 0-6 cố ý bỏ vì semantic không xác định
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
    }
}

records = []
seen_hashes = set()

exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

for ds_name, mapping in MAPPINGS.items():

    ds_root = RAW / ds_name

    for split in ("train", "valid", "test"):

        img_dir = ds_root / split / "images"
        lbl_dir = ds_root / split / "labels"

        if not img_dir.exists() or not lbl_dir.exists():
            continue

        for img in sorted(img_dir.iterdir()):

            if img.suffix.lower() not in exts:
                continue

            lbl = lbl_dir / (img.stem + ".txt")

            if not lbl.exists():
                continue

            new_lines = []

            for line in lbl.read_text(
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

                new_lines.append(
                    str(new_id) + " " + " ".join(parts[1:])
                )

            # nếu ảnh không còn annotation hợp lệ thì bỏ
            if not new_lines:
                continue

            digest = hashlib.sha256(img.read_bytes()).hexdigest()

            # loại ảnh trùng hoàn toàn
            if digest in seen_hashes:
                continue

            seen_hashes.add(digest)

            classes = {int(x.split()[0]) for x in new_lines}

            # ưu tiên class hiếm nhất để chia stratified
            if 1 in classes:
                category = 1       # DRINKING
            elif 0 in classes:
                category = 0       # EATING
            else:
                category = 2       # OTHER

            records.append({
                "dataset": ds_name,
                "image": img,
                "lines": new_lines,
                "category": category,
            })


rng = random.Random(42)

groups = {0: [], 1: [], 2: []}

for r in records:
    groups[r["category"]].append(r)

for values in groups.values():
    rng.shuffle(values)


splits = {
    "train": [],
    "valid": [],
    "test": [],
}

for category, items in groups.items():

    n = len(items)

    n_test = round(n * 0.10)
    n_val = round(n * 0.10)

    if n >= 10:
        n_test = max(1, n_test)
        n_val = max(1, n_val)

    splits["test"].extend(items[:n_test])
    splits["valid"].extend(items[n_test:n_test+n_val])
    splits["train"].extend(items[n_test+n_val:])


for split, items in splits.items():

    img_out = OUT / split / "images"
    lbl_out = OUT / split / "labels"

    img_out.mkdir(parents=True, exist_ok=True)
    lbl_out.mkdir(parents=True, exist_ok=True)

    rng.shuffle(items)

    for idx, rec in enumerate(items):

        img = rec["image"]

        new_stem = (
            f"{rec['dataset']}_{idx:05d}_{img.stem}"
        )

        new_img = img_out / (new_stem + img.suffix.lower())
        new_lbl = lbl_out / (new_stem + ".txt")

        shutil.copy2(img, new_img)

        new_lbl.write_text(
            "\n".join(rec["lines"]) + "\n",
            encoding="utf-8"
        )


yaml = """path: D:/for_cat/ai/datasets/behavior_prepared
train: train/images
val: valid/images
test: test/images

nc: 3
names:
  0: EATING
  1: DRINKING
  2: OTHER
"""

(OUT / "data.yaml").write_text(yaml, encoding="utf-8")


print()
print("===== BEHAVIOR PREPARED =====")

for split in ("train", "valid", "test"):

    img_count = len(list((OUT / split / "images").glob("*")))
    lbl_count = len(list((OUT / split / "labels").glob("*.txt")))

    counts = {0: 0, 1: 0, 2: 0}

    for f in (OUT / split / "labels").glob("*.txt"):
        for line in f.read_text().splitlines():
            if line.strip():
                counts[int(line.split()[0])] += 1

    print(split.upper())
    print("  images   :", img_count)
    print("  labels   :", lbl_count)
    print("  EATING   :", counts[0])
    print("  DRINKING :", counts[1])
    print("  OTHER    :", counts[2])

print()
print("OUTPUT:", OUT)
