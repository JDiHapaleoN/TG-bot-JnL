"""ISO 4217 currency catalog and money formatting utilities."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, List, Optional


@dataclass(frozen=True)
class CurrencyInfo:
    code: str
    symbol: str
    name_en: str
    name_ru: str
    symbol_prefix: bool = True


CURRENCIES: Dict[str, CurrencyInfo] = {
    "EUR": CurrencyInfo("EUR", "€", "Euro", "Евро", True),
    "USD": CurrencyInfo("USD", "$", "US Dollar", "Доллар США", True),
    "UZS": CurrencyInfo("UZS", "UZS", "Uzbekistani Som", "Узбекский сум", False),
    "RUB": CurrencyInfo("RUB", "₽", "Russian Ruble", "Российский рубль", False),
    "GBP": CurrencyInfo("GBP", "£", "British Pound", "Фунт стерлингов", True),
    "CHF": CurrencyInfo("CHF", "CHF", "Swiss Franc", "Швейцарский франк", True),
    "TRY": CurrencyInfo("TRY", "₺", "Turkish Lira", "Турецкая лира", True),
    "CNY": CurrencyInfo("CNY", "¥", "Chinese Yuan", "Китайский юань", True),
    "JPY": CurrencyInfo("JPY", "¥", "Japanese Yen", "Японская иена", True),
    "KZT": CurrencyInfo("KZT", "₸", "Kazakhstani Tenge", "Казахстанский тенге", False),
    "UAH": CurrencyInfo("UAH", "₴", "Ukrainian Hryvnia", "Украинская гривна", False),
    "BYN": CurrencyInfo("BYN", "Br", "Belarusian Ruble", "Белорусский рубль", False),
    "PLN": CurrencyInfo("PLN", "zł", "Polish Zloty", "Польский злотый", False),
    "CZK": CurrencyInfo("CZK", "Kč", "Czech Koruna", "Чешская крона", False),
    "AED": CurrencyInfo("AED", "AED", "UAE Dirham", "Дирхам ОАЭ", False),
    "CAD": CurrencyInfo("CAD", "CA$", "Canadian Dollar", "Канадский доллар", True),
    "AUD": CurrencyInfo("AUD", "A$", "Australian Dollar", "Австралийский доллар", True),
    "GEL": CurrencyInfo("GEL", "₾", "Georgian Lari", "Грузинский лари", False),
    "AMD": CurrencyInfo("AMD", "֏", "Armenian Dram", "Армянский драм", False),
    "AZN": CurrencyInfo("AZN", "₼", "Azerbaijani Manat", "Азербайджанский манат", False),
    "KGS": CurrencyInfo("KGS", "сом", "Kyrgyzstani Som", "Кыргызский сом", False),
    "TJS": CurrencyInfo("TJS", "SM", "Tajikistani Somoni", "Таджикский сомони", False),
    "INR": CurrencyInfo("INR", "₹", "Indian Rupee", "Индийская рупия", True),
    "KRW": CurrencyInfo("KRW", "₩", "South Korean Won", "Южнокорейская вона", True),
    "SGD": CurrencyInfo("SGD", "S$", "Singapore Dollar", "Сингапурский доллар", True),
    "HKD": CurrencyInfo("HKD", "HK$", "Hong Kong Dollar", "Гонконгский доллар", True),
    "THB": CurrencyInfo("THB", "฿", "Thai Baht", "Тайский бат", True),
    "ILS": CurrencyInfo("ILS", "₪", "Israeli New Shekel", "Израильский шекель", True),
    "BRL": CurrencyInfo("BRL", "R$", "Brazilian Real", "Бразильский реал", True),
    "MXN": CurrencyInfo("MXN", "MX$", "Mexican Peso", "Мексиканское песо", True),
    "SEK": CurrencyInfo("SEK", "kr", "Swedish Krona", "Шведская крона", False),
    "NOK": CurrencyInfo("NOK", "kr", "Norwegian Krone", "Норвежская крона", False),
    "DKK": CurrencyInfo("DKK", "kr", "Danish Krone", "Датская крона", False),
}

# Featured currencies shown on the first screen of currency picker (matching spec Section 5)
FEATURED_CURRENCY_CODES: List[str] = [
    "EUR",
    "USD",
    "UZS",
    "RUB",
    "GBP",
    "CHF",
    "TRY",
    "CNY",
    "JPY",
    "KZT",
    "UAH",
    "AED",
]

# All valid ISO 4217 3-letter currency codes for manual input validation
ALL_ISO_4217_CODES = set(CURRENCIES.keys()) | {
    "AFN", "ALL", "AOA", "ARS", "AWG", "BAM", "BBD", "BDT", "BGN", "BHD",
    "BIF", "BMD", "BND", "BOB", "BSD", "BTN", "BWP", "BZD", "CDF", "CLP",
    "COP", "CRC", "CUP", "CVE", "DJF", "DOP", "DZD", "EGP", "ERN", "ETB",
    "FJD", "FKP", "GMD", "GNF", "GTQ", "GYD", "HNL", "HTG", "HUF", "IDR",
    "IQD", "IRR", "ISK", "JMD", "JOD", "KES", "Khr", "KMF", "KPW", "KWD",
    "KYD", "LAK", "LBP", "LKR", "LRD", "LSL", "LYD", "MAD", "MDL", "MGA",
    "MKD", "MMK", "MNT", "MOP", "MRU", "MUR", "MVR", "MWK", "MYR", "MZN",
    "NAD", "NGN", "NIO", "NPR", "NZD", "OMR", "PAB", "PEN", "PGK", "PHP",
    "PKR", "PYG", "QAR", "RON", "RSD", "RWF", "SAR", "SBD", "SCR", "SDG",
    "SHP", "SLE", "SOS", "SRD", "SSP", "STN", "SYP", "SZL", "TMT", "TND",
    "TOP", "TTD", "TWD", "TZS", "UGX", "UYU", "VES", "VND", "VUV", "WST",
    "XAF", "XCD", "XOF", "XPF", "YER", "ZAR", "ZMW",
}


def get_currency_info(code: str) -> CurrencyInfo:
    code_up = (code or "EUR").upper().strip()
    if code_up in CURRENCIES:
        return CURRENCIES[code_up]
    return CurrencyInfo(code_up, code_up, code_up, code_up, False)


def is_valid_currency(code: str) -> bool:
    if not code:
        return False
    code_up = code.upper().strip()
    return len(code_up) == 3 and code_up.isalpha() and code_up in ALL_ISO_4217_CODES


def format_money(
    amount: Decimal | float | int | str,
    currency_code: str = "EUR",
    tx_type: Optional[str] = None,
    signed: bool = False,
) -> str:
    """
    Format an amount according to the specification:
    - Balance: '€1,245.50' or '− €50.00'
    - Expense (tx_type='expense'): '− €5.00'
    - Income (tx_type='income'): '+ €2,000.00'
    """
    dec = Decimal(str(amount)).quantize(Decimal("0.01"))
    abs_dec = abs(dec)
    info = get_currency_info(currency_code)

    formatted_num = f"{abs_dec:,.2f}"
    if info.symbol_prefix:
        spacer = " " if len(info.symbol) > 1 and info.symbol.isalpha() else ""
        base_str = f"{info.symbol}{spacer}{formatted_num}"
    else:
        base_str = f"{formatted_num} {info.symbol}"

    if tx_type == "expense":
        return f"− {base_str}"
    if tx_type == "income":
        return f"+ {base_str}"

    if dec < 0:
        return f"− {base_str}"
    if signed and dec > 0:
        return f"+ {base_str}"
    return base_str


def get_currency_label(code: str, lang: str = "ru") -> str:
    info = get_currency_info(code)
    name = info.name_ru if lang == "ru" else info.name_en
    return f"{info.code} — {name} ({info.symbol})"

