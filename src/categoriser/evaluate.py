"""Score model outputs against the hand-labelled test set.

Every approach (TF-IDF, Gemini few-shot, fine-tuned Qwen) writes a predictions CSV
with the same rows as the test CSV plus one column, `output`: the raw string the
model produced. Scoring the raw string is what makes JSON validity measurable.

Usage (repo root):
    python -m categoriser.evaluate data/test/test.csv runs/gemini.csv
"""
import csv
import json
import re
import sys

import numpy as np
from sklearn.metrics import f1_score

from categoriser.schema import TransactionLabel

INVALID = "__invalid__"  # counts as a wrong category for every class


def parse(output: str):
    """Return a TransactionLabel, or None if the output is not valid schema JSON."""
    try:
        return TransactionLabel.model_validate_json(output)
    except Exception:
        return None


def norm(merchant):
    return (merchant or "").strip().lower()


def loose(a, b):
    """Lenient merchant match: same name once case and punctuation are ignored, or one name
    contains the other ("Spencer's" vs "Spencers Retail"). Both empty also counts."""
    a, b = (re.sub(r"[^a-z0-9 ]", "", (x or "").lower()).strip() for x in (a, b))
    return a == b or (bool(a) and bool(b) and (a in b or b in a))


def macro_f1(gold, pred):
    labels = sorted(set(gold))  # gold classes only, so INVALID never earns credit
    return f1_score(gold, pred, labels=labels, average="macro", zero_division=0)


def bootstrap_ci(gold, pred, n=1000, seed=0):
    """95% interval for macro-F1. 300 rows is small; report this next to every score."""
    rng = np.random.default_rng(seed)
    gold, pred = np.array(gold), np.array(pred)
    scores = [macro_f1(gold[i], pred[i]) for i in (rng.integers(0, len(gold), len(gold)) for _ in range(n))]
    return float(np.percentile(scores, 2.5)), float(np.percentile(scores, 97.5))


def score(gold_rows, outputs):
    assert len(gold_rows) == len(outputs), f"{len(outputs)} predictions for {len(gold_rows)} test rows: finish (re-run) the prediction script first"
    parsed = [parse(o) for o in outputs]
    gold = [r["category"] for r in gold_rows]
    pred = [p.category.value if p else INVALID for p in parsed]
    merch_ok = [p is not None and norm(p.merchant) == norm(r["merchant"]) for p, r in zip(parsed, gold_rows)]
    unseen = [i for i, r in enumerate(gold_rows) if r["unseen_merchant"] == "1"]

    lo, hi = bootstrap_ci(gold, pred)
    result = {
        "n": len(gold),
        "macro_f1": macro_f1(gold, pred),
        "macro_f1_ci95": [lo, hi],
        "merchant_exact_match": float(np.mean(merch_ok)),
        "merchant_lenient_match": float(np.mean([p is not None and loose(p.merchant, r["merchant"]) for p, r in zip(parsed, gold_rows)])),
        "json_validity": sum(p is not None for p in parsed) / len(parsed),
    }
    if unseen:
        result["unseen_macro_f1"] = macro_f1([gold[i] for i in unseen], [pred[i] for i in unseen])
        result["unseen_merchant_exact_match"] = float(np.mean([merch_ok[i] for i in unseen]))
    # federal rows are copied from a real statement; every other format was drafted.
    # This slice is the honest score; report it next to the overall one.
    real = [i for i, r in enumerate(gold_rows) if r.get("bank_format") == "federal"]
    if real:
        result["real_layout_n"] = len(real)
        result["real_layout_macro_f1"] = macro_f1([gold[i] for i in real], [pred[i] for i in real])
    return result


def _selfcheck():
    rows = [
        {"category": "Food & dining", "merchant": "Swiggy", "unseen_merchant": "0"},
        {"category": "Salary", "merchant": "", "unseen_merchant": "1"},
    ]
    good = '{"category":"Food & dining","merchant":"swiggy","channel":"UPI","upi_type":"P2M"}'
    r = score(rows, [good, "not json"])
    assert r["json_validity"] == 0.5 and r["merchant_exact_match"] == 0.5
    assert r["macro_f1"] == 0.5 and r["unseen_macro_f1"] == 0.0


if __name__ == "__main__":
    _selfcheck()
    gold_path, pred_path = sys.argv[1], sys.argv[2]
    gold_rows = list(csv.DictReader(open(gold_path, encoding="utf-8")))
    outputs = [r["output"] for r in csv.DictReader(open(pred_path, encoding="utf-8"))]
    print(json.dumps(score(gold_rows, outputs), indent=2))
    # error list: read these before trusting the score; some "errors" will be label mistakes
    for r, o in zip(gold_rows, outputs):
        p = parse(o)
        got = (p.category.value, p.merchant) if p else ("INVALID", o[:60])
        if not p or got[0] != r["category"] or norm(got[1]) != norm(r["merchant"]):
            print(f"- {r['narration'][:70]}\n    gold: {r['category']} / {r['merchant'] or None}   got: {got[0]} / {got[1]}", file=sys.stderr)
