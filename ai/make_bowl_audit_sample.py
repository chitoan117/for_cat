from pathlib import Path
import random
import shutil

ROOT = Path(r"D:\for_cat\ai\datasets\behavior_raw\bowl_dataset")
OUT  = Path(r"D:\for_cat\bowl_audit_sample")

if OUT.exists():
    shutil.rmtree(OUT)

(OUT / "images").mkdir(parents=True)
(OUT / "labels").mkdir(parents=True)

random.seed(42)

groups = {
    "CAT_ONLY": [],
    "DOG_ONLY": [],
    "BOWL_ONLY": [],
    "BOWL_CAT": [],
    "BOWL_DOG": [],
    "EMPTY": [],
}

for split in ("train", "valid", "test"):
    img_dir = ROOT / split / "images"
    lbl_dir = ROOT / split / "labels"

    for img in img_dir.iterdir():

        if not img.is_file():
            continue

        lbl = lbl_dir / (img.stem + ".txt")

        if not lbl.exists():
            continue

        text = lbl.read_text(
            encoding="utf-8",
            errors="ignore"
        ).strip()

        if not text:
            groups["EMPTY"].append((split, img, lbl))
            continue

        ids = set()

        for line in text.splitlines():
            parts = line.split()

            if len(parts) < 5:
                continue

            try:
                ids.add(int(float(parts[0])))
            except:
                pass

        if ids == {1}:
            groups["CAT_ONLY"].append((split, img, lbl))

        elif ids == {2}:
            groups["DOG_ONLY"].append((split, img, lbl))

        elif ids == {0}:
            groups["BOWL_ONLY"].append((split, img, lbl))

        elif ids == {0,1}:
            groups["BOWL_CAT"].append((split, img, lbl))

        elif ids == {0,2}:
            groups["BOWL_DOG"].append((split, img, lbl))


limits = {
    "CAT_ONLY": 20,
    "DOG_ONLY": 20,
    "BOWL_ONLY": 20,
    "BOWL_CAT": 20,
    "BOWL_DOG": 20,
    "EMPTY": 10,
}

manifest = []

for group_name, items in groups.items():

    random.shuffle(items)

    selected = items[:limits[group_name]]

    for i, (split, img, lbl) in enumerate(selected):

        new_stem = f"{group_name}_{i:03d}_{split}_{img.stem}"

        shutil.copy2(
            img,
            OUT / "images" / (new_stem + img.suffix.lower())
        )

        shutil.copy2(
            lbl,
            OUT / "labels" / (new_stem + ".txt")
        )

        manifest.append(
            f"{group_name}\t{split}\t{img.name}"
        )

(OUT / "manifest.txt").write_text(
    "\n".join(manifest),
    encoding="utf-8"
)

print("===== AUDIT SAMPLE =====")

for name in groups:
    print(
        name,
        ":",
        min(len(groups[name]), limits[name])
    )

print("TOTAL:", len(manifest))
print("OUTPUT:", OUT)
