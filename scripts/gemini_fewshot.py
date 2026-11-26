"""Gemini few-shot baseline. Writes a predictions CSV for categoriser.evaluate.

No response_schema is passed on purpose: the fine-tuned model gets no constrained
decoding either, so JSON validity is compared like for like.

Usage (repo root, GEMINI_API_KEY set):
    python scripts/gemini_fewshot.py data/test/test.csv runs/gemini.csv --model gemini-3.8-flash
Re-running the same command resumes after the last written row.
"""
import argparse
import csv
import os
import sys
import time

from google import genai
from google.genai import errors, types

sys.path.insert(0, "src")
from categoriser.schema import Category, Channel  # noqa: E402

# Examples use merchants that are not in the test set, so no answer leaks into the prompt.
EXAMPLES = """\
Narration: UPI/P2M/431200981245/DOMINOS PIZZA/UPI/HDFC BANK | Direction: debit
{"category": "Food & dining", "merchant": "Domino's", "channel": "UPI", "upi_type": "P2M"}
Narration: UPI-ZEPTO MARKETPLACE-zepto@ybl-YESB0YBLUPI-431311092214-UPI | Direction: debit
{"category": "Groceries", "merchant": "Zepto", "channel": "UPI", "upi_type": "P2M"}
Narration: POS 459150XXXXXX1122 MYNTRA DESIGNS BANGALORE | Direction: debit
{"category": "Shopping", "merchant": "Myntra", "channel": "CARD", "upi_type": null}
Narration: ACH D- TATA CAPITAL LTD-TCFL000000098765 | Direction: debit
{"category": "Loan EMI", "merchant": "Tata Capital", "channel": "NACH", "upi_type": null}
Narration: NEFT CR-HSBC0400002-ORBIT SYSTEMS PVT LTD-SALARY OCT 2026-HSBCN26300112233 | Direction: credit
{"category": "Salary", "merchant": "Orbit Systems", "channel": "NEFT", "upi_type": null}
Narration: UPI/ANKIT SHARMA/431622019847/trip share | Direction: debit
{"category": "Transfer out", "merchant": null, "channel": "UPI", "upi_type": "P2P"}
Narration: ATW-524409XXXXXX5566-S1BW0123-MYSORE | Direction: debit
{"category": "Cash withdrawal", "merchant": null, "channel": "ATM", "upi_type": null}
Narration: CHRG: NACH RTN 14-10-2026 | Direction: debit
{"category": "Bank charges & penalties", "merchant": null, "channel": "INTERNAL", "upi_type": null}
"""

PROMPT = f"""You categorise Indian bank statement lines. Reply with one JSON object and nothing else:
{{"category": ..., "merchant": ..., "channel": ..., "upi_type": ...}}

category: one of {[c.value for c in Category]}
channel: one of {[c.value for c in Channel]}
merchant: canonical brand as people say it, without legal suffixes (Ltd, Pvt, Finserv, Of India); keep acronyms upper case, otherwise Title Case. Null for individuals, cash and bank entries. Never output a person's name.
Raw meat, fish and dairy delivery (e.g. Licious) is Groceries, not Food & dining.
upi_type: "P2M" for a business payee, "P2P" for a person, null when channel is not UPI.
Rules: an explicit word (RENT, EMI, SALARY, REFUND) beats the merchant; a person's name means Transfer in/out; otherwise "Other".

Examples:
{EXAMPLES}
"""

ap = argparse.ArgumentParser()
ap.add_argument("test_csv")
ap.add_argument("out_csv")
ap.add_argument("--model", default="gemini-3.8-flash")  # the API names its replacement when a model is retired
ap.add_argument("--sleep", type=float, default=6.0, help="seconds between calls; free tier is rate-limited")
args = ap.parse_args()

os.makedirs(os.path.dirname(args.out_csv) or ".", exist_ok=True)
rows = list(csv.DictReader(open(args.test_csv, encoding="utf-8")))
new_file = not os.path.exists(args.out_csv) or os.path.getsize(args.out_csv) == 0
done = 0 if new_file else sum(1 for _ in open(args.out_csv, encoding="utf-8")) - 1  # minus header
client = genai.Client()  # reads GEMINI_API_KEY
config = types.GenerateContentConfig(temperature=0, response_mime_type="application/json")

with open(args.out_csv, "a", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    if new_file:
        w.writerow(["narration", "output", "latency_ms", "input_tokens", "output_tokens"])
    for r in rows[done:]:
        q = f"{PROMPT}\nNarration: {r['narration']} | Direction: {r['direction']}\n"
        t0 = time.perf_counter()
        for attempt in range(6):  # free tier returns 429/503 under load; back off and retry
            try:
                resp = client.models.generate_content(model=args.model, contents=q, config=config)
                break
            except errors.APIError as e:
                if e.code not in (429, 500, 503) or attempt == 5:
                    raise
                print(f"  {e.code}, retrying in {10 * 2**attempt}s")
                time.sleep(10 * 2**attempt)
                t0 = time.perf_counter()  # latency excludes waiting
        ms = (time.perf_counter() - t0) * 1000
        u = resp.usage_metadata
        w.writerow([r["narration"], (resp.text or "").strip(), round(ms), u.prompt_token_count, u.candidates_token_count])
        f.flush()  # keep progress if the free tier cuts us off
        time.sleep(args.sleep)

print(f"wrote {args.out_csv}; score with: cd src && python -m categoriser.evaluate ../{args.test_csv} ../{args.out_csv}")
