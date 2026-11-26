"""Generate synthetic training narrations in the same CSV format as the test set.

Deterministic (fixed seed), so the output is not committed: regenerate it instead.
Merchants flagged unseen_merchant=1 in the test set are never generated, and no
generated narration may equal a test narration.

Usage (repo root):
    python scripts/generate_synthetic.py --n 24000 --out data/synthetic/train.csv
"""
import argparse
import csv
import random
import sys

from faker import Faker

sys.path.insert(0, "src")
from categoriser.schema import Category, TransactionLabel  # noqa: E402

BANKS = ["hdfc", "sbi", "icici", "axis", "kotak", "canara", "federal"]
BANK4 = ["HDFC", "SBIN", "ICIC", "UTIB", "KKBK", "CNRB", "YESB", "BARB", "PUNB", "FDRL"]
BANK_NAMES = ["HDFC Bank", "ICICI Bank", "Axis Bank", "State Bank Of India", "Kotak Mahindra", "Yes Bank", "Canara Bank", "Federal Bank"]
CITIES = ["BANGALORE", "BENGALURU", "MYSORE", "CHENNAI", "MUMBAI", "PUNE", "HYDERABAD", "KOCHI", "DELHI", "BLR"]
AREAS = ["KORAMANGALA", "INDIRANAGAR", "JAYANAGAR", "BTM LAYOUT", "WHITEFIELD", "HEBBAL", "BANASHANKARI", "MALLESWARAM", "ELECTRONIC CITY", "YELAHANKA"]
P2P_HANDLES = ["okaxis", "oksbi", "okhdfcbank", "okicici", "ybl", "paytm", "ibl", "axl", "upi"]

# category: (MCC codes, [(canonical merchant, narration name, vpa)])
MERCHANTS = {
    "Food & dining": (["5812", "5814", "5462"], [
        ("Swiggy", "SWIGGY", "swiggy@icici"), ("Zomato", "ZOMATO LTD", "zomato.payu@ybl"),
        ("Domino's", "DOMINOS PIZZA", "dominos.rzp@hdfcbank"), ("McDonald's", "MCDONALDS", "mcdonalds@axisbank"),
        ("KFC", "KFC", "kfc.payu@icici"), ("Starbucks", "TATA STARBUCKS", "starbucks@hdfcbank"),
        ("Burger King", "BURGER KING INDIA", "burgerking@ybl"), ("Pizza Hut", "PIZZA HUT", "pizzahut.rzp@icici"),
        ("EatSure", "EATSURE", "eatsure@axisbank"), ("Cafe Coffee Day", "CAFE COFFEE DAY", "ccd@ybl"),
        ("Subway", "SUBWAY", "subway.payu@hdfcbank"), ("Haldiram's", "HALDIRAMS", "haldirams@icici")]),
    "Groceries": (["5411", "5499"], [
        ("BigBasket", "BIGBASKET", "bigbasket@hdfcbank"), ("Blinkit", "BLINKIT", "blinkit.payu@ybl"),
        ("Zepto", "ZEPTO MARKETPLACE", "zepto@ybl"), ("Instamart", "SWIGGY INSTAMART", "swiggy.instamart@icici"),
        ("DMart", "DMART AVENUE SUPERMARTS", "dmart@hdfcbank"), ("JioMart", "JIOMART", "jiomart@axisbank"),
        ("Nature's Basket", "NATURES BASKET", "naturesbasket@icici"), ("FreshToHome", "FRESHTOHOME", "freshtohome.rzp@icici"),
        ("More", "MORE RETAIL", "moreretail@ybl")]),
    "Shopping": (["5311", "5399", "5691", "5732"], [
        ("Amazon", "AMAZON PAY IN E COMMERC", "amazonupi@apl"), ("Flipkart", "FLIPKART INTERNET PVT LTD", "flipkart.rzp@axisbank"),
        ("Myntra", "MYNTRA DESIGNS", "myntra@ybl"), ("Ajio", "AJIO RELIANCE RETAIL", "ajio@hdfcbank"),
        ("Nykaa", "NYKAA E RETAIL", "nykaa.rzp@icici"), ("Croma", "CROMA INFINITI RETAIL", "croma@axisbank"),
        ("Meesho", "MEESHO", "meesho.rzp@icici"), ("Reliance Digital", "RELIANCE DIGITAL", "reliancedigital@ybl"),
        ("Tata CLiQ", "TATA CLIQ", "tatacliq@hdfcbank"), ("Westside", "WESTSIDE TRENT", "westside@icici")]),
    "Travel & transport": (["4111", "4112", "4121", "4722", "5541"], [
        ("Uber", "UBER INDIA", "uber@axisbank"), ("Ola", "OLA CABS", "olacabs@ybl"),
        ("Rapido", "RAPIDO", "rapido.rzp@icici"), ("IRCTC", "IRCTC", "irctc.upi@sbi"),
        ("MakeMyTrip", "MAKEMYTRIP INDIA PVT LTD", "makemytrip.payu@axisbank"), ("IndiGo", "INDIGO AIRLINES", "indigo@hdfcbank"),
        ("redBus", "REDBUS", "redbus.payu@icici"), ("Namma Metro", "BMRCL NAMMA METRO", "bmrcl@ybl"),
        ("Cleartrip", "CLEARTRIP", "cleartrip@axisbank"), ("Air India", "AIR INDIA LTD", "airindia@icici")]),
    "Bills & utilities": (["4814", "4900", "4899"], [
        ("BESCOM", "BESCOM", "bescom.billdesk@hdfcbank"), ("Airtel", "AIRTEL", "airtelpayments@airtel"),
        ("Jio", "RELIANCE JIO", "jio@axisbank"), ("Vi", "VI PREPAID", "vi.billdesk@hdfcbank"),
        ("BSNL", "BSNL", "bsnl@sbi"), ("Tata Power", "TATA POWER", "tatapower@icici"),
        ("Indane", "INDANE GAS", "indane@ybl"), ("Excitel", "EXCITEL BROADBAND", "excitel.rzp@icici"),
        ("Dish TV", "DISH TV", "dishtv@hdfcbank")]),
    "Entertainment & subscriptions": (["7832", "7922", "5815", "5818"], [
        ("Netflix", "NETFLIX ENTERTAINMENT", "netflix.payu@hdfcbank"), ("Spotify", "SPOTIFY INDIA", "spotify@icici"),
        ("JioHotstar", "JIOHOTSTAR", "jiohotstar@axisbank"), ("BookMyShow", "BOOKMYSHOW", "bookmyshow.rzp@hdfcbank"),
        ("Google Play", "GOOGLE PLAY", "googleplay@axisbank"), ("SonyLIV", "SONYLIV", "sonyliv@ybl"),
        ("ZEE5", "ZEE5", "zee5.payu@icici"), ("Apple", "APPLE MEDIA SERVICES", "apple@hdfcbank"),
        ("YouTube", "YOUTUBE PREMIUM", "youtube@axisbank")]),
    "Health": (["5912", "8011", "8062", "8071"], [
        ("PharmEasy", "PHARMEASY", "pharmeasy@ybl"), ("Tata 1mg", "TATA 1MG", "tata1mg.payu@hdfcbank"),
        ("Practo", "PRACTO TECHNOLOGIES", "practo@hdfcbank"), ("Netmeds", "NETMEDS", "netmeds@icici"),
        ("Fortis", "FORTIS HEALTHCARE", "fortis@axisbank"), ("Narayana Health", "NARAYANA HRUDAYALAYA", "narayana@icici"),
        ("Thyrocare", "THYROCARE TECHNOLOGIES", "thyrocare@ybl"), ("Truemeds", "TRUEMEDS", "truemeds.rzp@icici"),
        ("Wellness Forever", "WELLNESS FOREVER", "wellnessforever@hdfcbank")]),
    "Investments": (["6211"], [
        ("Zerodha", "ZERODHA BROKING LTD", "zerodha@hdfcbank"), ("Groww", "GROWW", "groww@axisbank"),
        ("Paytm Money", "PAYTM MONEY", "paytmmoney@paytm"), ("ET Money", "ET MONEY", "etmoney@icici"),
        ("Angel One", "ANGEL ONE LTD", "angelone@ybl"), ("Smallcase", "SMALLCASE", "smallcase@hdfcbank"),
        ("SBI Mutual Fund", "SBI MUTUAL FUND", "sbimf@sbi"), ("Nippon India MF", "NIPPON INDIA MUTUAL FUND", "nipponmf@icici"),
        ("Dhan", "DHAN RAISE SECURITIES", "dhan@axisbank")]),
    "Loan EMI": (["6012"], [
        ("Bajaj Finance", "BAJAJ FINANCE LTD", "bajajfinance@icici"), ("HDFC Bank", "HDFC BANK LTD", "hdfcloan@hdfcbank"),
        ("Tata Capital", "TATA CAPITAL LTD", "tatacapital@hdfcbank"), ("ICICI Bank", "ICICI BANK LTD", "iciciloan@icici"),
        ("Home Credit", "HOME CREDIT INDIA", "homecredit@ybl"), ("Muthoot Finance", "MUTHOOT FINANCE", "muthoot@icici"),
        ("L&T Finance", "L AND T FINANCE", "ltfs@axisbank"), ("Fibe", "FIBE EARLYSALARY", "fibe@icici"),
        ("Aditya Birla Finance", "ADITYA BIRLA FINANCE", "abfl@hdfcbank")]),
    "Credit card payment": (["6012"], [
        ("CRED", "CRED CLUB", "cred.club@axisbank"), (None, "HDFC CREDIT CARD", "hdfccc.billdesk@hdfcbank"),
        (None, "ICICI CREDIT CARD", "icicicc@icici"), (None, "AXIS BANK CREDIT CARDS", "axiscc@axisbank"),
        (None, "KOTAK CREDIT CARD", "kotakcc@kotak")]),
    "Rent": (["6513"], [
        ("NoBroker", "NOBROKER", "nobroker.rent@icici"), ("CRED", "CRED RENT", "cred.rent@axisbank"),
        ("Magicbricks", "MAGICBRICKS", "magicbricks@hdfcbank"), ("NestAway", "NESTAWAY", "nestaway@ybl"),
        ("Colive", "COLIVE", "colive.rzp@icici")]),
    "Insurance": (["6300"], [
        ("LIC", "LIC OF INDIA", "lic@sbi"), ("Policybazaar", "POLICYBAZAAR", "policybazaar@ybl"),
        ("Max Life", "MAX LIFE INSURANCE", "maxlife@icici"), ("SBI Life", "SBI LIFE INSURANCE", "sbilife@sbi"),
        ("Bajaj Allianz", "BAJAJ ALLIANZ", "bajajallianz@hdfcbank"), ("Niva Bupa", "NIVA BUPA HEALTH", "nivabupa@icici"),
        ("Care Health", "CARE HEALTH INSURANCE", "carehealth@axisbank"), ("HDFC Life", "HDFC LIFE INSURANCE", "hdfclife@hdfcbank"),
        ("ICICI Lombard", "ICICI LOMBARD GIC", "icicilombard@icici")]),
}
DIVIDEND_PAYERS = [("Reliance Industries", "RELIANCE INDUSTRIES"), ("Wipro", "WIPRO LTD"), ("HUL", "HINDUSTAN UNILEVER"),
                   ("Coal India", "COAL INDIA LTD"), ("NTPC", "NTPC LTD"), ("Power Grid", "POWER GRID CORP"), ("Tata Motors", "TATA MOTORS LTD")]
CASHBACK = [("PhonePe", "PHONEPE CASHBACK", "cashback@ybl"), ("CRED", "CRED CASHBACK", "cred.club@axisbank"),
            ("Google Pay", "GOOGLE PAY REWARDS", "gpayrewards@okaxis"), ("Amazon", "AMAZON PAY CASHBACK", "amazonupi@apl")]
NOTES = ["Payment", "UPI", "Paid", "NA", "Payment fo", "Paid via", "order", "Pay", "Sent"]


class Gen:
    def __init__(self, seed, unseen):
        self.r = random.Random(seed)
        self.fake = Faker("en_IN")
        self.fake.seed_instance(seed)
        self.unseen = unseen

    def d(self, n):
        return "".join(self.r.choice("0123456789") for _ in range(n))

    def ref(self):
        return self.r.choice(["4", "5", "6"]) + self.d(11)

    def card(self):
        return self.r.choice(["459150", "524409", "416612", "437551", "652214"]) + "XXXXXX" + self.d(4)

    def ifsc(self):
        return self.r.choice(BANK4) + "0" + self.d(6)

    def person(self):
        name = self.fake.name().upper().replace(".", "")
        handle = name.split()[0].lower() + self.r.choice(["", self.d(2), "." + name.split()[-1][0].lower()]) + "@" + self.r.choice(P2P_HANDLES)
        return name, handle

    def merchant(self, cat):
        mccs, pool = MERCHANTS[cat]
        pool = [m for m in pool if m[0] not in self.unseen]
        return self.r.choice(mccs), self.r.choice(pool)

    # --- channel layouts: return narration text for a bank format ---
    def upi(self, bank, name, vpa, note, mcc, credit, p2p):
        ref, b4 = self.ref(), self.r.choice(BANK4)
        if bank == "federal":
            return f"{'UPI IN' if credit else 'UPIOUT'}/{ref}/{vpa}/{note}/{'0000' if p2p else mcc}"
        return self.r.choice({
            "hdfc": [f"UPI-{name}-{vpa}-{self.ifsc()}-{ref}-{note.upper()}"],
            "sbi": [f"{'BY' if credit else 'TO'} TRANSFER-UPI/{'CR' if credit else 'DR'}/{ref}/{name}/{b4}/{vpa}/{note}--"],
            "icici": [f"UPI/{ref}/{note}/{vpa}/{self.r.choice(BANK_NAMES)}"],
            "axis": [f"UPI/{'P2A' if p2p else 'P2M'}/{ref}/{name}/{note}/{self.r.choice(BANK_NAMES).upper()}"],
            "kotak": [f"UPI/{name}/{ref}/{note}"],
            "canara": [f"UPI/{'CR' if credit else 'DR'}/{ref}/{name}/{b4}/{vpa}/{note}"],
        }[bank])

    def nach(self, bank, name, credit=False, word=""):
        ref = self.d(self.r.choice([8, 10, 12]))
        if credit:
            return self.r.choice([f"ACH C- {name} {word}-{ref}", f"NACH CR {name} {word} {ref}", f"ACH/{name}-{word}/{ref}"]).replace("  ", " ")
        return {
            "hdfc": f"ACH D- {name}-{self.r.choice(['', 'CITI', 'UTIB', 'ICIC'])}{ref}",
            "sbi": f"DEBIT-ACHDr {self.r.choice(BANK4)}{ref} {name}",
            "icici": f"ACH/{name}/{self.r.choice(BANK4)}{ref}",
            "axis": f"NACH-DR- {name}-{ref}",
            "kotak": f"NACH DR {ref} {name}",
            "canara": f"NACH DR {name} {ref}",
            "federal": f"ACH DR/{name}/{ref}",
        }[bank]

    def neft(self, bank, name, note, credit):
        utr, ifsc = self.r.choice(BANK4) + "N" + self.d(10), self.ifsc()
        if credit:
            return {
                "hdfc": f"NEFT CR-{ifsc}-{name}-{note}-{utr}",
                "sbi": f"BY TRANSFER-NEFT*{ifsc}*{utr}*{note} {name}--",
                "icici": f"NEFT/{utr}/{note}/{name}",
                "axis": f"NEFT-{utr}-{name}-{note}",
                "kotak": f"NEFT {utr} {name} {note}",
                "canara": f"NEFT CR {utr} {name} {note}",
                "federal": f"NFT/{name[:15]}/{utr}/{self.r.choice(BANK_NAMES).upper()[:10]}",
            }[bank]
        return {
            "hdfc": f"NEFT DR-{ifsc}-{name}-{note}",
            "sbi": f"TO TRANSFER-NEFT*{ifsc}*{utr}*{name} {note}--",
            "icici": f"NEFT/{utr}/{name}/{note}",
            "axis": f"NEFT/DR/{utr}/{name}",
            "kotak": f"NEFT DR {utr} {name}",
            "canara": f"NEFT/DR/{utr}/{name}/{note}",
            "federal": f"TO NEFT/{utr}/{name[:15]}",
        }[bank]

    def imps(self, bank, name, note, credit):
        ref = self.ref()
        return self.r.choice([f"IMPS/P2A/{ref}/{name}/{self.r.choice(BANK_NAMES)}/{note}",
                              f"IMPS-{ref}-{name}-{self.r.choice(BANK4)}-{note}",
                              f"{'BY' if credit else 'TO'} TRANSFER-IMPS/{ref}/{name}--"])

    def card_txn(self, bank, name, online):
        c = self.card()
        city = self.r.choice(CITIES)
        if bank == "federal":
            return f"TO {'ECM' if online else 'POS'}/{self.ref()}/{name} \\{city if not online else name.split()[0]}"
        return self.r.choice({
            "hdfc": [f"POS {c} {name} {city}", f"ME DC SI {c} {name}"],
            "sbi": [f"POS ATM PURCH OTHPG {self.ref()} {name}", f"BY DEBIT CARD-OTHPG {self.ref()} {name}"],
            "icici": [f"MPS/{name}/{self.ref()}/{city}", f"POS/{c}/{name}"],
            "axis": [f"ECOM PUR-{c}-{name}", f"POS/{c}/{name}/{city}"],
            "kotak": [f"PCD/{c}/{name}/{city}"],
            "canara": [f"POS-{c}-{name}-{city}"],
        }[bank])

    def atm(self, bank):
        c, t = self.card(), self.r.choice(["S1BW", "S1CN", "SPCNH", "S1AN", "DBTM"]) + self.d(4)
        area, city = self.r.choice(AREAS), self.r.choice(CITIES)
        return {
            "hdfc": f"NWD-{c}-{t}-{city}",
            "sbi": f"ATM WDL-ATM CASH {self.d(4)} {area} {city}",
            "icici": f"ATM/CASH WDL/{t}/{city}",
            "axis": f"ATM-WDL/{self.d(6)}/{area}",
            "kotak": f"CASH WDL {self.d(6)} {area}",
            "canara": f"ATW-{c}-{t}-{city}",
            "federal": f"TO ATM/{self.d(4)}/FBL-{area}\\{self.r.choice(['MAIN ROAD', 'METRO STN', 'BUS STAND', city])}",
        }[bank]

    # --- one labelled row for a category ---
    def row(self, cat):
        r, bank = self.r, self.r.choice(BANKS)
        out = dict(direction="debit", category=cat, merchant=None, channel="UPI", upi_type=None)
        if cat in MERCHANTS:
            mcc, (canon, name, vpa) = self.merchant(cat)
            if cat == "Rent" and r.random() < 0.4:  # rent to a landlord, marked by the note
                pname, handle = self.person()
                canon, name, vpa, mcc = None, pname, handle, "0000"
                out["upi_type"] = "P2P"
            kind = r.choices(["upi", "nach", "card", "qr"], weights=[
                5, 4 if cat in ("Loan EMI", "Insurance", "Investments") else 0,
                2 if cat not in ("Rent", "Loan EMI") else 0,
                2 if cat in ("Food & dining", "Groceries", "Shopping", "Health", "Travel & transport") else 0])[0]
            note = {"Rent": r.choice(["RENT", "Rent", "rent Nov", "HOUSE RENT", "PG RENT"]),
                    "Loan EMI": r.choice(["EMI", "LOAN EMI", "Payment"]),
                    "Credit card payment": r.choice(["CC bill", "Card bill", "CC PAYMENT", "Payment"]),
                    "Insurance": r.choice(["Premium", "Policy", "Renewal", "Payment"])}.get(cat, r.choice(NOTES))
            if kind == "qr":  # name-less merchant QR: only the MCC carries the category
                bank = "federal"
                vpa = r.choice([f"q{self.d(9)}@ybl", f"paytmqr{self.d(6)}@ptys", f"bhqr.{self.d(7)}a@sib", f"9{self.d(9)}@okbizaxis"])
                out.update(merchant=None, upi_type="P2M", category=cat)
                text = f"UPIOUT/{self.ref()}/{vpa}/{r.choice(['Paid via ', 'Paid ', 'Pai', 'Paid v'])}/{mcc}"
            elif kind == "nach":
                out.update(channel="NACH", merchant=canon)
                text = self.nach(bank, name)
            elif kind == "card":
                out.update(channel="CARD", merchant=canon)
                text = self.card_txn(bank, name, online=r.random() < 0.6)
            else:
                out.update(merchant=canon, upi_type=out["upi_type"] or "P2M")
                text = self.upi(bank, name, vpa, note, mcc, credit=False, p2p=out["upi_type"] == "P2P")
            return text, out
        if cat in ("Transfer in", "Transfer out"):
            credit = cat == "Transfer in"
            out["direction"] = "credit" if credit else "debit"
            name, handle = self.person()
            note = r.choice(NOTES + ["dinner split", "trip", "gift", "self", "returning", "share"])
            ch = r.choices(["UPI", "IMPS", "NEFT"], weights=[6, 2, 2])[0]
            out["channel"] = ch
            if ch == "UPI":
                out["upi_type"] = "P2P"
                return self.upi(bank, name, handle, note, "0000", credit, True), out
            return (self.imps(bank, name, note, credit) if ch == "IMPS" else self.neft(bank, name, note.upper(), credit)), out
        if cat == "Salary":
            out["direction"] = "credit"
            company = self.fake.company().upper().replace(",", "").replace(".", "")
            out["merchant"] = " ".join(w.capitalize() for w in company.replace(" PVT LTD", "").replace(" LTD", "").replace(" PRIVATE LIMITED", "").split())
            out["channel"] = r.choices(["NEFT", "IMPS", "RTGS"], weights=[7, 2, 1])[0]
            word = r.choice(["SALARY", "SAL", "SALARY NOV 2026", "SAL OCT26", "STIPEND", "SALARY CREDIT"])
            if bank == "federal":  # Federal's NFT layout drops the payer note, so it can't show a salary word
                bank = r.choice(BANKS[:-1])
            text = self.neft(bank, company, word, True) if out["channel"] != "IMPS" else f"IMPS/P2A/{self.ref()}/{company}/{word}"
            if out["channel"] == "RTGS":
                text = f"RTGS CR-{self.ifsc()}-{company}-{word}"
            return text, out
        if cat == "Refund & cashback":
            out["direction"] = "credit"
            if r.random() < 0.35:
                canon, name, vpa = r.choice(CASHBACK)
                out.update(merchant=canon, upi_type="P2M")
                return self.upi(bank, name, vpa, r.choice(["Cashback", "Reward", "CASHBACK"]), "0000", True, False), out
            src = r.choice(["Shopping", "Food & dining", "Travel & transport", "Entertainment & subscriptions"])
            _, (canon, name, vpa) = self.merchant(src)
            out["merchant"] = canon
            style = r.choice(["upi", "rev", "card"])
            if style == "card":
                out.update(channel="CARD")
                return f"{r.choice(['ECOM REF', 'POS REF', 'REFUND'])}-{self.card()}-{name}", out
            out["upi_type"] = "P2M"
            if style == "rev":
                return r.choice([f"REV-UPI-{self.ref()}-{name}", f"UPI/REV/{self.ref()}/{name}/Reversal/{r.choice(BANK_NAMES).upper()}"]), out
            return self.upi(bank, name, vpa, r.choice(["Refund", "REFUND", "Refund cancellation"]), "0000", True, False), out
        if cat == "Interest & dividend":
            out.update(direction="credit", channel="INTERNAL")
            if r.random() < 0.3:
                canon, name = r.choice(DIVIDEND_PAYERS)
                out.update(merchant=canon, channel="NACH")
                return self.nach(bank, name, credit=True, word=r.choice(["DIV", "DIVIDEND", "FINAL DIV", "INT DIV"])), out
            return r.choice([f"INT.PD:{self.d(14)}:01-0{r.randint(1, 9)}-2026 TO 3{r.randint(0, 1)}-{r.randint(10, 12)}-2026",
                             "CREDIT INTEREST", "SB INT CR", f"INTEREST CREDIT FD {self.d(6)}", f"RD INT CR {self.d(6)}",
                             "CREDIT INTEREST CAPITALISED", f"{self.d(10)}:Int.Pd:01-07-2026 to 30-09-2026", "INT CR SB A/C"]), out
        if cat == "Cash withdrawal":
            out.update(channel="ATM")
            return self.atm(bank), out
        if cat == "Bank charges & penalties":
            out.update(channel="INTERNAL")
            if r.random() < 0.45:  # bounce charges: the signal lenders care about most
                _, (canon, name, _) = self.merchant("Loan EMI")
                named = r.random() < 0.6
                out["merchant"] = canon if named else None
                base = r.choice(["ACH RTN CHRGS", "NACH RTN CHARGES", "ECS RTN CHGS", "CHRG: ACH DEBIT RETURN",
                                 "ECS/ACH RETURN CHARGES", "MANDATE RTN CHG", "CHRG:ECS RTN", "INWARD ECS RETURN CHARGES"])
                return (f"{base} {self.d(6)} {name}" if named else f"{base} {self.d(2)}-{r.randint(10, 12)}-2026"), out
            if r.random() < 0.15:
                out["channel"] = "CARD"
                return f"TO INTL. ECM DCC/{self.ref()}/{r.choice(['GOOGLE', 'APPLE.COM/BILL', 'NETFLIX.COM', 'OPENAI', 'AMAZON WEB SVCS'])}", out
            return r.choice(["SMS CHARGES FOR QTR ENDED SEP26", "GST @18% ON CHGS", "ANNUAL DEBIT CARD FEE INCL GST",
                             f"MIN BAL CHARGES {r.choice(['AUG', 'SEP', 'OCT', 'NOV'])}26", "ATM DECLINE CHARGES", f"CHQ BOOK ISSUE CHGS {self.d(4)}",
                             "DEBIT CARD AMC", f"NON MAINT CHGS {self.d(6)}", "IMPS CHARGES INCL GST"]), out
        if cat == "Other":
            out["channel"] = r.choice(["OTHER", "OTHER", "CHEQUE"])
            if out["channel"] == "CHEQUE":
                text = r.choice([f"CHQ DEP CLG {self.d(6)}", f"CHQ PAID-{self.d(6)}-MICR CLG", f"CLG/{self.d(6)}/CHQ"])
                out["direction"] = "credit" if "DEP" in text else "debit"
                return text, out
            if r.random() < 0.35:  # salons, laundry and other services sit outside the category list
                out.update(channel="UPI", upi_type="P2M", direction="debit")
                return f"UPIOUT/{self.ref()}/q{self.d(9)}@ybl/Paid via /{r.choice(['7210', '7230', '7299', '8299'])}", out
            text = r.choice([f"REV-ADJ {self.d(5)} DISPUTE", f"MISC CR {self.d(8)}", f"SI ADJ DR {self.d(6)}",
                             f"TRF DR ADJ REF {self.d(5)}", f"CASH DEP SELF {self.d(4)}", f"ADJ ENTRY {self.d(6)}"])
            out["direction"] = "credit" if ("CR " in text or "DEP" in text) else r.choice(["debit", "credit"]) if "ADJ ENTRY" in text else "debit"
            return text, out
        raise ValueError(cat)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=24000)
    ap.add_argument("--out", default="data/synthetic/train.csv")
    ap.add_argument("--test", default="data/test/test.csv")
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()

    test = list(csv.DictReader(open(args.test, encoding="utf-8")))
    unseen = {r["merchant"] for r in test if r["unseen_merchant"] == "1" and r["merchant"]}
    test_text = {r["narration"] for r in test}
    g = Gen(args.seed, unseen)

    cats = [c.value for c in Category]
    rows, seen = [], set()
    while len(rows) < args.n:
        cat = cats[len(rows) % len(cats)]  # balanced: macro-F1 weights every category equally
        text, label = g.row(cat)
        text = text.replace(",", " ")
        if text in seen or text in test_text:
            continue
        TransactionLabel(**{k: label[k] for k in ("category", "merchant", "channel", "upi_type")})  # validates
        assert label["merchant"] not in unseen, label["merchant"]
        seen.add(text)
        bank = "synthetic"
        rows.append([text, label["direction"], label["category"], label["merchant"] or "", label["channel"], label["upi_type"] or "", bank, "0"])

    import os
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["narration", "direction", "category", "merchant", "channel", "upi_type", "bank_format", "unseen_merchant"])
        w.writerows(rows)
    print(f"wrote {len(rows)} rows to {args.out}")


if __name__ == "__main__":
    main()
