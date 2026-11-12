from pathlib import Path
from collections import Counter

ROOT = Path(r"D:\for_cat\ai\datasets\behavior_raw\bowl_dataset")

CLASSES = {
    0: "BOWL",
    1: "CAT",
    2: "DOG"
}

bad = []

for split in ("train", "valid", "test"):

    label_dir = ROOT / split / "labels"

    for label_path in label_dir.glob("*.txt"):

        for line_no, line in enumerate(
            label_path.read_text(
                encoding="utf-8",
                errors="ignore"
            ).splitlines(),
            start=1
        ):

            parts = line.strip().split()

            if len(parts) != 5:
                continue

            try:
                cid = int(float(parts[0]))
                x, y, w, h = map(float, parts[1:])
            except ValueError:
                continue

            left   = x - w / 2
            right  = x + w / 2
            top    = y - h / 2
            bottom = y + h / 2

            overflow = max(
                0,
                -left,
                right - 1,
                -top,
                bottom - 1
            )

            if overflow > 0:
                bad.append({
                    "split": split,
                    "file": label_path.name,
                    "class": CLASSES.get(cid, str(cid)),
                    "overflow": overflow,
                    "left": left,
                    "right": right,
                    "top": top,
                    "bottom": bottom
                })

print("===== OUTSIDE BOX AUDIT =====")
print("Total:", len(bad))

levels = Counter()

for b in bad:
    o = b["overflow"]

    if o <= 0.001:
        levels["<= 0.001"] += 1
    elif o <= 0.005:
        levels["0.001 - 0.005"] += 1
    elif o <= 0.01:
        levels["0.005 - 0.01"] += 1
    elif o <= 0.05:
        levels["0.01 - 0.05"] += 1
    else:
        levels["> 0.05"] += 1

print()
print("===== SEVERITY =====")
for k in (
    "<= 0.001",
    "0.001 - 0.005",
    "0.005 - 0.01",
    "0.01 - 0.05",
    "> 0.05"
):
    print(f"{k}: {levels[k]}")

print()
print("===== BY CLASS =====")
classes = Counter(b["class"] for b in bad)

for name, count in classes.items():
    print(name, ":", count)

print()
print("===== WORST 20 =====")

for b in sorted(
    bad,
    key=lambda x: x["overflow"],
    reverse=True
)[:20]:

    print(
        b["split"],
        b["class"],
        f"overflow={b['overflow']:.6f}",
        b["file"]
    )
