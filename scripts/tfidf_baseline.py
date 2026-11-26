"""TF-IDF + logistic regression baseline. Writes a predictions CSV for categoriser.evaluate.

One classifier per output field. Merchant is a closed-set classifier over the training
merchants (plus "none"), so it cannot name a merchant it never saw: that is the gap
the fine-tuned model has to close.

Usage (repo root):
    python scripts/tfidf_baseline.py data/synthetic/train.csv data/test/test.csv runs/tfidf.csv
"""
import csv
import json
import sys
import time
from collections import Counter

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

train_path, test_path, out_path = sys.argv[1:4]
FIELDS = ["category", "merchant", "channel", "upi_type"]


def text(r):
    return f"{r['direction'].upper()} {r['narration']}"


train = list(csv.DictReader(open(train_path, encoding="utf-8")))
test = list(csv.DictReader(open(test_path, encoding="utf-8")))

vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), min_df=2, max_features=50000, sublinear_tf=True)  # cap keeps it inside 8 GB RAM
X = vec.fit_transform(text(r) for r in train)
# Employers (salary payers) are open-set: thousands of one-off names a classifier can't learn.
# Keep merchants seen at least 5 times; the rest become "none".
counts = Counter(r["merchant"] for r in train)
target = {f: [r[f] for r in train] for f in FIELDS}
target["merchant"] = [m if counts[m] >= 5 else "" for m in target["merchant"]]
models = {f: LogisticRegression(max_iter=1000, C=5).fit(X, target[f]) for f in FIELDS}

t0 = time.perf_counter()
Xt = vec.transform(text(r) for r in test)
preds = {f: m.predict(Xt) for f, m in models.items()}
ms = (time.perf_counter() - t0) * 1000 / len(test)

import os
os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
with open(out_path, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["narration", "output", "latency_ms"])
    for i, r in enumerate(test):
        out = {k: (preds[k][i] or None) for k in FIELDS}
        w.writerow([r["narration"], json.dumps(out), round(ms, 3)])
print(f"wrote {out_path}; {ms:.3f} ms per transaction on this machine")
