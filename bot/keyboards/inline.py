"""Reply and Inline keyboards for all bot workflows."""

import calendar
from datetime import date, timedelta
from typing import List, Optional

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    WebAppInfo,
)

from bot.config import settings
from bot.database.models import RecurringTransaction, Transaction
from bot.i18n.translations import t
from bot.services.categories import (
    CATEGORIES,
    EXPENSE_CATEGORY_CODES,
    INCOME_CATEGORY_CODES,
)
from bot.services.currencies import CURRENCIES, FEATURED_CURRENCY_CODES, format_money
from bot.services.geo import COUNTRIES, POPULAR_TIMEZONES


def persistent_reply_kb(lang: str = "ru") -> ReplyKeyboardMarkup:
    """Persistent bottom Reply Keyboard for 1-tap navigation from any chat screen."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=t("kb_expense", lang)),
                KeyboardButton(text=t("kb_income", lang)),
            ],
            [
                KeyboardButton(text=t("kb_stats", lang)),
                KeyboardButton(text=t("kb_history", lang)),
            ],
            [
                KeyboardButton(text=t("kb_menu", lang)),
                KeyboardButton(text=t("kb_profile", lang)),
            ],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def language_select_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🇷🇺 Русский", callback_data="reg:lang:ru"),
                InlineKeyboardButton(text="🇬🇧 English", callback_data="reg:lang:en"),
            ]
        ]
    )


def suggested_name_kb(suggested_name: str) -> ReplyKeyboardMarkup:
    clean_name = (suggested_name or "User").strip()[:60]
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=clean_name)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def contact_request_kb(lang: str = "ru") -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t("btn_share_contact", lang), request_contact=True)],
            [KeyboardButton(text=t("btn_skip_phone", lang))],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def location_request_kb(lang: str = "ru") -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t("btn_share_location", lang), request_location=True)],
            [KeyboardButton(text=t("btn_choose_country_manual", lang))],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def reg_confirm_kb(lang: str = "ru") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t("btn_confirm_reg", lang), callback_data="reg:confirm")],
            [
                InlineKeyboardButton(text=t("btn_change_country", lang), callback_data="reg:edit_country"),
                InlineKeyboardButton(text=t("btn_change_currency", lang), callback_data="reg:edit_currency"),
            ],
            [
                InlineKeyboardButton(text=t("btn_change_tz", lang), callback_data="reg:edit_tz"),
            ],
        ]
    )


def country_picker_kb(prefix: str = "reg:country", lang: str = "ru", back_cb: Optional[str] = None) -> InlineKeyboardMarkup:
    rows: List[List[InlineKeyboardButton]] = []
    featured_codes = [
        "DE", "UZ", "RU", "US", "GB", "CH",
        "TR", "CN", "JP", "KZ", "UA", "BY",
        "PL", "FR", "IT", "ES", "AE", "GE",
    ]
    row: List[InlineKeyboardButton] = []
    for code in featured_codes:
        c = COUNTRIES[code]
        label = f"{c.flag} {c.name_ru if lang == 'ru' else c.name_en}"
        row.append(InlineKeyboardButton(text=label, callback_data=f"{prefix}:{code}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)

    if back_cb:
        rows.append([InlineKeyboardButton(text=t("btn_cancel", lang), callback_data=back_cb)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def currency_picker_kb(prefix: str = "reg:currency", lang: str = "ru", back_cb: Optional[str] = None) -> InlineKeyboardMarkup:
    rows: List[List[InlineKeyboardButton]] = []
    row: List[InlineKeyboardButton] = []
    for code in FEATURED_CURRENCY_CODES:
        info = CURRENCIES[code]
        label = f"{info.code} ({info.symbol})"
        row.append(InlineKeyboardButton(text=label, callback_data=f"{prefix}:{code}"))
        if len(row) == 3:
            rows.append(row)
            row = []
    if row:
        rows.append(row)

    if back_cb:
        rows.append([InlineKeyboardButton(text=t("btn_cancel", lang), callback_data=back_cb)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def timezone_picker_kb(prefix: str = "reg:tz", lang: str = "ru", back_cb: Optional[str] = None) -> InlineKeyboardMarkup:
    rows: List[List[InlineKeyboardButton]] = []
    row: List[InlineKeyboardButton] = []
    for tz_name in POPULAR_TIMEZONES:
        short_label = tz_name.split("/")[-1].replace("_", " ")
        row.append(InlineKeyboardButton(text=f"🕒 {short_label}", callback_data=f"{prefix}:{tz_name}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)

    if back_cb:
        rows.append([InlineKeyboardButton(text=t("btn_cancel", lang), callback_data=back_cb)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def main_menu_kb(lang: str = "ru", telegram_id: Optional[int] = None) -> InlineKeyboardMarkup:
    rows: List[List[InlineKeyboardButton]] = [
        [
            InlineKeyboardButton(text=t("btn_add_expense", lang), callback_data="menu:add_expense"),
            InlineKeyboardButton(text=t("btn_add_income", lang), callback_data="menu:add_income"),
        ],
        [
            InlineKeyboardButton(text=t("btn_stats", lang), callback_data="menu:stats"),
            InlineKeyboardButton(text=t("btn_history", lang), callback_data="menu:history:0"),
        ],
        [
            InlineKeyboardButton(text=t("btn_recurring", lang), callback_data="menu:recurring"),
        ],
        [
            InlineKeyboardButton(text=t("btn_profile", lang), callback_data="menu:profile"),
        ],
    ]

    if settings.webapp_url and settings.webapp_url.startswith("https://"):
        url = settings.webapp_url.rstrip("/")
        rows.append(
            [
                InlineKeyboardButton(
                    text=t("btn_webapp", lang),
                    web_app=WebAppInfo(url=url),
                )
            ]
        )

    return InlineKeyboardMarkup(inline_keyboard=rows)


def back_to_menu_kb(lang: str = "ru") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t("btn_back_menu", lang), callback_data="menu:home")]
        ]
    )


def tx_saved_kb(tx_id: int, lang: str = "ru") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=t("btn_change_cat", lang), callback_data=f"tx:cat:{tx_id}"),
                InlineKeyboardButton(text=t("btn_edit_tx", lang), callback_data=f"tx:edit:{tx_id}"),
                InlineKeyboardButton(text=t("btn_delete_tx", lang), callback_data=f"tx:del:{tx_id}"),
            ],
            [
                InlineKeyboardButton(text=t("btn_back_menu", lang), callback_data="menu:home"),
            ],
        ]
    )


def category_picker_kb(tx_id: int, tx_type: str = "expense", lang: str = "ru") -> InlineKeyboardMarkup:
    codes = INCOME_CATEGORY_CODES if tx_type == "income" else EXPENSE_CATEGORY_CODES
    rows: List[List[InlineKeyboardButton]] = []
    row: List[InlineKeyboardButton] = []
    for code in codes:
        info = CATEGORIES[code]
        name = info.name_ru if lang == "ru" else info.name_en
        row.append(
            InlineKeyboardButton(
                text=f"{info.icon} {name}",
                callback_data=f"tx:setcat:{tx_id}:{code}",
            )
        )
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton(text=t("btn_back_menu", lang), callback_data="menu:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def history_list_kb(
    txs: List[Transaction],
    offset: int,
    total: int,
    limit: int = 6,
    lang: str = "ru",
) -> InlineKeyboardMarkup:
    rows: List[List[InlineKeyboardButton]] = []

    for tx in txs:
        icon = "📉" if tx.tx_type == "expense" else "📈"
        amt_str = format_money(tx.amount, tx.currency, tx_type=tx.tx_type)
        desc = tx.description or (
            t("no_description_expense", lang)
            if tx.tx_type == "expense"
            else t("no_description_income", lang)
        )
        short_desc = desc[:20] + ("…" if len(desc) > 20 else "")
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{icon} {amt_str} — {short_desc}",
                    callback_data=f"tx:view:{tx.id}:{offset}",
                )
            ]
        )

    nav_row: List[InlineKeyboardButton] = []
    if offset > 0:
        prev_off = max(0, offset - limit)
        nav_row.append(InlineKeyboardButton(text="⬅️", callback_data=f"menu:history:{prev_off}"))
    if offset + limit < total:
        next_off = offset + limit
        nav_row.append(InlineKeyboardButton(text="➡️", callback_data=f"menu:history:{next_off}"))
    if nav_row:
        rows.append(nav_row)

    rows.append([InlineKeyboardButton(text=t("btn_back_menu", lang), callback_data="menu:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def tx_detail_kb(tx_id: int, offset: int = 0, lang: str = "ru") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=t("btn_change_cat", lang), callback_data=f"tx:cat:{tx_id}"),
                InlineKeyboardButton(text=t("btn_edit_tx", lang), callback_data=f"tx:edit:{tx_id}"),
                InlineKeyboardButton(text=t("btn_delete_tx", lang), callback_data=f"tx:del:{tx_id}"),
            ],
            [
                InlineKeyboardButton(
                    text=t("btn_back_history", lang), callback_data=f"menu:history:{offset}"
                ),
                InlineKeyboardButton(text=t("btn_back_menu", lang), callback_data="menu:home"),
            ],
        ]
    )


def recurring_menu_kb(items: List[RecurringTransaction], lang: str = "ru") -> InlineKeyboardMarkup:
    rows: List[List[InlineKeyboardButton]] = []
    for rec in items:
        status_icon = "✅" if rec.is_active else "⏸"
        type_icon = "📉" if rec.tx_type == "expense" else "📈"
        amt_str = format_money(rec.amount, rec.currency, tx_type=rec.tx_type)
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{status_icon} {type_icon} {rec.title} ({amt_str})",
                    callback_data=f"rec:view:{rec.id}",
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(text=t("btn_add_rec_expense", lang), callback_data="rec:add:expense"),
            InlineKeyboardButton(text=t("btn_add_rec_income", lang), callback_data="rec:add:income"),
        ]
    )
    rows.append([InlineKeyboardButton(text=t("btn_back_menu", lang), callback_data="menu:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def recurring_presets_kb(tx_type: str, lang: str = "ru") -> InlineKeyboardMarkup:
    if tx_type == "income":
        presets = (
            ["Зарплата", "Стипендия", "Арендный доход"]
            if lang == "ru"
            else ["Salary", "Stipend", "Rental Income"]
        )
    else:
        presets = (
            ["Аренда квартиры", "Интернет", "Подписки", "Страховка", "Абонемент в спортзал"]
            if lang == "ru"
            else ["Apartment Rent", "Internet", "Subscriptions", "Insurance", "Gym Membership"]
        )

    rows: List[List[InlineKeyboardButton]] = []
    for p in presets:
        rows.append([InlineKeyboardButton(text=p, callback_data=f"rec:preset:{p}")])
    rows.append([InlineKeyboardButton(text=t("btn_cancel", lang), callback_data="menu:recurring")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def recurring_period_kb(lang: str = "ru") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=t("period_daily", lang), callback_data="rec:period:daily"),
                InlineKeyboardButton(text=t("period_weekly", lang), callback_data="rec:period:weekly"),
            ],
            [
                InlineKeyboardButton(text=t("period_monthly", lang), callback_data="rec:period:monthly"),
                InlineKeyboardButton(text=t("period_yearly", lang), callback_data="rec:period:yearly"),
            ],
            [InlineKeyboardButton(text=t("btn_cancel", lang), callback_data="menu:recurring")],
        ]
    )


def recurring_date_kb(today_local: date, lang: str = "ru") -> InlineKeyboardMarkup:
    tomorrow = today_local + timedelta(days=1)
    year = today_local.year + (today_local.month // 12)
    month = (today_local.month % 12) + 1
    first_next_month = date(year, month, 1)

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t("btn_date_today", lang, date=today_local.strftime("%d.%m.%Y")),
                    callback_data=f"rec:date:{today_local.isoformat()}",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t("btn_date_tomorrow", lang, date=tomorrow.strftime("%d.%m.%Y")),
                    callback_data=f"rec:date:{tomorrow.isoformat()}",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t(
                        "btn_date_next_month",
                        lang,
                        date=first_next_month.strftime("%d.%m.%Y"),
                    ),
                    callback_data=f"rec:date:{first_next_month.isoformat()}",
                )
            ],
            [InlineKeyboardButton(text=t("btn_cancel", lang), callback_data="menu:recurring")],
        ]
    )


def recurring_detail_kb(rec_id: int, lang: str = "ru") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=t("btn_toggle_rec", lang), callback_data=f"rec:toggle:{rec_id}"),
                InlineKeyboardButton(text=t("btn_delete_rec", lang), callback_data=f"rec:del:{rec_id}"),
            ],
            [
                InlineKeyboardButton(text="⬅️", callback_data="menu:recurring"),
                InlineKeyboardButton(text=t("btn_back_menu", lang), callback_data="menu:home"),
            ],
        ]
    )


def profile_settings_kb(lang: str = "ru") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=t("btn_edit_name", lang), callback_data="prof:edit:name"),
                InlineKeyboardButton(text=t("btn_edit_phone", lang), callback_data="prof:edit:phone"),
            ],
            [
                InlineKeyboardButton(text=t("btn_edit_country", lang), callback_data="prof:edit:country"),
                InlineKeyboardButton(text=t("btn_edit_currency", lang), callback_data="prof:edit:currency"),
            ],
            [
                InlineKeyboardButton(text=t("btn_edit_tz", lang), callback_data="prof:edit:tz"),
                InlineKeyboardButton(text=t("btn_edit_lang", lang), callback_data="prof:toggle:lang"),
            ],
            [
                InlineKeyboardButton(
                    text=t("btn_toggle_notify_rec", lang), callback_data="prof:toggle:notify_rec"
                ),
                InlineKeyboardButton(
                    text=t("btn_toggle_daily_rem", lang), callback_data="prof:toggle:daily_rem"
                ),
            ],
            [
                InlineKeyboardButton(text=t("btn_recurring", lang), callback_data="menu:recurring"),
                InlineKeyboardButton(text=t("btn_export_csv", lang), callback_data="prof:export_csv"),
            ],
            [
                InlineKeyboardButton(
                    text=t("btn_delete_account", lang), callback_data="prof:delete_confirm"
                ),
            ],
            [
                InlineKeyboardButton(text=t("btn_back_menu", lang), callback_data="menu:home"),
            ],
        ]
    )


def confirm_delete_account_kb(lang: str = "ru") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t("btn_confirm_delete_yes", lang), callback_data="prof:delete_execute"
                )
            ],
            [
                InlineKeyboardButton(
                    text=t("btn_confirm_delete_no", lang), callback_data="menu:profile"
                )
            ],
        ]
    )

