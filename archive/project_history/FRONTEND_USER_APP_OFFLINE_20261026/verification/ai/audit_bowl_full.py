from pathlib import Path
from collections import Counter, defaultdict
import hashlib

ROOT = Path(r"D:\for_cat\ai\datasets\behavior_raw\bowl_dataset")

CLASSES = {
    0: "BOWL",
    1: "CAT",
    2: "DOG",
}

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

total_images = 0
total_labels = 0
class_objects = Counter()
images_by_class = Counter()
class_combinations = Counter()

missing_labels = []
orphan_labels = []
empty_labels = []
invalid_lines = []
invalid_classes = []
invalid_boxes = []

hash_locations = defaultdict(list)

print("========== BOWL DATASET FULL AUDIT ==========")

for split in ("train", "valid", "test"):

    image_dir = ROOT / split / "images"
    label_dir = ROOT / split / "labels"

    images = {
        p.stem: p
        for p in image_dir.iterdir()
        if p.is_file() and p.suffix.lower() in IMAGE_EXTS
    }

    labels = {
        p.stem: p
        for p in label_dir.glob("*.txt")
        if p.is_file()
    }

    print()
    print(f"===== {split.upper()} =====")
    print("Images :", len(images))
    print("Labels :", len(labels))

    total_images += len(images)
    total_labels += len(labels)

    split_objects = Counter()
    split_image_classes = Counter()

    for stem, image_path in images.items():

        # exact duplicate detection
        digest = hashlib.sha256(
            image_path.read_bytes()
        ).hexdigest()

        hash_locations[digest].append(
            (split, image_path.name)
        )

        label_path = labels.get(stem)

        if label_path is None:
            missing_labels.append(
                str(image_path)
            )
            continue

        text = label_path.read_text(
            encoding="utf-8",
            errors="ignore"
        ).strip()

        if not text:
            empty_labels.append(
                str(label_path)
            )
            continue

        present = set()

        for line_no, line in enumerate(
            text.splitlines(), start=1
        ):

            parts = line.strip().split()

            if len(parts) != 5:
                invalid_lines.append(
                    (str(label_path), line_no, line)
                )
                continue

            try:
                class_id = int(float(parts[0]))
                x, y, w, h = map(float, parts[1:])
            except ValueError:
                invalid_lines.append(
                    (str(label_path), line_no, line)
                )
                continue

            if class_id not in CLASSES:
                invalid_classes.append(
                    (str(label_path), line_no, class_id)
                )
                continue

            # YOLO normalized box basic validation
            if not (
                0 <= x <= 1 and
                0 <= y <= 1 and
                0 < w <= 1 and
                0 < h <= 1 and
                x - w / 2 >= -1e-6 and
                x + w / 2 <= 1 + 1e-6 and
                y - h / 2 >= -1e-6 and
                y + h / 2 <= 1 + 1e-6
            ):
                invalid_boxes.append(
                    (
                        str(label_path),
                        line_no,
                        class_id,
                        x, y, w, h
                    )
                )

            split_objects[class_id] += 1
            class_objects[class_id] += 1
            present.add(class_id)

        if present:
            combo = tuple(sorted(present))
            class_combinations[combo] += 1

            for cid in present:
                split_image_classes[cid] += 1
                images_by_class[cid] += 1

    for stem, label_path in labels.items():
        if stem not in images:
            orphan_labels.append(
                str(label_path)
            )

    for cid in CLASSES:
        print(
            f"{CLASSES[cid]} objects:",
            split_objects[cid]
        )

    for cid in CLASSES:
        print(
            f"Images containing {CLASSES[cid]}:",
            split_image_classes[cid]
        )

print()
print("========== TOTAL ==========")
print("Images :", total_images)
print("Labels :", total_labels)

for cid in CLASSES:
    print(
        f"{CLASSES[cid]} objects:",
        class_objects[cid]
    )

print()
print("===== IMAGE CLASS COMBINATIONS =====")

for combo, count in sorted(
    class_combinations.items(),
    key=lambda x: -x[1]
):
    names = "+".join(
        CLASSES[c] for c in combo
    )
    print(f"{names}: {count} images")

duplicate_groups = [
    items
    for items in hash_locations.values()
    if len(items) > 1
]

cross_split_duplicates = []

for group in duplicate_groups:
    splits = {x[0] for x in group}

    if len(splits) > 1:
        cross_split_duplicates.append(group)

print()
print("===== DATA QUALITY =====")
print("Missing labels          :", len(missing_labels))
print("Orphan labels           :", len(orphan_labels))
print("Empty labels            :", len(empty_labels))
print("Invalid label lines     :", len(invalid_lines))
print("Invalid class IDs       :", len(invalid_classes))
print("Invalid/outside boxes   :", len(invalid_boxes))
print("Exact duplicate groups  :", len(duplicate_groups))
print("Cross-split dup groups  :", len(cross_split_duplicates))

print()
print("===== CROSS-SPLIT DUPLICATE EXAMPLES =====")

for group in cross_split_duplicates[:20]:
    print(group)

print()
print("AUDIT COMPLETE")
