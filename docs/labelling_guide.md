# Labelling guide (v0.1, draft)

One guide for everything: the synthetic generator, the hand-labelled test set and the
Gemini few-shot prompt. If two labellers (or you on two different days) could disagree on
a row, the rule for it belongs here.

## Input and output

- **Input:** the narration string plus `direction` (debit or credit). Every real statement
  row has a Dr/Cr column, and without it "Refund" vs "Shopping" or "Transfer in" vs
  "Transfer out" is often undecidable.
- **Output:** JSON matching `src/categoriser/schema.py`:
  `{"category": ..., "merchant": ..., "channel": ..., "upi_type": ...}`

`recurring` from the original plan has been dropped: a single narration can't show
whether something repeats. Recurrence is a feature to compute downstream from the
transaction history, in the Risk Agent's Credit sub-agent.

## Categories (20)

| Category | Direction | Includes | Does not include |
|---|---|---|---|
| Salary | credit | NEFT/IMPS credits from an employer, "SAL", "SALARY" | Freelance payments from individuals → Transfer in |
| Refund & cashback | credit | Merchant refunds, UPI cashback, reversals of a failed debit | Interest → Interest & dividend |
| Interest & dividend | credit | "INT.PD", "INT CR", FD interest, dividend credits | |
| Transfer in | credit | P2P UPI/IMPS/NEFT from individuals, self-transfers in | Salary |
| Loan EMI | debit | NACH/ACH debits to lenders/NBFCs (Bajaj Finance, HDFC Ltd, etc.), "EMI" | Credit card bill → Credit card payment |
| Credit card payment | debit | Payments to a card account (CRED, BillDesk card pay, "CC PAYMENT") | |
| Rent | debit | Rent via NoBroker/CRED rent/Housing, or narration says "RENT" | P2P to a person with no rent marker → Transfer out |
| Insurance | debit | LIC, health/motor/term premiums | |
| Food & dining | debit | Swiggy, Zomato, restaurants, cafes | Instamart, Blinkit, Zepto → Groceries |
| Groceries | debit | BigBasket, Blinkit, Zepto, Instamart, DMart, kirana P2M | |
| Shopping | debit | Amazon, Flipkart, Myntra, Ajio, Nykaa, electronics, retail | Amazon Pay bill payments → Bills & utilities |
| Travel & transport | debit | Uber, Ola, Rapido, IRCTC, airlines, metro, FASTag, fuel | |
| Bills & utilities | debit | Electricity (BESCOM etc.), gas, water, broadband, mobile recharge, DTH | |
| Entertainment & subscriptions | debit | Netflix, Spotify, Hotstar, BookMyShow, Google Play, app stores | |
| Health | debit | Pharmacies, hospitals, labs, PharmEasy, 1mg, Practo | Health insurance premium → Insurance |
| Investments | debit | SIPs, mutual funds, Zerodha/Groww, NPS, PPF, FD booking | |
| Cash withdrawal | debit | ATM (ATW, NWD, "CASH WDL") | |
| Bank charges & penalties | debit | SMS charges, AMC, GST on charges, **ECS/NACH return (bounce) charges** | |
| Transfer out | debit | P2P UPI/IMPS/NEFT to individuals, self-transfers out | Rent if marked; payments to a business UPI ID → its spending category |
| Other | either | Genuinely undecidable or not in the list | Use sparingly; target under 5% of the test set |

Bounce charges sit inside "Bank charges & penalties" but are the single most useful risk
signal for a lender, so the test set must include at least 10 of them.

## Field rules

- **merchant:** the canonical brand, Title Case: "SWIGGY BANGALORE" → "Swiggy",
  "AMAZON PAY IN E COMMERC" → "Amazon". Null for individuals, ATM, interest and charges.
  Never copy a person's name into the output.
- **channel:** from the rail, not the merchant. NACH covers ACH and ECS mandates; CARD
  covers POS and card-not-present.
- **upi_type:** P2M when the payee VPA or name is a business (contains a merchant handle,
  "PAYTM-", "@ybl" merchant IDs, a company name); P2P for a person. Null when channel is
  not UPI.

## Tie-breakers, in order

1. An explicit word in the narration wins ("RENT", "EMI", "SALARY", "REFUND").
2. Otherwise the merchant decides the category.
3. Otherwise a person's name means Transfer in/out.
4. Otherwise "Other". Don't guess from the amount.

## Narration formats to cover

Formats differ by bank, and that variety is most of what makes this task hard. These
patterns are approximate; check each one against the layout of a real statement (look
only at the layout and copy no real values) before relying on it.

- UPI: `UPI/DR/<12-digit RRN>/<NAME>/<BANK>/<vpa>/<note>`,
  `UPI-<NAME>-<vpa>-<IFSC>-<RRN>-<note>`, `UPI/<RRN>/<note>/<vpa>/<Bank name>`
- NEFT/IMPS: `NEFT-<UTR>-<SENDER NAME>-<note>`, `IMPS/P2A/<RRN>/<name>/<bank>`
- NACH: `ACH D- <LENDER NAME>-<mandate ref>`, `NACH DR <ref> <lender>`
- Card: `POS <masked card> <MERCHANT> <city>`, `ECOM PUR <merchant>`
- ATM: `ATW-<masked card>-<terminal>-<city>`, `NWD-...`, `CASH WDL`
- Bank: `INT.PD:<period>`, `SMS CHGS`, `CHRG: ECS RTN`, `GST @18% ON CHGS`

## Test-set rules (read before labelling)

1. **Write the 300 test narrations before you write the synthetic generator.** If you
   build the generator first, its templates shape what you think a narration looks like,
   and the test set ends up measuring how well the model learned your templates.
2. Hold out merchants: about a third of test rows use merchants that never appear in the
   generator's merchant lists. Report F1 separately on this "unseen merchant" slice. It's
   the slice where a fine-tuned LLM should beat TF-IDF.
3. At least 10 rows per category, and spread the rows across at least 6 bank formats.
4. No real personal data: invent names, VPAs and reference numbers.
