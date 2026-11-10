"""Registration and /start command handlers with existing-profile protection."""

from typing import Any, Dict, Optional

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove

from bot.database.crud import (
    create_or_update_user,
    get_user_by_telegram_id,
    update_user_fields,
)
from bot.database.session import async_session_factory
from bot.handlers.menu import (
    EXPENSE_BTN_TEXTS,
    HISTORY_BTN_TEXTS,
    INCOME_BTN_TEXTS,
    MENU_BTN_TEXTS,
    PROFILE_BTN_TEXTS,
    STATS_BTN_TEXTS,
    build_main_menu_payload,
)
from bot.i18n.translations import t
from bot.keyboards.inline import (
    contact_request_kb,
    country_picker_kb,
    currency_picker_kb,
    language_select_kb,
    location_request_kb,
    persistent_reply_kb,
    reg_confirm_kb,
    safe_edit_text,
    suggested_name_kb,
    timezone_picker_kb,
)
from bot.services.currencies import get_currency_info, get_currency_label, is_valid_currency
from bot.services.geo import (
    format_timezone_with_offset,
    get_country_name,
    get_country_profile,
    is_valid_timezone,
    resolve_location_offline,
)
from bot.states.forms import RegistrationStates

router = Router(name="start")

ALL_NAV_TEXTS = (
    MENU_BTN_TEXTS
    | EXPENSE_BTN_TEXTS
    | INCOME_BTN_TEXTS
    | STATS_BTN_TEXTS
    | HISTORY_BTN_TEXTS
    | PROFILE_BTN_TEXTS
)


async def _ensure_reg_state_data(
    state: FSMContext,
    telegram_id: int,
    full_name: Optional[str] = None,
    lang_code: Optional[str] = None,
) -> Dict[str, Any]:
    """Ensure registration FSM state has valid profile fields even if state was cleared."""
    data = await state.get_data()
    if data.get("country_code") and data.get("currency") and data.get("timezone"):
        return data

    async with async_session_factory() as session:
        existing = await get_user_by_telegram_id(session, telegram_id)
        if existing:
            defaults = {
                "language": data.get("language") or existing.language or "ru",
                "name": data.get("name") or existing.name or full_name or "User",
                "phone": data.get("phone") if "phone" in data else existing.phone,
                "country_code": data.get("country_code") or existing.country_code or "DE",
                "currency": data.get("currency") or existing.currency or "EUR",
                "timezone": data.get("timezone") or existing.timezone or "Europe/Berlin",
            }
            await state.update_data(**defaults)
            return await state.get_data()

    tg_lang = "en" if (lang_code or "").startswith("en") else "ru"
    defaults = {
        "language": data.get("language") or tg_lang,
        "name": data.get("name") or full_name or "User",
        "phone": data.get("phone"),
        "country_code": data.get("country_code") or "DE",
        "currency": data.get("currency") or "EUR",
        "timezone": data.get("timezone") or "Europe/Berlin",
    }
    await state.update_data(**defaults)
    return await state.get_data()


async def start_registration_flow(message: Message, state: FSMContext) -> None:
    await state.clear()
    tg_lang = "en" if (message.from_user.language_code or "").startswith("en") else "ru"
    await state.update_data(
        language=tg_lang,
        name=message.from_user.full_name or "User",
        phone=None,
        country_code="DE",
        currency="EUR",
        timezone="Europe/Berlin",
        user_modified_reg=True,
    )
    await state.set_state(RegistrationStates.language)
    await message.answer(
        t("welcome_start", tg_lang),
        reply_markup=language_select_kb(),
        parse_mode="HTML",
    )


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, message.from_user.id)
        if user and user.is_registered:
            await state.clear()
            text, kb = await build_main_menu_payload(session, user)
            await message.answer(
                "👋",
                reply_markup=persistent_reply_kb(user.language),
            )
            await message.answer(
                text,
                reply_markup=kb,
                parse_mode="HTML",
            )
            return

    await start_registration_flow(message, state)


@router.callback_query(F.data.startswith("reg:lang:"))
async def cb_reg_language(callback: CallbackQuery, state: FSMContext) -> None:
    lang = callback.data.split(":")[-1]
    cur_state = await state.get_state()

    async with async_session_factory() as session:
        existing_user = await get_user_by_telegram_id(session, callback.from_user.id)
        if (
            existing_user
            and existing_user.is_registered
            and cur_state != RegistrationStates.language.state
        ):
            user = await update_user_fields(session, callback.from_user.id, language=lang)
            await state.clear()
            await callback.message.answer(
                "🌐",
                reply_markup=persistent_reply_kb(lang),
            )
            menu_text, menu_kb = await build_main_menu_payload(session, user)
            await safe_edit_text(callback.message, menu_text, reply_markup=menu_kb)
            await callback.answer(t("profile_updated", lang))
            return

    await _ensure_reg_state_data(
        state,
        callback.from_user.id,
        callback.from_user.full_name,
        callback.from_user.language_code,
    )
    await state.update_data(language=lang, user_modified_reg=True)
    await state.set_state(RegistrationStates.name)
    suggested = callback.from_user.full_name or "User"
    await callback.message.answer(
        t("ask_name", lang),
        reply_markup=suggested_name_kb(suggested),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(RegistrationStates.name, F.text, ~F.text.in_(ALL_NAV_TEXTS), ~F.text.startswith("/"))
async def msg_reg_name(message: Message, state: FSMContext) -> None:
    data = await _ensure_reg_state_data(
        state,
        message.from_user.id,
        message.from_user.full_name,
        message.from_user.language_code,
    )
    lang = data.get("language", "ru")
    name = message.text.strip()[:100]
    if not name:
        name = message.from_user.full_name or "User"

    await state.update_data(name=name, user_modified_reg=True)
    await state.set_state(RegistrationStates.phone)
    await message.answer(
        t("ask_phone", lang),
        reply_markup=contact_request_kb(lang),
        parse_mode="HTML",
    )


@router.message(RegistrationStates.phone, F.contact)
async def msg_reg_phone_contact(message: Message, state: FSMContext) -> None:
    data = await _ensure_reg_state_data(
        state,
        message.from_user.id,
        message.from_user.full_name,
        message.from_user.language_code,
    )
    lang = data.get("language", "ru")
    phone = message.contact.phone_number
    if phone and not phone.startswith("+"):
        phone = f"+{phone}"

    await state.update_data(phone=phone, user_modified_reg=True)
    await state.set_state(RegistrationStates.location)
    await message.answer(
        t("ask_location", lang),
        reply_markup=location_request_kb(lang),
        parse_mode="HTML",
    )


@router.message(RegistrationStates.phone, F.text, ~F.text.in_(ALL_NAV_TEXTS), ~F.text.startswith("/"))
async def msg_reg_phone_text(message: Message, state: FSMContext) -> None:
    data = await _ensure_reg_state_data(
        state,
        message.from_user.id,
        message.from_user.full_name,
        message.from_user.language_code,
    )
    lang = data.get("language", "ru")
    txt = message.text.strip()
    skip_labels = {
        t("btn_skip_phone", "ru").lower(),
        t("btn_skip_phone", "en").lower(),
        "skip",
        "пропустить",
    }
    phone = None if txt.lower() in skip_labels else txt[:32]

    await state.update_data(phone=phone, user_modified_reg=True)
    await state.set_state(RegistrationStates.location)
    await message.answer(
        t("ask_location", lang),
        reply_markup=location_request_kb(lang),
        parse_mode="HTML",
    )


async def _send_reg_summary(
    message: Message, state: FSMContext, remove_reply_kb: bool = False
) -> None:
    data = await _ensure_reg_state_data(
        state,
        message.from_user.id,
        message.from_user.full_name,
        message.from_user.language_code,
    )
    lang = data.get("language", "ru")
    name = data.get("name", "User")
    phone = data.get("phone") or t("not_specified", lang)
    country_code = data.get("country_code", "DE")
    currency = data.get("currency", "EUR")
    tz_name = data.get("timezone", "Europe/Berlin")

    await state.set_state(RegistrationStates.confirm)

    if remove_reply_kb:
        rm_msg = await message.answer("⏳", reply_markup=ReplyKeyboardRemove())
        try:
            await rm_msg.delete()
        except Exception:
            pass

    summary_text = t(
        "reg_summary",
        lang,
        name=name,
        phone=phone,
        country=get_country_name(country_code, lang),
        currency=get_currency_label(currency, lang),
        timezone=format_timezone_with_offset(tz_name),
    )
    await message.answer(
        summary_text,
        reply_markup=reg_confirm_kb(lang),
        parse_mode="HTML",
    )


@router.message(RegistrationStates.location, F.location)
async def msg_reg_location(message: Message, state: FSMContext) -> None:
    lat = message.location.latitude
    lon = message.location.longitude
    country_profile, tz_name = resolve_location_offline(lat, lon)

    await state.update_data(
        country_code=country_profile.code,
        currency=country_profile.currency,
        timezone=tz_name,
        user_modified_reg=True,
    )
    await _send_reg_summary(message, state, remove_reply_kb=True)


@router.message(RegistrationStates.location, F.text, ~F.text.in_(ALL_NAV_TEXTS), ~F.text.startswith("/"))
async def msg_reg_location_manual(message: Message, state: FSMContext) -> None:
    data = await _ensure_reg_state_data(
        state,
        message.from_user.id,
        message.from_user.full_name,
        message.from_user.language_code,
    )
    lang = data.get("language", "ru")
    rm_msg = await message.answer("⏳", reply_markup=ReplyKeyboardRemove())
    try:
        await rm_msg.delete()
    except Exception:
        pass

    await state.set_state(RegistrationStates.custom_country)
    await message.answer(
        t("choose_country_prompt", lang),
        reply_markup=country_picker_kb(prefix="reg:country", lang=lang),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "reg:edit_country")
async def cb_reg_edit_country(callback: CallbackQuery, state: FSMContext) -> None:
    data = await _ensure_reg_state_data(
        state,
        callback.from_user.id,
        callback.from_user.full_name,
        callback.from_user.language_code,
    )
    lang = data.get("language", "ru")
    await state.set_state(RegistrationStates.custom_country)
    await safe_edit_text(
        callback.message,
        t("choose_country_prompt", lang),
        reply_markup=country_picker_kb(
            prefix="reg:country", lang=lang, back_cb="reg:back_summary"
        ),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("reg:country:"))
async def cb_reg_country_selected(callback: CallbackQuery, state: FSMContext) -> None:
    await _ensure_reg_state_data(
        state,
        callback.from_user.id,
        callback.from_user.full_name,
        callback.from_user.language_code,
    )
    code = callback.data.split(":")[-1]
    profile = get_country_profile(code)
    await state.update_data(
        country_code=profile.code,
        currency=profile.currency,
        timezone=profile.default_timezone,
        user_modified_reg=True,
    )
    await _edit_or_send_reg_summary(callback, state)


@router.callback_query(F.data == "reg:edit_currency")
async def cb_reg_edit_currency(callback: CallbackQuery, state: FSMContext) -> None:
    data = await _ensure_reg_state_data(
        state,
        callback.from_user.id,
        callback.from_user.full_name,
        callback.from_user.language_code,
    )
    lang = data.get("language", "ru")
    await state.set_state(RegistrationStates.custom_currency)
    await safe_edit_text(
        callback.message,
        t("prompt_new_currency", lang),
        reply_markup=currency_picker_kb(
            prefix="reg:currency", lang=lang, back_cb="reg:back_summary"
        ),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("reg:currency:"))
async def cb_reg_currency_selected(callback: CallbackQuery, state: FSMContext) -> None:
    await _ensure_reg_state_data(
        state,
        callback.from_user.id,
        callback.from_user.full_name,
        callback.from_user.language_code,
    )
    code = callback.data.split(":")[-1]
    await state.update_data(currency=code.upper(), user_modified_reg=True)
    await _edit_or_send_reg_summary(callback, state)


@router.message(
    RegistrationStates.custom_currency,
    F.text,
    ~F.text.in_(ALL_NAV_TEXTS),
    ~F.text.startswith("/"),
)
async def msg_reg_custom_currency(message: Message, state: FSMContext) -> None:
    data = await _ensure_reg_state_data(
        state,
        message.from_user.id,
        message.from_user.full_name,
        message.from_user.language_code,
    )
    lang = data.get("language", "ru")
    code = message.text.strip().upper()
    if not is_valid_currency(code):
        await message.answer(
            t("invalid_currency", lang),
            reply_markup=currency_picker_kb(
                prefix="reg:currency", lang=lang, back_cb="reg:back_summary"
            ),
            parse_mode="HTML",
        )
        return
    await state.update_data(currency=code, user_modified_reg=True)
    await _send_reg_summary(message, state)


@router.callback_query(F.data == "reg:edit_tz")
async def cb_reg_edit_tz(callback: CallbackQuery, state: FSMContext) -> None:
    data = await _ensure_reg_state_data(
        state,
        callback.from_user.id,
        callback.from_user.full_name,
        callback.from_user.language_code,
    )
    lang = data.get("language", "ru")
    await state.set_state(RegistrationStates.custom_timezone)
    await safe_edit_text(
        callback.message,
        t("prompt_new_tz", lang),
        reply_markup=timezone_picker_kb(
            prefix="reg:tz", lang=lang, back_cb="reg:back_summary"
        ),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("reg:tz:"))
async def cb_reg_tz_selected(callback: CallbackQuery, state: FSMContext) -> None:
    await _ensure_reg_state_data(
        state,
        callback.from_user.id,
        callback.from_user.full_name,
        callback.from_user.language_code,
    )
    tz_name = callback.data.split("reg:tz:")[-1]
    await state.update_data(timezone=tz_name, user_modified_reg=True)
    await _edit_or_send_reg_summary(callback, state)


@router.message(
    RegistrationStates.custom_timezone,
    F.text,
    ~F.text.in_(ALL_NAV_TEXTS),
    ~F.text.startswith("/"),
)
async def msg_reg_custom_tz(message: Message, state: FSMContext) -> None:
    data = await _ensure_reg_state_data(
        state,
        message.from_user.id,
        message.from_user.full_name,
        message.from_user.language_code,
    )
    lang = data.get("language", "ru")
    tz_name = message.text.strip()
    if not is_valid_timezone(tz_name):
        await message.answer(
            t("invalid_timezone", lang),
            reply_markup=timezone_picker_kb(
                prefix="reg:tz", lang=lang, back_cb="reg:back_summary"
            ),
            parse_mode="HTML",
        )
        return
    await state.update_data(timezone=tz_name, user_modified_reg=True)
    await _send_reg_summary(message, state)


@router.callback_query(F.data == "reg:back_summary")
async def cb_reg_back_summary(callback: CallbackQuery, state: FSMContext) -> None:
    await _edit_or_send_reg_summary(callback, state)


async def _edit_or_send_reg_summary(callback: CallbackQuery, state: FSMContext) -> None:
    data = await _ensure_reg_state_data(
        state,
        callback.from_user.id,
        callback.from_user.full_name,
        callback.from_user.language_code,
    )
    lang = data.get("language", "ru")
    name = data.get("name", "User")
    phone = data.get("phone") or t("not_specified", lang)
    country_code = data.get("country_code", "DE")
    currency = data.get("currency", "EUR")
    tz_name = data.get("timezone", "Europe/Berlin")

    await state.set_state(RegistrationStates.confirm)
    summary_text = t(
        "reg_summary",
        lang,
        name=name,
        phone=phone,
        country=get_country_name(country_code, lang),
        currency=get_currency_label(currency, lang),
        timezone=format_timezone_with_offset(tz_name),
    )
    await safe_edit_text(
        callback.message,
        summary_text,
        reply_markup=reg_confirm_kb(lang),
    )
    await callback.answer()


@router.callback_query(F.data == "reg:confirm")
async def cb_reg_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    async with async_session_factory() as session:
        existing_user = await get_user_by_telegram_id(session, callback.from_user.id)
        data = await state.get_data()

        if existing_user and existing_user.is_registered and not data.get("user_modified_reg"):
            # Never overwrite an already-registered user's profile if they click an old button
            # without having actively edited settings in the summary card.
            await state.clear()
            menu_text, menu_kb = await build_main_menu_payload(session, existing_user)
            await callback.message.answer(
                menu_text,
                reply_markup=menu_kb,
                parse_mode="HTML",
            )
            await callback.answer()
            return

        lang = data.get("language") or (existing_user.language if existing_user else "ru")
        name = (
            data.get("name")
            or (existing_user.name if existing_user else None)
            or callback.from_user.full_name
            or "User"
        )
        phone = data.get("phone") if "phone" in data else (existing_user.phone if existing_user else None)
        country_code = data.get("country_code") or (
            existing_user.country_code if existing_user else "DE"
        )
        profile = get_country_profile(country_code)
        currency = data.get("currency") or (
            existing_user.currency if existing_user else profile.currency
        )
        tz_name = data.get("timezone") or (
            existing_user.timezone if existing_user else profile.default_timezone
        )

        user = await create_or_update_user(
            session=session,
            telegram_id=callback.from_user.id,
            name=name,
            phone=phone,
            country_code=country_code,
            country_name=profile.name_en,
            currency=currency,
            tz_name=tz_name,
            language=lang,
            is_registered=True,
        )
        await state.clear()
        cur_info = get_currency_info(user.currency)
        try:
            await callback.message.edit_text(
                t("reg_completed", lang, sym=cur_info.symbol),
                parse_mode="HTML",
            )
        except Exception:
            pass
        await callback.message.answer(
            "⌨️",
            reply_markup=persistent_reply_kb(lang),
        )
        menu_text, menu_kb = await build_main_menu_payload(session, user)
        await callback.message.answer(
            menu_text,
            reply_markup=menu_kb,
            parse_mode="HTML",
        )
    await callback.answer()
