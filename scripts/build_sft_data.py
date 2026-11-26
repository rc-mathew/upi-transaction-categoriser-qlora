"""Turn the synthetic CSV into chat-format JSONL for supervised fine-tuning.

Usage (repo root):
    python scripts/build_sft_data.py data/synthetic/train.csv data/synthetic
writes sft_train.jsonl and sft_val.jsonl (5% held out, for spotting overfitting).
"""
import csv
import json
import random
import sys

sys.path.insert(0, "src")
from categoriser.prompt import chat  # noqa: E402

src, out_dir = sys.argv[1], sys.argv[2]
rows = list(csv.DictReader(open(src, encoding="utf-8")))
random.Random(0).shuffle(rows)
n_val = len(rows) // 20
for name, part in (("sft_val", rows[:n_val]), ("sft_train", rows[n_val:])):
    with open(f"{out_dir}/{name}.jsonl", "w", encoding="utf-8") as f:
        for r in part:
            f.write(json.dumps({"messages": chat(r)}, ensure_ascii=False) + "\n")
    print(f"{name}: {len(part)} rows")
