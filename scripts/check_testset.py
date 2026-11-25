"""Validate data/test/test.csv against the schema and the labelling-guide quotas.

Columns: narration,direction,category,merchant,channel,upi_type,bank_format,unseen_merchant
Usage: python scripts/check_testset.py [path]   (run from repo root)
"""
import csv
import sys
from collections import Counter

sys.path.insert(0, "src")
from categoriser.schema import Category, Direction, TransactionLabel  # noqa: E402

path = sys.argv[1] if len(sys.argv) > 1 else "data/test/test.csv"
rows = list(csv.DictReader(open(path, encoding="utf-8")))
errors = []
for i, r in enumerate(rows, start=2):  # line 1 is the header
    try:
        Direction(r["direction"])
        TransactionLabel(**{k: (r[k] or None) for k in ("category", "merchant", "channel", "upi_type")})
    except Exception as e:
        errors.append(f"line {i}: {str(e).splitlines()[0]}")
    if not r["narration"].strip():
        errors.append(f"line {i}: empty narration")

cats = Counter(r["category"] for r in rows)
formats = {r["bank_format"] for r in rows}
unseen = sum(r["unseen_merchant"] == "1" for r in rows)
dupes = len(rows) - len({r["narration"] for r in rows})

print(f"rows {len(rows)}/300, bank formats {len(formats)}/6, unseen-merchant rows {unseen} (~100 target), duplicate narrations {dupes}")
for c in Category:
    if cats[c.value] < 10:
        print(f"  need >=10: {c.value} has {cats[c.value]}")
print("\n".join(errors[:20]) or "schema OK")
sys.exit(1 if errors else 0)
