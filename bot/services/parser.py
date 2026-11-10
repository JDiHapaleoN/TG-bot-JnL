"""Fast natural-entry transaction parser for Telegram messages with strict validation."""

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Optional

MIN_AMOUNT = Decimal("0.01")
MAX_AMOUNT = Decimal("999999999.99")

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

# Matches:
# - Optional '+' sign (for income). Negative numbers ('-', '−') are rejected as invalid.
# - Optional leading currency symbol
# - Integer or 1-2 decimal place number (not followed by extra digits/dots)
# - Optional trailing currency symbol or 3-letter ISO currency code
# - Optional separator ('|', '—', '-') and description
_TX_PATTERN = re.compile(
    r"^\s*"
    r"(?P<sign>\+)?\s*"
    r"(?P<lead_sym>[€$£₽₺¥₸₴])?\s*"
    r"(?P<number>\d+(?:[.,]\d{1,2})?)"
    r"(?![.,\d])\s*"
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
    Rejects negative numbers (e.g. '-50'), zero ('0'), >2 decimal places ('12.345'),
    and overly large numbers (> 999,999,999.99).
    """
    if not text or not isinstance(text, str) or not text.strip():
        return None

    cleaned = text.strip()
    if cleaned.startswith("/") or cleaned.startswith("-") or cleaned.startswith("−") or cleaned.startswith("–"):
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

    if desc.startswith("|"):
        desc = desc[1:].strip()

    try:
        amount = Decimal(raw_number).quantize(Decimal("0.01"))
    except InvalidOperation:
        return None

    if amount < MIN_AMOUNT or amount > MAX_AMOUNT:
        return None

    if sign == "+":
        tx_type = "income"
    else:
        tx_type = default_type if default_type in ("expense", "income") else "expense"

    sym = lead_sym or trail_sym
    currency_override = SYMBOL_TO_CURRENCY.get(sym) if sym else None

    return ParsedTransaction(
        tx_type=tx_type,
        amount=amount,
        description=desc[:255],
        currency_override=currency_override,
    )
