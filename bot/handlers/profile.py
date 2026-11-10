"""User profile and settings handlers."""

import csv
import io
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, Message, ReplyKeyboardRemove

from bot.database.crud import (
    delete_user_account,
    get_user_by_telegram_id,
    get_user_transactions,
    to_local_datetime,
    update_user_fields,
)
from bot.database.models import User
from bot.database.session import async_session_factory
from bot.i18n.translations import t
from bot.keyboards.inline import (
    confirm_delete_account_kb,
    contact_request_kb,
    country_picker_kb,
    currency_picker_kb,
    profile_settings_kb,
    timezone_picker_kb,
)
from bot.services.currencies import get_currency_label, is_valid_currency
from bot.services.geo import (
    format_timezone_with_offset,
    get_country_name,
    get_country_profile,
    is_valid_timezone,
)
from bot.states.forms import ProfileStates

router = Router(name="profile")


def _build_profile_card(user: User) -> str:
    lang = user.language
    reg_local = to_local_datetime(user.created_at, user.timezone)
    return t(
        "profile_card",
        lang,
        name=user.name,
        phone=user.phone or t("not_specified", lang),
        country=get_country_name(user.country_code, lang),
        currency=get_currency_label(user.currency, lang),
        timezone=format_timezone_with_offset(user.timezone),
        reg_date=reg_local.strftime("%d.%m.%Y"),
        notify_rec=t("enabled" if user.notify_recurring else "disabled", lang),
        daily_rem=t("enabled" if user.daily_reminder else "disabled", lang),
        reminder_hour=f"{user.reminder_hour:02d}",
    )


@router.message(Command("profile"))
async def cmd_profile(message: Message, state: FSMContext) -> None:
    await state.clear()
    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, message.from_user.id)
        if not user or not user.is_registered:
            return
        await message.answer(
            _build_profile_card(user),
            reply_markup=profile_settings_kb(user.language),
            parse_mode="HTML",
        )


@router.callback_query(F.data == "menu:profile")
async def cb_menu_profile(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user or not user.is_registered:
            await callback.answer()
            return
        await callback.message.edit_text(
            _build_profile_card(user),
            reply_markup=profile_settings_kb(user.language),
            parse_mode="HTML",
        )
        await callback.answer()


@router.callback_query(F.data == "prof:edit:name")
async def cb_prof_edit_name(callback: CallbackQuery, state: FSMContext) -> None:
    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.answer()
            return
        await state.set_state(ProfileStates.editing_name)
        await callback.message.answer(t("prompt_new_name", user.language), parse_mode="HTML")
        await callback.answer()


@router.message(ProfileStates.editing_name, F.text)
async def msg_prof_new_name(message: Message, state: FSMContext) -> None:
    new_name = message.text.strip()[:100]
    async with async_session_factory() as session:
        user = await update_user_fields(session, message.from_user.id, name=new_name)
        await state.clear()
        if user:
            await message.answer(
                f"{t('profile_updated', user.language)}\n\n{_build_profile_card(user)}",
                reply_markup=profile_settings_kb(user.language),
                parse_mode="HTML",
            )


@router.callback_query(F.data == "prof:edit:phone")
async def cb_prof_edit_phone(callback: CallbackQuery, state: FSMContext) -> None:
    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.answer()
            return
        await state.set_state(ProfileStates.editing_phone)
        await callback.message.answer(
            t("prompt_new_phone", user.language),
            reply_markup=contact_request_kb(user.language),
            parse_mode="HTML",
        )
        await callback.answer()


@router.message(ProfileStates.editing_phone, F.contact)
async def msg_prof_new_phone_contact(message: Message, state: FSMContext) -> None:
    phone = message.contact.phone_number
    if phone and not phone.startswith("+"):
        phone = f"+{phone}"
    async with async_session_factory() as session:
        user = await update_user_fields(session, message.from_user.id, phone=phone)
        await state.clear()
        rm = await message.answer("⏳", reply_markup=ReplyKeyboardRemove())
        try:
            await rm.delete()
        except Exception:
            pass
        if user:
            await message.answer(
                f"{t('profile_updated', user.language)}\n\n{_build_profile_card(user)}",
                reply_markup=profile_settings_kb(user.language),
                parse_mode="HTML",
            )


@router.message(ProfileStates.editing_phone, F.text)
async def msg_prof_new_phone_text(message: Message, state: FSMContext) -> None:
    phone = message.text.strip()[:32]
    async with async_session_factory() as session:
        user = await update_user_fields(session, message.from_user.id, phone=phone)
        await state.clear()
        rm = await message.answer("⏳", reply_markup=ReplyKeyboardRemove())
        try:
            await rm.delete()
        except Exception:
            pass
        if user:
            await message.answer(
                f"{t('profile_updated', user.language)}\n\n{_build_profile_card(user)}",
                reply_markup=profile_settings_kb(user.language),
                parse_mode="HTML",
            )


@router.callback_query(F.data == "prof:edit:country")
async def cb_prof_edit_country(callback: CallbackQuery, state: FSMContext) -> None:
    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.answer()
            return
        await state.set_state(ProfileStates.editing_country)
        await callback.message.edit_text(
            t("choose_country_prompt", user.language),
            reply_markup=country_picker_kb(
                prefix="prof:country", lang=user.language, back_cb="menu:profile"
            ),
            parse_mode="HTML",
        )
        await callback.answer()


@router.callback_query(F.data.startswith("prof:country:"))
async def cb_prof_country_selected(callback: CallbackQuery, state: FSMContext) -> None:
    code = callback.data.split(":")[-1]
    profile = get_country_profile(code)
    async with async_session_factory() as session:
        user = await update_user_fields(
            session,
            callback.from_user.id,
            country_code=profile.code,
            country_name=profile.name_en,
        )
        await state.clear()
        if user:
            await callback.message.edit_text(
                _build_profile_card(user),
                reply_markup=profile_settings_kb(user.language),
                parse_mode="HTML",
            )
        await callback.answer(t("profile_updated", user.language if user else "ru"))


@router.callback_query(F.data == "prof:edit:currency")
async def cb_prof_edit_currency(callback: CallbackQuery, state: FSMContext) -> None:
    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.answer()
            return
        await state.set_state(ProfileStates.editing_currency)
        await callback.message.edit_text(
            t("prompt_new_currency", user.language),
            reply_markup=currency_picker_kb(
                prefix="prof:currency", lang=user.language, back_cb="menu:profile"
            ),
            parse_mode="HTML",
        )
        await callback.answer()


@router.callback_query(F.data.startswith("prof:currency:"))
async def cb_prof_currency_selected(callback: CallbackQuery, state: FSMContext) -> None:
    code = callback.data.split(":")[-1].upper()
    async with async_session_factory() as session:
        user = await update_user_fields(session, callback.from_user.id, currency=code)
        await state.clear()
        if user:
            await callback.message.edit_text(
                _build_profile_card(user),
                reply_markup=profile_settings_kb(user.language),
                parse_mode="HTML",
            )
        await callback.answer(t("profile_updated", user.language if user else "ru"))


@router.message(ProfileStates.editing_currency, F.text)
async def msg_prof_currency_text(message: Message, state: FSMContext) -> None:
    code = message.text.strip().upper()
    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, message.from_user.id)
        if not user:
            return
        if not is_valid_currency(code):
            await message.answer(t("invalid_currency", user.language), parse_mode="HTML")
            return
        user = await update_user_fields(session, message.from_user.id, currency=code)
        await state.clear()
        if user:
            await message.answer(
                f"{t('profile_updated', user.language)}\n\n{_build_profile_card(user)}",
                reply_markup=profile_settings_kb(user.language),
                parse_mode="HTML",
            )


@router.callback_query(F.data == "prof:edit:tz")
async def cb_prof_edit_tz(callback: CallbackQuery, state: FSMContext) -> None:
    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.answer()
            return
        await state.set_state(ProfileStates.editing_timezone)
        await callback.message.edit_text(
            t("prompt_new_tz", user.language),
            reply_markup=timezone_picker_kb(
                prefix="prof:tz", lang=user.language, back_cb="menu:profile"
            ),
            parse_mode="HTML",
        )
        await callback.answer()


@router.callback_query(F.data.startswith("prof:tz:"))
async def cb_prof_tz_selected(callback: CallbackQuery, state: FSMContext) -> None:
    tz_name = callback.data.split("prof:tz:")[-1]
    async with async_session_factory() as session:
        user = await update_user_fields(session, callback.from_user.id, timezone=tz_name)
        await state.clear()
        if user:
            await callback.message.edit_text(
                _build_profile_card(user),
                reply_markup=profile_settings_kb(user.language),
                parse_mode="HTML",
            )
        await callback.answer(t("profile_updated", user.language if user else "ru"))


@router.message(ProfileStates.editing_timezone, F.text)
async def msg_prof_tz_text(message: Message, state: FSMContext) -> None:
    tz_name = message.text.strip()
    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, message.from_user.id)
        if not user:
            return
        if not is_valid_timezone(tz_name):
            await message.answer(t("invalid_timezone", user.language), parse_mode="HTML")
            return
        user = await update_user_fields(session, message.from_user.id, timezone=tz_name)
        await state.clear()
        if user:
            await message.answer(
                f"{t('profile_updated', user.language)}\n\n{_build_profile_card(user)}",
                reply_markup=profile_settings_kb(user.language),
                parse_mode="HTML",
            )


@router.callback_query(F.data.startswith("prof:toggle:"))
async def cb_prof_toggle_setting(callback: CallbackQuery) -> None:
    field = callback.data.split(":")[-1]
    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.answer()
            return

        if field == "lang":
            new_lang = "en" if user.language == "ru" else "ru"
            user = await update_user_fields(session, user.telegram_id, language=new_lang)
        elif field == "notify_rec":
            user = await update_user_fields(
                session, user.telegram_id, notify_recurring=not user.notify_recurring
            )
        elif field == "daily_rem":
            user = await update_user_fields(
                session, user.telegram_id, daily_reminder=not user.daily_reminder
            )

        if user:
            await callback.message.edit_text(
                _build_profile_card(user),
                reply_markup=profile_settings_kb(user.language),
                parse_mode="HTML",
            )
        await callback.answer()


@router.callback_query(F.data == "prof:export_csv")
async def cb_prof_export_csv(callback: CallbackQuery) -> None:
    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.answer()
            return
        txs, _ = await get_user_transactions(session, user.id, limit=5000, offset=0)
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["ID", "Date", "Time", "Type", "Amount", "Currency", "Description"])
        for tx in txs:
            dt_local = to_local_datetime(tx.created_at, user.timezone)
            writer.writerow(
                [
                    tx.id,
                    dt_local.strftime("%Y-%m-%d"),
                    dt_local.strftime("%H:%M:%S"),
                    tx.tx_type,
                    f"{tx.amount:.2f}",
                    tx.currency,
                    tx.description,
                ]
            )
        csv_bytes = output.getvalue().encode("utf-8-sig")
        doc = BufferedInputFile(csv_bytes, filename="finance_history.csv")
        await callback.message.answer_document(doc)
        await callback.answer()


@router.callback_query(F.data == "prof:delete_confirm")
async def cb_prof_delete_confirm(callback: CallbackQuery) -> None:
    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.answer()
            return
        await callback.message.edit_text(
            t("confirm_delete_account", user.language),
            reply_markup=confirm_delete_account_kb(user.language),
            parse_mode="HTML",
        )
        await callback.answer()


@router.callback_query(F.data == "prof:delete_execute")
async def cb_prof_delete_execute(callback: CallbackQuery, state: FSMContext) -> None:
    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        lang = user.language if user else "ru"
        await delete_user_account(session, callback.from_user.id)
        await state.clear()
        await callback.message.edit_text(t("account_deleted", lang), parse_mode="HTML")
        await callback.answer()

