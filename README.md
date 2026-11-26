# UPI Transaction Categoriser (QLoRA)

> **Work in progress.** Data, test set and baselines are done; fine-tuning is next.
> This README is updated as each stage finishes.

A small open model (Qwen2.5 1.5B), fine-tuned with QLoRA, that turns raw Indian bank and UPI
statement lines into structured fields, and runs on a laptop CPU.

```
UPIOUT/618204417735/q512093847@ybl/Paid via /5814   (debit)
→ {"category": "Food & dining", "merchant": null, "channel": "UPI", "upi_type": "P2M"}
```

**Why it matters:** lenders score cash flow from categorised transactions when underwriting
(for example through India's Account Aggregator system), and personal-finance apps need the
same categories. A narrow, repetitive task like this is where a small fine-tuned model should
compete with a large hosted LLM on cost, and it keeps transaction data on the bank's own machines.

## Status

| Stage | State |
|---|---|
| Output schema and labelling guide | Done |
| Hand-labelled test set (217 rows) | Done |
| Synthetic training data generator (24k rows) | Done |
| Baselines: TF-IDF + logistic regression, Gemini few-shot | Done |
| QLoRA fine-tune on Kaggle (T4) | Next |
| 4-bit GGUF export, CPU latency, Hugging Face model card and demo | Planned |

## Results so far

All approaches are scored on the same hand-labelled test set, never on synthetic data.

| Metric | TF-IDF + LR | Gemini 3.5 Flash-Lite (8-shot) | Fine-tuned Qwen2.5 1.5B |
|---|---|---|---|
| Category macro-F1 (95% CI) | 0.85 (0.79–0.88) | 0.92–0.97 | — |
| Macro-F1, real bank layouts only (35 rows) | 0.85 | 0.60 | — |
| Macro-F1, merchants unseen in training | 0.62 | 0.96 | — |
| Merchant name, exact / lenient match | 0.66 / 0.66 | 0.87 / 0.93 | — |
| JSON validity | 1.00 | 1.00 | — |

**Early reading.** Gemini is strong overall and on unseen merchants, but drops sharply on real
Federal Bank lines, where many UPI payments carry no merchant name and only a merchant category
code (MCC) shows the category. TF-IDF cannot name merchants it never saw. The fine-tuned model's
target is to come close to Gemini overall and beat it on real layouts, at no API cost. The
real-layout slice is only 35 rows, so treat that gap as a strong signal, not a proven result.

## Data

**Output schema** ([`src/categoriser/schema.py`](src/categoriser/schema.py)): 20 categories
built for lending (EMIs, credit-card payments, rent, bounce charges kept separate), merchant,
payment channel, and P2M/P2P for UPI. Input is the narration plus debit/credit direction.

**Test set** ([`data/test/test.csv`](data/test/test.csv)), 217 rows, at least 10 per category:

- 35 rows copied from a real Federal Bank statement (`bank_format = federal`), with every name,
  UPI ID, reference and account number replaced. These give the honest `real_layout` score.
- The rest were drafted in the approximate layouts of six other banks, then reviewed.
- 70 rows use merchants that never appear in the training data (`unseen_merchant = 1`).
- Labelling rules, including the MCC rule for name-less UPI lines, are in
  [`docs/labelling_guide.md`](docs/labelling_guide.md).

**Training data** ([`scripts/generate_synthetic.py`](scripts/generate_synthetic.py)): 24,000
synthetic rows, balanced across categories, covering UPI, NACH, NEFT, IMPS, card, ATM and bank
entries in seven bank layouts. Deterministic, so it is regenerated rather than committed. It never
uses a test-set unseen merchant or reproduces a test narration.

No real personal data is stored in this repository.

## How to run

```bash
pip install -r requirements.txt

# training data
python scripts/generate_synthetic.py --n 24000 --out data/synthetic/train.csv
python scripts/build_sft_data.py data/synthetic/train.csv data/synthetic

# baselines
python scripts/tfidf_baseline.py data/synthetic/train.csv data/test/test.csv runs/tfidf.csv
python scripts/gemini_fewshot.py data/test/test.csv runs/gemini.csv --model gemini-3.5-flash-lite   # needs GEMINI_API_KEY

# score any predictions file
cd src && python -m categoriser.evaluate ../data/test/test.csv ../runs/tfidf.csv
```

Fine-tuning: [`notebooks/finetune_qlora.ipynb`](notebooks/finetune_qlora.ipynb), run on Kaggle
with a T4 GPU.

## Repository layout

```
src/categoriser/   schema, prompt format, evaluation
scripts/           data generator, SFT data builder, baselines, test-set checker
data/test/         hand-labelled test set
docs/              labelling guide
notebooks/         Kaggle QLoRA notebook
```

## Limitations

- Most test rows are drafted rather than taken from real statements, because only one real
  account was available. The `real_layout` score is reported separately for that reason.
- Bank layouts other than Federal Bank are approximations.
- Training data is fully synthetic.

Built with AI pair-programming.
