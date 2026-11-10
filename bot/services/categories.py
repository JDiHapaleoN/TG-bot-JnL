"""Expense and income categories catalog and automatic keyword-based classification."""

from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass(frozen=True)
class CategoryInfo:
    code: str
    tx_type: str  # 'expense' | 'income'
    icon: str
    name_ru: str
    name_en: str
    keywords: Tuple[str, ...]


CATEGORIES: Dict[str, CategoryInfo] = {
    # Expense categories
    "food": CategoryInfo(
        code="food",
        tx_type="expense",
        icon="🍔",
        name_ru="Еда и кафе",
        name_en="Food & Dining",
        keywords=(
            "обед", "ужин", "завтрак", "кофе", "кафе", "ресторан", "мак", "mcdonald",
            "kfc", "burger", "бургер", "пицца", "pizza", "шаурма", "донер", "döner",
            "столовая", "перекус", "круассан", "чай", "суши", "lunch", "dinner",
            "breakfast", "coffee", "cafe", "restaurant",
        ),
    ),
    "groceries": CategoryInfo(
        code="groceries",
        tx_type="expense",
        icon="🛒",
        name_ru="Продукты",
        name_en="Groceries",
        keywords=(
            "продукты", "супермаркет", "магазин", "хлеб", "молоко", "мясо", "фрукты",
            "овощи", "вода", "lidl", "aldi", "rewe", "edeka", "kaufland", "netto",
            "penny", "korzinka", "корзинка", "makro", "пятерочка", "магнит", "перекресток",
            "вкусвилл", "ашан", "groceries", "supermarket", "market",
        ),
    ),
    "transport": CategoryInfo(
        code="transport",
        tx_type="expense",
        icon="🚕",
        name_ru="Транспорт",
        name_en="Transport",
        keywords=(
            "такси", "метро", "автобус", "трамвай", "проезд", "проездной", "бензин",
            "топливо", "заправка", "поезд", "билет", "самолет", "парковка", "uber",
            "bolt", "yandex", "яндекс", "bvg", "db", "bahn", "taxi", "bus", "metro",
            "train", "ticket", "fuel", "gas", "parking",
        ),
    ),
    "housing": CategoryInfo(
        code="housing",
        tx_type="expense",
        icon="🏠",
        name_ru="Жильё и счета",
        name_en="Housing & Bills",
        keywords=(
            "аренда", "квартира", "жилье", "жильё", "коммуналка", "жкх", "свет",
            "электричество", "газ", "отопление", "интернет", "связь", "телефон",
            "мобильный", "страховка", "rent", "apartment", "utilities", "electricity",
            "internet", "phone", "insurance", "wifi",
        ),
    ),
    "shopping": CategoryInfo(
        code="shopping",
        tx_type="expense",
        icon="🛍",
        name_ru="Покупки",
        name_en="Shopping",
        keywords=(
            "одежда", "обувь", "куртка", "кроссовки", "футболка", "джинсы", "техника",
            "дом", "мебель", "косметика", "бытовая", "amazon", "ozon", "озон", "wb",
            "wildberries", "zara", "ikea", "shopping", "clothes", "shoes",
        ),
    ),
    "entertainment": CategoryInfo(
        code="entertainment",
        tx_type="expense",
        icon="🎬",
        name_ru="Развлечения и подписки",
        name_en="Entertainment",
        keywords=(
            "кино", "театр", "концерт", "подписка", "подписки", "netflix", "spotify",
            "youtube", "apple", "telegram", "chatgpt", "игры", "steam", "ps5", "бар",
            "клуб", "отдых", "отпуск", "хобби", "movie", "cinema", "subscription",
            "games", "bar", "party",
        ),
    ),
    "health": CategoryInfo(
        code="health",
        tx_type="expense",
        icon="💊",
        name_ru="Здоровье и спорт",
        name_en="Health & Sport",
        keywords=(
            "аптека", "лекарства", "таблетки", "врач", "доктор", "клиника", "анализы",
            "стоматолог", "зубной", "спортзал", "зал", "фитнес", "абонемент", "тренировка",
            "бассейн", "витамины", "pharmacy", "medicine", "doctor", "dentist", "gym",
            "fitness", "sport", "health",
        ),
    ),
    "education": CategoryInfo(
        code="education",
        tx_type="expense",
        icon="📚",
        name_ru="Образование",
        name_en="Education",
        keywords=(
            "курсы", "курс", "книга", "книги", "учеба", "учёба", "университет",
            "колледж", "школа", "репетитор", "немецкий", "английский", "обучение",
            "course", "book", "books", "study", "university", "tuition", "tutor",
        ),
    ),
    "other": CategoryInfo(
        code="other",
        tx_type="expense",
        icon="📦",
        name_ru="Прочее",
        name_en="Other",
        keywords=(),
    ),
    # Income categories
    "salary": CategoryInfo(
        code="salary",
        tx_type="income",
        icon="💼",
        name_ru="Зарплата",
        name_en="Salary",
        keywords=(
            "зарплата", "зп", "аванс", "оклад", "премия", "бонус", "работа",
            "salary", "wage", "paycheck", "bonus", "work",
        ),
    ),
    "stipend": CategoryInfo(
        code="stipend",
        tx_type="income",
        icon="🎓",
        name_ru="Стипендия",
        name_en="Stipend",
        keywords=("стипендия", "грант", "stipend", "scholarship", "grant"),
    ),
    "freelance": CategoryInfo(
        code="freelance",
        tx_type="income",
        icon="💻",
        name_ru="Фриланс и доход",
        name_en="Freelance & Business",
        keywords=(
            "фриланс", "заказ", "проект", "клиент", "арендный", "дивиденды",
            "инвестиции", "проценты", "freelance", "project", "client", "dividend",
        ),
    ),
    "gift": CategoryInfo(
        code="gift",
        tx_type="income",
        icon="🎁",
        name_ru="Подарок и кэшбэк",
        name_en="Gift & Cashback",
        keywords=(
            "подарок", "перевод", "кэшбэк", "кешбэк", "возврат", "долг",
            "gift", "present", "cashback", "refund", "transfer",
        ),
    ),
    "other_income": CategoryInfo(
        code="other_income",
        tx_type="income",
        icon="💰",
        name_ru="Прочий доход",
        name_en="Other Income",
        keywords=(),
    ),
}

EXPENSE_CATEGORY_CODES: List[str] = [
    "food",
    "groceries",
    "transport",
    "housing",
    "shopping",
    "entertainment",
    "health",
    "education",
    "other",
]

INCOME_CATEGORY_CODES: List[str] = [
    "salary",
    "stipend",
    "freelance",
    "gift",
    "other_income",
]


def detect_category(description: str, tx_type: str = "expense") -> str:
    """Automatically detect category code from transaction description keywords."""
    default_code = "other_income" if tx_type == "income" else "other"
    if not description or not description.strip():
        return default_code

    lower_desc = description.lower()
    codes = INCOME_CATEGORY_CODES if tx_type == "income" else EXPENSE_CATEGORY_CODES

    for code in codes:
        info = CATEGORIES[code]
        for kw in info.keywords:
            if kw in lower_desc:
                return code

    return default_code


def get_category_info(code: str, tx_type: str = "expense") -> CategoryInfo:
    if code in CATEGORIES:
        return CATEGORIES[code]
    fallback = "other_income" if tx_type == "income" else "other"
    return CATEGORIES[fallback]


def get_category_label(code: str, lang: str = "ru", tx_type: str = "expense") -> str:
    info = get_category_info(code, tx_type=tx_type)
    name = info.name_ru if lang == "ru" else info.name_en
    return f"{info.icon} {name}"

