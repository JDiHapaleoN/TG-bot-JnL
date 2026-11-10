"""Fast natural-entry transaction parser for Telegram messages."""

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Optional

SYMBOL_TO_CURRENCY = {
    "€": "EUR",
    "$": "USD",
    "£": "GBP",
    "₽": "RUB",
    "₺": "TRY",
    "¥": "JPY",
    "₸": "KZT",
    "₴": "UAH",
}

# Regex matching:
# 1. Optional sign: +, -, −, –
# 2. Optional leading currency symbol: €, $, £, ₽, ₺, ¥, ₸, ₴
# 3. Numeric amount: digits with optional decimal part (. or ,)
# 4. Optional trailing currency symbol
# 5. Optional separator (|, —, -, spaces) and description
_TX_PATTERN = re.compile(
    r"^\s*"
    r"(?P<sign>[+\-−–])?\s*"
    r"(?P<lead_sym>[€$£₽₺¥₸₴])?\s*"
    r"(?P<number>\d+(?:[.,]\d{1,2})?)\s*"
    r"(?P<trail_sym>[€$£₽₺¥₸₴])?"
    r"(?:\s*(?:\||—|--|-)\s*(?P<pipe_desc>.*)|\s+(?P<space_desc>.*))?"
    r"\s*$",
    re.DOTALL,
)


@dataclass(frozen=True)
class ParsedTransaction:
    tx_type: str  # 'expense' | 'income'
    amount: Decimal
    description: str
    currency_override: Optional[str] = None


def parse_transaction_message(
    text: str,
    default_type: str = "expense",
) -> Optional[ParsedTransaction]:
    """
    Parse a quick transaction message such as:
      - '5' -> Expense 5.00
      - '12.50' or '12,50' -> Expense 12.50
      - '+1500' -> Income 1500.00
      - '5 | Обед в McDonald's' -> Expense 5.00, description="Обед в McDonald's"
      - '5 Обед' -> Expense 5.00, description="Обед"
      - '+200 Стипендия' -> Income 200.00, description="Стипендия"
    Returns None if the text is not a valid transaction entry.
    """
    if not text or not text.strip():
        return None

    cleaned = text.strip()
    if cleaned.startswith("/"):
        return None

    match = _TX_PATTERN.match(cleaned)
    if not match:
        return None

    sign = match.group("sign")
    lead_sym = match.group("lead_sym")
    trail_sym = match.group("trail_sym")
    raw_number = match.group("number").replace(",", ".")
    desc = match.group("pipe_desc")
    if desc is None:
        desc = match.group("space_desc") or ""
    desc = desc.strip()

    # If the description starts with "|", strip it cleanly
    if desc.startswith("|"):
        desc = desc[1:].strip()

    try:
        amount = Decimal(raw_number).quantize(Decimal("0.01"))
    except InvalidOperation:
        return None

    if amount <= Decimal("0.00") or amount > Decimal("999999999.99"):
        return None

    if sign == "+":
        tx_type = "income"
    elif sign in ("-", "−", "–"):
        tx_type = "expense"
    else:
        tx_type = default_type if default_type in ("expense", "income") else "expense"

    sym = lead_sym or trail_sym
    currency_override = SYMBOL_TO_CURRENCY.get(sym) if sym else None

    return ParsedTransaction(
        tx_type=tx_type,
        amount=amount,
        description=desc,
        currency_override=currency_override,
    )

