"""Output schema for the transaction categoriser.

Every model (TF-IDF baseline, Gemini few-shot, fine-tuned Qwen) is scored
against this one schema. JSON validity = "parses and validates against
TransactionLabel".
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class Direction(str, Enum):
    DEBIT = "debit"
    CREDIT = "credit"


class Category(str, Enum):
    # Inflows
    SALARY = "Salary"
    REFUND_CASHBACK = "Refund & cashback"
    INTEREST_DIVIDEND = "Interest & dividend"
    TRANSFER_IN = "Transfer in"
    # Obligations (what lenders look at first)
    LOAN_EMI = "Loan EMI"
    CREDIT_CARD_PAYMENT = "Credit card payment"
    RENT = "Rent"
    INSURANCE = "Insurance"
    # Spending
    FOOD_DINING = "Food & dining"
    GROCERIES = "Groceries"
    SHOPPING = "Shopping"
    TRAVEL_TRANSPORT = "Travel & transport"
    BILLS_UTILITIES = "Bills & utilities"
    ENTERTAINMENT_SUBS = "Entertainment & subscriptions"
    HEALTH = "Health"
    # Money movement and bank
    INVESTMENTS = "Investments"
    CASH_WITHDRAWAL = "Cash withdrawal"
    BANK_CHARGES = "Bank charges & penalties"
    TRANSFER_OUT = "Transfer out"
    OTHER = "Other"


class Channel(str, Enum):
    UPI = "UPI"
    NEFT = "NEFT"
    IMPS = "IMPS"
    RTGS = "RTGS"
    NACH = "NACH"  # includes ACH / ECS mandates
    CARD = "CARD"  # POS and online card spends
    ATM = "ATM"
    CHEQUE = "CHEQUE"
    INTERNAL = "INTERNAL"  # interest, charges, bank-initiated entries
    OTHER = "OTHER"


class UpiType(str, Enum):
    P2M = "P2M"
    P2P = "P2P"


class TransactionInput(BaseModel):
    """What the model sees. Direction is on every real statement row."""

    narration: str
    direction: Direction


class TransactionLabel(BaseModel):
    """What the model must output, as JSON."""

    model_config = ConfigDict(extra="forbid")

    category: Category
    merchant: Optional[str] = Field(
        default=None,
        description="Canonical merchant/payee organisation, e.g. 'Swiggy'. "
        "Null for transfers to or from individuals, cash and bank entries.",
    )
    channel: Channel
    upi_type: Optional[UpiType] = Field(
        default=None, description="Only set when channel is UPI."
    )
