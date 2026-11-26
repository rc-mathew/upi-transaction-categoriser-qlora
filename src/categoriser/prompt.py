"""The one prompt format the fine-tuned model is trained and served with.

Kept short on purpose: every token is paid for in CPU latency at serving time.
"""
import json

SYSTEM = (
    "Categorise an Indian bank statement line. Reply with JSON only: "
    '{"category", "merchant", "channel", "upi_type"}.'
)


def user_message(narration: str, direction: str) -> str:
    return f"Narration: {narration}\nDirection: {direction}"


def assistant_message(category, merchant, channel, upi_type) -> str:
    return json.dumps(
        {"category": category, "merchant": merchant or None, "channel": channel, "upi_type": upi_type or None},
        ensure_ascii=False,
    )


def chat(row: dict, with_answer: bool = True) -> list[dict]:
    msgs = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": user_message(row["narration"], row["direction"])},
    ]
    if with_answer:
        msgs.append({"role": "assistant", "content": assistant_message(
            row["category"], row["merchant"], row["channel"], row["upi_type"])})
    return msgs
