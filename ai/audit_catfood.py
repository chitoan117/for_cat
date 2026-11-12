from pathlib import Path

root = Path(r"D:\for_cat\ai\datasets\behavior_raw\catfood_dataset")

for split in ("train", "valid", "test"):
    label_dir = root / split / "labels"

    empty_images = 0
    full_images = 0
    both_images = 0
    usable_images = 0
    only_irrelevant = 0

    if not label_dir.exists():
        continue

    for label_path in label_dir.glob("*.txt"):
        ids = set()

        for line in label_path.read_text(
            encoding="utf-8",
            errors="ignore"
        ).splitlines():

            parts = line.strip().split()

            if not parts:
                continue

            try:
                ids.add(int(float(parts[0])))
            except ValueError:
                pass

        has_empty = 1 in ids
        has_full = 3 in ids

        if has_empty:
            empty_images += 1

        if has_full:
            full_images += 1

        if has_empty and has_full:
            both_images += 1

        if has_empty or has_full:
            usable_images += 1
        else:
            only_irrelevant += 1

    print(f"===== {split.upper()} =====")
    print("EMPTY_BOWL images :", empty_images)
    print("FOOD_FULL images  :", full_images)
    print("BOTH in same image:", both_images)
    print("USABLE images     :", usable_images)
    print("CAT/FACE only     :", only_irrelevant)
    print()
