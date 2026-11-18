"""Trilingual (Russian, English & German) translations and message templates."""

from typing import Dict

TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "ru": {
        # Registration
        "welcome_start": (
            "👋 <b>Добро пожаловать в Personal Finance Bot!</b>\n\n"
            "Ваш личный финансовый помощник в Telegram, который позволяет учитывать "
            "каждый доход и расход за 2–3 секунды.\n\n"
            "🌐 Выберите язык интерфейса / Choose language / Sprache wählen:"
        ),
        "ask_name": (
            "👤 <b>Шаг 1 из 3 — Как вас зовут?</b>\n\n"
            "Введите ваше имя в чат или нажмите кнопку ниже:"
        ),
        "ask_phone": (
            "📱 <b>Шаг 2 из 3 — Номер телефона</b>\n\n"
            "Нажмите кнопку <b>«📱 Отправить контакт»</b> ниже или введите номер вручную:"
        ),
        "btn_share_contact": "📱 Отправить контакт",
        "btn_skip_phone": "Пропустить",
        "ask_location": (
            "📍 <b>Шаг 3 из 3 — Местоположение</b>\n\n"
            "Отправьте геолокацию, чтобы бот автоматически определил вашу страну, "
            "основную валюту и часовой пояс.\n\n"
            "<i>Геолокация используется только для первоначальной настройки и не сохраняется. "
            "Вы также можете выбрать страну вручную.</i>"
        ),
        "btn_share_location": "📍 Отправить геолокацию",
        "btn_choose_country_manual": "🌍 Выбрать страну вручную",
        "choose_country_prompt": "🌍 <b>Выберите вашу страну из списка:</b>",
        "reg_summary": (
            "✅ <b>Настройки профиля определены!</b>\n\n"
            "👤 <b>Имя:</b> {name}\n"
            "📱 <b>Телефон:</b> {phone}\n"
            "🌍 <b>Страна:</b> {country}\n"
            "💱 <b>Основная валюта:</b> {currency}\n"
            "🕒 <b>Часовой пояс:</b> {timezone}\n\n"
            "Всё верно? Вы можете сразу завершить регистрацию или изменить любой параметр:"
        ),
        "btn_confirm_reg": "✅ Всё верно, начать!",
        "btn_change_country": "🌍 Изменить страну",
        "btn_change_currency": "💱 Изменить валюту",
        "btn_change_tz": "🕒 Изменить часовой пояс",
        "reg_completed": (
            "🎉 <b>Регистрация завершена!</b>\n\n"
            "💡 <b>Как пользоваться ботом за 2 секунды:</b>\n"
            "Просто отправьте сумму в чат в любой момент:\n"
            "• <code>5</code> — расход 5 {sym}\n"
            "• <code>6.1 lidl</code> — расход с авто-определением категории 🛒 Продукты\n"
            "• <code>12.50 Обед</code> — расход с описанием\n"
            "• <code>+1500 Зарплата</code> — доход с описанием"
        ),

        # Main Menu
        "main_menu_card": (
            "💼 <b>Personal Finance Bot</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🟢 <b>{balance}</b>\n"
            "<i>Текущий баланс</i>\n\n"
            "📈 <b>Доходы за месяц:</b>  <code>{month_income}</code>\n"
            "📉 <b>Расходы за месяц:</b> <code>{month_expense}</code>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "💡 <i>Отправьте число в чат (например <code>6.1 lidl</code> или <code>+500</code>) для мгновенной записи!</i>"
        ),
        "btn_add_expense": "➕ Добавить расход",
        "btn_add_income": "👛 Добавить доход",
        "btn_stats": "📊 Статистика",
        "btn_history": "🕒 История",
        "btn_recurring": "🔄 Регулярные операции",
        "btn_partner": "🤝 Партнёр",
        "btn_profile": "👤 Мой профиль и настройки",
        "btn_webapp": "📱 Открыть Dashboard (Mini App)",
        "btn_back_menu": "🏠 Главное меню",
        "btn_cancel": "❌ Отмена",

        # Transactions & Payment Methods
        "prompt_add_expense": (
            "➖ <b>Добавление расхода</b>\n\n"
            "Выберите категорию ниже или сразу отправьте сумму и магазин/описание:\n"
            "• <code>6.1 lidl</code>\n"
            "• <code>12.50 Кофе и круассан</code>\n"
            "• <code>45 ikea</code>"
        ),
        "prompt_add_income": (
            "➕ <b>Добавление дохода</b>\n\n"
            "Выберите категорию ниже или сразу отправьте сумму и описание:\n"
            "• <code>1500 Зарплата</code>\n"
            "• <code>+200 Стипендия</code>\n"
            "• <code>50 Подарок</code>"
        ),
        "expense_saved": (
            "✅ <b>Расход сохранён</b>  <i>Успешно</i>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "<b>{formatted_amount}</b>\n"
            "📝 <b>Описание:</b> {description}\n"
            "💳 <b>Оплата:</b> {payment_method}\n"
            "📅 <b>Дата:</b> {date}\n"
            "🕒 <b>Время:</b> {time}\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "💼 <b>Новый баланс:</b> <b>{balance}</b>"
        ),
        "income_saved": (
            "✅ <b>Доход сохранён</b>  <i>Успешно</i>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "<b>{formatted_amount}</b>\n"
            "📝 <b>Описание:</b> {description}\n"
            "💳 <b>Способ:</b> {payment_method}\n"
            "📅 <b>Дата:</b> {date}\n"
            "🕒 <b>Время:</b> {time}\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "💼 <b>Новый баланс:</b> <b>{balance}</b>"
        ),
        "pay_card": "💳 Карта",
        "pay_cash": "💵 Наличные",
        "pay_updated": "✅ Способ оплаты: {method}",
        "no_description_expense": "Расход",
        "no_description_income": "Доход",
        "btn_edit_tx": "✏️ Изменить",
        "btn_delete_tx": "🗑 Удалить",
        "tx_deleted": "🗑 Операция удалена. Новый баланс: <b>{balance}</b>",
        "tx_not_found": "⚠️ Операция не найдена.",
        "prompt_edit_tx": (
            "✏️ <b>Редактирование операции #{tx_id}</b>\n\n"
            "Текущая запись: <b>{formatted_amount}</b> — {description}\n"
            "💳 <b>Способ оплаты:</b> {payment_method}\n\n"
            "Вы можете переключить <b>Наличные / Карта</b> или <b>Категорию</b> кнопками ниже, "
            "либо отправить в чат новую сумму или описание (например: <code>15 Ужин</code>):"
        ),
        "tx_updated": (
            "✅ <b>Операция обновлена!</b>\n\n"
            "<b>{formatted_amount}</b> — {description}\n"
            "💳 <b>Способ оплаты:</b> {payment_method}\n"
            "💼 <b>Новый баланс:</b> <b>{balance}</b>"
        ),
        "invalid_tx_input": (
            "⚠️ Не удалось распознать сумму.\n"
            "Отправьте число, например: <code>5</code>, <code>6.1 lidl</code> или <code>+1500 Зарплата</code>."
        ),

        # History
        "history_title": (
            "🕒 <b>История операций</b> (Всего: {total})\n"
            "Страница {page} из {total_pages}\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "<i>Нажмите на операцию ниже для деталей, смены карты/наличных или редактирования:</i>"
        ),
        "history_empty": (
            "🕒 <b>История операций пуста</b>\n\n"
            "Вы ещё не добавили ни одной записи. Отправьте любую сумму в чат (например, <code>6.1 lidl</code>)!"
        ),
        "tx_detail_view": (
            "📄 <b>Детали операции #{tx_id}</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "📌 <b>Тип:</b> {type_label}\n"
            "💰 <b>Сумма:</b> <b>{formatted_amount}</b>\n"
            "💳 <b>Оплата:</b> {payment_method}\n"
            "💱 <b>Валюта:</b> {currency}\n"
            "📝 <b>Описание:</b> {description}\n"
            "📅 <b>Дата:</b> {date}\n"
            "🕒 <b>Время:</b> {time}"
        ),
        "type_expense": "📉 Расход",
        "type_income": "📈 Доход",
        "btn_back_history": "⬅️ К истории",

        # Statistics
        "stats_card": (
            "📊 <b>Финансовая статистика</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "💼 <b>Текущий баланс:</b> <b>{balance}</b>\n\n"
            "📉 <b>Расходы:</b>\n"
            "• За сегодня: <code>{today_expense}</code>\n"
            "• За неделю: <code>{week_expense}</code>\n"
            "• За месяц: <code>{month_expense}</code>\n"
            "• За всё время: <code>{total_expense}</code>\n\n"
            "📈 <b>Доходы:</b>\n"
            "• За сегодня: <code>{today_income}</code>\n"
            "• За неделю: <code>{week_income}</code>\n"
            "• За месяц: <code>{month_income}</code>\n"
            "• За всё время: <code>{total_income}</code>\n\n"
            "⚖️ <b>Разница (доходы − расходы за месяц):</b> <b>{net_diff}</b>\n"
            "🕒 <i>Часовой пояс: {timezone}</i>"
        ),
        "stats_payment_breakdown": (
            "\n\n💳 <b>Оплата расходов (за месяц):</b>\n"
            "• 💳 Картой: <code>{month_card}</code> ({card_pct}%)\n"
            "• 💵 Наличными: <code>{month_cash}</code> ({cash_pct}%)"
        ),
        "stats_category_header": "\n\n🏷 <b>По категориям (за месяц):</b>",

        # Recurring Transactions
        "recurring_menu_title": (
            "🔄 <b>Регулярные доходы и расходы</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Бот автоматически добавляет операции в историю в указанную дату.\n\n"
            "{list_text}"
        ),
        "recurring_empty": "<i>У вас пока нет регулярных операций.</i>",
        "btn_add_rec_expense": "➕ Регулярный расход",
        "btn_add_rec_income": "➕ Регулярный доход",
        "rec_ask_title_expense": (
            "📉 <b>Новый регулярный расход</b>\n\n"
            "Выберите шаблон или введите название в чат (например: <i>Аренда квартиры, Интернет, Подписка, Спортзал</i>):"
        ),
        "rec_ask_title_income": (
            "📈 <b>Новый регулярный доход</b>\n\n"
            "Выберите шаблон или введите название в чат (например: <i>Зарплата, Стипендия, Арендный доход</i>):"
        ),
        "rec_ask_amount": "💰 Введите сумму для <b>«{title}»</b> ({currency}):",
        "rec_ask_period": "📅 Выберите периодичность для <b>«{title}»</b>:",
        "period_daily": "Ежедневно",
        "period_weekly": "Еженедельно",
        "period_monthly": "Ежемесячно",
        "period_yearly": "Ежегодно",
        "rec_ask_date": (
            "🗓 Введите дату следующего списания/начисления в формате <code>ДД.ММ.ГГГГ</code> "
            "или выберите быстрый вариант:"
        ),
        "btn_date_today": "Сегодня ({date})",
        "btn_date_tomorrow": "Завтра ({date})",
        "btn_date_next_month": "1-е число след. месяца ({date})",
        "rec_created": (
            "✅ <b>Регулярная операция создана!</b>\n\n"
            "📌 <b>Название:</b> {title}\n"
            "💰 <b>Сумма:</b> {amount}\n"
            "🔁 <b>Периодичность:</b> {period}\n"
            "📅 <b>Следующая дата:</b> {next_date}"
        ),
        "rec_detail": (
            "🔄 <b>Регулярная операция #{rec_id}</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "📌 <b>Название:</b> {title}\n"
            "📊 <b>Тип:</b> {type_label}\n"
            "💰 <b>Сумма:</b> {amount}\n"
            "🔁 <b>Периодичность:</b> {period}\n"
            "📅 <b>Следующая дата:</b> {next_date}\n"
            "⚡ <b>Статус:</b> {status}"
        ),
        "status_active": "✅ Активна",
        "status_paused": "⏸ На паузе",
        "btn_toggle_rec": "⏯ Пауза / Возобновить",
        "btn_delete_rec": "🗑 Удалить",
        "rec_deleted": "🗑 Регулярная операция удалена.",
        "rec_auto_notification": (
            "🔔 <b>Автоматическая операция выполнена!</b>\n\n"
            "<b>{formatted_amount}</b> — {title}\n"
            "📅 Следующая дата: {next_date}\n"
            "💼 <b>Новый баланс:</b> <b>{balance}</b>"
        ),

        # Partner Mode
        "partner_unlinked_card": (
            "🤝 <b>Партнёрский режим</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Свяжите ваш аккаунт с партнёром, чтобы вместе вести бюджет:\n"
            "• Мгновенные уведомления, когда партнёр записывает расход\n"
            "• Просмотр статистики, истории и доходов партнёра за месяц\n\n"
            "🔑 <b>Ваш личный партнёрский код:</b>\n"
            "<code>{partner_code}</code>\n\n"
            "<i>Отправьте этот код партнёру или нажмите кнопку «🔗 Связать аккаунты» ниже и введите код партнёра. "
            "Два аккаунта связываются навсегда.</i>"
        ),
        "btn_link_partner": "🔗 Связать аккаунты",
        "prompt_enter_partner_code": (
            "🔗 <b>Привязка партнёра</b>\n\n"
            "Ваш личный код: <code>{partner_code}</code>\n\n"
            "Отправьте в чат партнёрский код второго пользователя (например: <code>JNL-AB12CD</code>):"
        ),
        "partner_link_success": (
            "🎉 <b>Аккаунты успешно связаны навсегда!</b>\n\n"
            "🤝 Ваш партнёр: <b>{partner_name}</b>"
        ),
        "partner_linked_notification": (
            "🤝 <b>Партнёрский режим активирован!</b>\n\n"
            "Пользователь <b>{user_name}</b> связал свой аккаунт с вашим.\n"
            "Теперь вы будете получать уведомления о расходах друг друга и сможете просматривать общую статистику в разделе «🤝 Партнёр»."
        ),
        "partner_error_invalid_code": (
            "⚠️ Партнёрский код не найден. Проверьте код и отправьте его ещё раз:"
        ),
        "partner_error_self_code": (
            "⚠️ Это ваш собственный код. Введите партнёрский код второго пользователя:"
        ),
        "partner_error_already_linked": (
            "ℹ️ Ваш аккаунт уже навсегда связан с партнёром."
        ),
        "partner_error_target_linked": (
            "⚠️ Этот пользователь уже связан с другим партнёром."
        ),
        "partner_dashboard_card": (
            "🤝 <b>Партнёрский кабинет</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "👤 <b>Партнёр:</b> {partner_name}\n"
            "🔑 <b>Ваш код:</b> <code>{partner_code}</code>\n\n"
            "💼 <b>Баланс партнёра:</b> <b>{partner_balance}</b>\n"
            "📈 <b>Доходы партнёра за месяц:</b> <code>{partner_month_income}</code>\n"
            "📉 <b>Расходы партнёра за месяц:</b> <code>{partner_month_expense}</code>\n"
            "  • 💳 Картой: <code>{partner_month_card}</code>\n"
            "  • 💵 Наличными: <code>{partner_month_cash}</code>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "📊 <b>Ваши показатели за месяц:</b>\n"
            "📈 Доходы: <code>{my_month_income}</code> | 📉 Расходы: <code>{my_month_expense}</code>"
        ),
        "btn_partner_stats": "📊 Статистика партнёра",
        "btn_partner_history": "🕒 История партнёра",
        "btn_partner_refresh": "🔄 Обновить",
        "btn_back_partner": "⬅️ К партнёру",
        "btn_back_partner_history": "⬅️ К истории партнёра",
        "partner_stats_title": "🤝 <b>Статистика партнёра: {partner_name}</b>\n\n{stats_body}",
        "partner_history_title": (
            "🕒 <b>История партнёра: {partner_name}</b> (Всего: {total})\n"
            "Страница {page} из {total_pages}\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "<i>Нажмите на запись ниже для просмотра деталей операции:</i>"
        ),
        "partner_history_empty": (
            "🕒 <b>История операций партнёра ({partner_name}) пока пуста.</b>"
        ),
        "partner_tx_detail_view": (
            "🤝 <b>Операция партнёра ({partner_name}) #{tx_id}</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "📌 <b>Тип:</b> {type_label}\n"
            "💰 <b>Сумма:</b> <b>{formatted_amount}</b>\n"
            "💳 <b>Оплата:</b> {payment_method}\n"
            "💱 <b>Валюта:</b> {currency}\n"
            "📝 <b>Описание:</b> {description}\n"
            "📅 <b>Дата:</b> {date}\n"
            "🕒 <b>Время:</b> {time}"
        ),
        "partner_expense_alert": (
            "🤝 <b>Новый расход партнёра ({partner_name})</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "<b>{formatted_amount}</b>\n"
            "📝 <b>Описание:</b> {description}\n"
            "💳 <b>Оплата:</b> {payment_method}\n"
            "📅 <b>Время:</b> {date} в {time}\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "📉 <b>Расходы партнёра за месяц:</b> <code>{month_expense}</code>\n"
            "📈 <b>Доходы партнёра за месяц:</b> <code>{month_income}</code>"
        ),

        # Profile & Settings
        "profile_card": (
            "👤 <b>Мой профиль и настройки</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "👤 <b>Имя:</b> {name}\n"
            "📱 <b>Телефон:</b> {phone}\n"
            "🌍 <b>Страна:</b> {country}\n"
            "💱 <b>Основная валюта:</b> {currency}\n"
            "🕒 <b>Часовой пояс:</b> {timezone}\n"
            "🌐 <b>Язык интерфейса:</b> Русский 🇷🇺\n"
            "📅 <b>Дата регистрации:</b> {reg_date}\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🔔 <b>Уведомления о регулярных платежах:</b> {notify_rec}\n"
            "⏰ <b>Напоминания записать расходы ({reminder_hour}:00):</b> {daily_rem}"
        ),
        "prompt_choose_lang": (
            "🌐 <b>Выберите язык интерфейса / Choose language / Sprache wählen:</b>"
        ),
        "enabled": "✅ Вкл",
        "disabled": "❌ Выкл",
        "not_specified": "Не указан",
        "btn_edit_name": "✏️ Имя",
        "btn_edit_phone": "📱 Телефон",
        "btn_edit_country": "🌍 Страна",
        "btn_edit_currency": "💱 Валюта",
        "btn_edit_tz": "🕒 Часовой пояс",
        "btn_edit_lang": "🌐 Язык / Language / Sprache",
        "btn_toggle_notify_rec": "🔔 Уведомления регулярных",
        "btn_toggle_daily_rem": "⏰ Напоминания о расходах",
        "btn_export_csv": "📥 Экспорт истории (CSV)",
        "btn_delete_account": "⚠️ Удалить аккаунт",
        "prompt_new_name": "✏️ Введите новое имя:",
        "prompt_new_phone": "📱 Отправьте контакт кнопкой или введите новый номер телефона в чат:",
        "prompt_new_currency": (
            "💱 <b>Выберите основную валюту</b> из списка ниже или отправьте "
            "трёхбуквенный код валюты по стандарту ISO 4217 (например: <code>EUR</code>, <code>USD</code>, <code>UZS</code>, <code>PLN</code>):"
        ),
        "prompt_new_tz": (
            "🕒 <b>Выберите часовой пояс</b> из списка ниже или отправьте название зоны IANA "
            "(например: <code>Europe/Berlin</code>, <code>Asia/Tashkent</code>, <code>America/New_York</code>):"
        ),
        "profile_updated": "✅ Настройки профиля успешно обновлены!",
        "invalid_currency": "⚠️ Неизвестный код валюты ISO 4217. Попробуйте, например: <code>EUR</code>, <code>USD</code>, <code>UZS</code>.",
        "invalid_timezone": "⚠️ Неизвестный часовой пояс. Пример правильного формата: <code>Europe/Berlin</code> или <code>Asia/Tashkent</code>.",
        "confirm_delete_account": (
            "⚠️ <b>Удаление аккаунта</b>\n\n"
            "Вы уверены, что хотите удалить свой профиль, всю историю операций и регулярные платежи?\n"
            "<i>Это действие необратимо!</i>"
        ),
        "btn_confirm_delete_yes": "🗑 Да, удалить навсегда",
        "btn_confirm_delete_no": "✅ Нет, оставить аккаунт",
        "account_deleted": "👋 Ваш аккаунт и все финансовые данные были удалены. Нажмите /start, если захотите начать заново.",
        "daily_reminder_msg": (
            "⏰ <b>Напоминание о расходах</b>\n\n"
            "Не забудьте записать сегодняшние расходы! Просто отправьте сумму в чат (например: <code>6.1 lidl</code>)."
        ),
        "system_error_safe": (
            "⚠️ Произошла временная техническая задержка. Ваши данные в безопасности, попробуйте ещё раз."
        ),
        "db_save_error": (
            "⚠️ Не удалось сохранить операцию из-за временной ошибки базы данных. Попробуйте отправить сумму ещё раз."
        ),
        "unknown_command": (
            "ℹ️ Неизвестная команда. Используйте /menu для открытия главного меню или просто отправьте сумму в чат."
        ),
        "kb_expense": "➕ Расход",
        "kb_income": "👛 Доход",
        "kb_stats": "📊 Статистика",
        "kb_history": "🕒 История",
        "kb_menu": "🏠 Главное меню",
        "kb_partner": "🤝 Партнёр",
        "kb_profile": "👤 Профиль",
        "btn_change_cat": "🏷 Категория",
        "choose_cat_prompt": "🏷 <b>Выберите категорию для операции #{tx_id}:</b>",
        "cat_updated": "✅ Категория изменена на: {category}",
        "prompt_add_expense_cat": (
            "➖ <b>Добавление расхода — {category}</b>\n\n"
            "Отправьте сумму и (по желанию) описание:\n"
            "• <code>6.1</code>\n"
            "• <code>12.50 Комментарий</code>"
        ),
        "prompt_add_income_cat": (
            "➕ <b>Добавление дохода — {category}</b>\n\n"
            "Отправьте сумму и (по желанию) описание:\n"
            "• <code>1500</code>\n"
            "• <code>200 Комментарий</code>"
        ),
        "btn_back_categories": "⬅️ К категориям",
        "btn_back_tx": "⬅️ К операции",
        "btn_flip_type": "🔄 Сменить тип (Расход ↔ Доход)",
        "tx_type_flipped": "✅ Тип операции изменён!",
        "btn_edit_rec_amount": "💰 Сумма",
        "btn_edit_rec_title": "✏️ Название",
        "btn_edit_rec_period": "🔁 Период",
        "btn_edit_rec_date": "📅 Дата",
        "rec_updated": "✅ Регулярная операция обновлена!",
        "rec_edit_title_prompt": "✏️ <b>Изменение названия для «{title}»</b>\n\nВведите новое название или выберите шаблон:",
        "rec_edit_amount_prompt": "💰 <b>Изменение суммы для «{title}»</b>\n\nВведите новую сумму ({currency}):",
        "rec_edit_period_prompt": "🔁 <b>Выберите новую периодичность для «{title}»:</b>",
        "rec_edit_date_prompt": (
            "🗓 <b>Изменение следующей даты для «{title}»</b>\n\n"
            "Введите дату в формате <code>ДД.ММ.ГГГГ</code> или выберите вариант ниже:"
        ),
        "btn_back_rec": "⬅️ Назад",
        "btn_back_profile": "⬅️ Назад в профиль",
        "btn_edit_rem_hour": "🕒 Время напоминания ({hour}:00)",
        "prompt_new_rem_hour": "🕒 <b>Выберите время ежедневного напоминания:</b>",
    },
    "en": {
        # Registration
        "welcome_start": (
            "👋 <b>Welcome to Personal Finance Bot!</b>\n\n"
            "Your personal finance assistant in Telegram that lets you track every "
            "expense and income in 2–3 seconds.\n\n"
            "🌐 Choose your language / Выберите язык / Sprache wählen:"
        ),
        "ask_name": (
            "👤 <b>Step 1 of 3 — What is your name?</b>\n\n"
            "Type your name in the chat or tap the button below:"
        ),
        "ask_phone": (
            "📱 <b>Step 2 of 3 — Phone Number</b>\n\n"
            "Tap <b>«📱 Share Contact»</b> below or type your phone number manually:"
        ),
        "btn_share_contact": "📱 Share Contact",
        "btn_skip_phone": "Skip",
        "ask_location": (
            "📍 <b>Step 3 of 3 — Location</b>\n\n"
            "Share your location so the bot can automatically detect your country, "
            "primary currency, and timezone.\n\n"
            "<i>Location is only used for initial setup and is not stored. "
            "You can also select your country manually.</i>"
        ),
        "btn_share_location": "📍 Share Location",
        "btn_choose_country_manual": "🌍 Select Country Manually",
        "choose_country_prompt": "🌍 <b>Select your country from the list:</b>",
        "reg_summary": (
            "✅ <b>Profile Settings Detected!</b>\n\n"
            "👤 <b>Name:</b> {name}\n"
            "📱 <b>Phone:</b> {phone}\n"
            "🌍 <b>Country:</b> {country}\n"
            "💱 <b>Primary Currency:</b> {currency}\n"
            "🕒 <b>Timezone:</b> {timezone}\n\n"
            "Does everything look good? Confirm to finish setup or customize any field:"
        ),
        "btn_confirm_reg": "✅ Looks good, start!",
        "btn_change_country": "🌍 Change Country",
        "btn_change_currency": "💱 Change Currency",
        "btn_change_tz": "🕒 Change Timezone",
        "reg_completed": (
            "🎉 <b>Registration Complete!</b>\n\n"
            "💡 <b>How to log transactions in 2 seconds:</b>\n"
            "Simply send an amount in the chat at any time:\n"
            "• <code>5</code> — expense of 5 {sym}\n"
            "• <code>6.1 lidl</code> — expense with auto-detected category 🛒 Groceries\n"
            "• <code>12.50 Lunch</code> — expense with description\n"
            "• <code>+1500 Salary</code> — income with description"
        ),

        # Main Menu
        "main_menu_card": (
            "💼 <b>Personal Finance Bot</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🟢 <b>{balance}</b>\n"
            "<i>Current Balance</i>\n\n"
            "📈 <b>Monthly Income:</b>   <code>{month_income}</code>\n"
            "📉 <b>Monthly Expenses:</b> <code>{month_expense}</code>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "💡 <i>Send any number in chat (e.g. <code>6.1 lidl</code> or <code>+500</code>) for instant logging!</i>"
        ),
        "btn_add_expense": "➕ Add Expense",
        "btn_add_income": "👛 Add Income",
        "btn_stats": "📊 Statistics",
        "btn_history": "🕒 History",
        "btn_recurring": "🔄 Recurring Operations",
        "btn_partner": "🤝 Partner",
        "btn_profile": "👤 My Profile & Settings",
        "btn_webapp": "📱 Open Dashboard (Mini App)",
        "btn_back_menu": "🏠 Main Menu",
        "btn_cancel": "❌ Cancel",

        # Transactions & Payment Methods
        "prompt_add_expense": (
            "➖ <b>Add Expense</b>\n\n"
            "Pick a category below or send the amount and store/description directly:\n"
            "• <code>6.1 lidl</code>\n"
            "• <code>12.50 Coffee & croissant</code>\n"
            "• <code>45 ikea</code>"
        ),
        "prompt_add_income": (
            "➕ <b>Add Income</b>\n\n"
            "Pick a category below or send the amount and description directly:\n"
            "• <code>1500 Salary</code>\n"
            "• <code>+200 Stipend</code>\n"
            "• <code>50 Gift</code>"
        ),
        "expense_saved": (
            "✅ <b>Expense Saved</b>  <i>Success</i>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "<b>{formatted_amount}</b>\n"
            "📝 <b>Description:</b> {description}\n"
            "💳 <b>Payment:</b> {payment_method}\n"
            "📅 <b>Date:</b> {date}\n"
            "🕒 <b>Time:</b> {time}\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "💼 <b>New Balance:</b> <b>{balance}</b>"
        ),
        "income_saved": (
            "✅ <b>Income Saved</b>  <i>Success</i>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "<b>{formatted_amount}</b>\n"
            "📝 <b>Description:</b> {description}\n"
            "💳 <b>Method:</b> {payment_method}\n"
            "📅 <b>Date:</b> {date}\n"
            "🕒 <b>Time:</b> {time}\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "💼 <b>New Balance:</b> <b>{balance}</b>"
        ),
        "pay_card": "💳 Card",
        "pay_cash": "💵 Cash",
        "pay_updated": "✅ Payment method: {method}",
        "no_description_expense": "Expense",
        "no_description_income": "Income",
        "btn_edit_tx": "✏️ Edit",
        "btn_delete_tx": "🗑 Delete",
        "tx_deleted": "🗑 Transaction deleted. New balance: <b>{balance}</b>",
        "tx_not_found": "⚠️ Transaction not found.",
        "prompt_edit_tx": (
            "✏️ <b>Edit Transaction #{tx_id}</b>\n\n"
            "Current entry: <b>{formatted_amount}</b> — {description}\n"
            "💳 <b>Payment method:</b> {payment_method}\n\n"
            "Switch <b>Cash / Card</b> or <b>Category</b> using the buttons below, "
            "or send a new amount or description in chat (e.g., <code>15 Dinner</code>):"
        ),
        "tx_updated": (
            "✅ <b>Transaction Updated!</b>\n\n"
            "<b>{formatted_amount}</b> — {description}\n"
            "💳 <b>Payment method:</b> {payment_method}\n"
            "💼 <b>New Balance:</b> <b>{balance}</b>"
        ),
        "invalid_tx_input": (
            "⚠️ Could not parse the amount.\n"
            "Send a number, for example: <code>5</code>, <code>6.1 lidl</code>, or <code>+1500 Salary</code>."
        ),

        # History
        "history_title": (
            "🕒 <b>Transaction History</b> (Total: {total})\n"
            "Page {page} of {total_pages}\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "<i>Tap a transaction below to view details, switch Cash/Card, edit, or delete:</i>"
        ),
        "history_empty": (
            "🕒 <b>Transaction History is Empty</b>\n\n"
            "You haven't logged any transactions yet. Simply send an amount in chat (e.g. <code>6.1 lidl</code>)!"
        ),
        "tx_detail_view": (
            "📄 <b>Transaction Details #{tx_id}</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "📌 <b>Type:</b> {type_label}\n"
            "💰 <b>Amount:</b> <b>{formatted_amount}</b>\n"
            "💳 <b>Payment:</b> {payment_method}\n"
            "💱 <b>Currency:</b> {currency}\n"
            "📝 <b>Description:</b> {description}\n"
            "📅 <b>Date:</b> {date}\n"
            "🕒 <b>Time:</b> {time}"
        ),
        "type_expense": "📉 Expense",
        "type_income": "📈 Income",
        "btn_back_history": "⬅️ Back to History",

        # Statistics
        "stats_card": (
            "📊 <b>Financial Statistics</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "💼 <b>Current Balance:</b> <b>{balance}</b>\n\n"
            "📉 <b>Expenses:</b>\n"
            "• Today: <code>{today_expense}</code>\n"
            "• This Week: <code>{week_expense}</code>\n"
            "• This Month: <code>{month_expense}</code>\n"
            "• All Time: <code>{total_expense}</code>\n\n"
            "📈 <b>Income:</b>\n"
            "• Today: <code>{today_income}</code>\n"
            "• This Week: <code>{week_income}</code>\n"
            "• This Month: <code>{month_income}</code>\n"
            "• All Time: <code>{total_income}</code>\n\n"
            "⚖️ <b>Net Difference (monthly income − expenses):</b> <b>{net_diff}</b>\n"
            "🕒 <i>Timezone: {timezone}</i>"
        ),
        "stats_payment_breakdown": (
            "\n\n💳 <b>Expenses by Payment Method (This Month):</b>\n"
            "• 💳 Card: <code>{month_card}</code> ({card_pct}%)\n"
            "• 💵 Cash: <code>{month_cash}</code> ({cash_pct}%)"
        ),
        "stats_category_header": "\n\n🏷 <b>By Category (This Month):</b>",

        # Recurring Transactions
        "recurring_menu_title": (
            "🔄 <b>Recurring Income & Expenses</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "The bot automatically logs these operations on their scheduled date.\n\n"
            "{list_text}"
        ),
        "recurring_empty": "<i>You have no recurring operations yet.</i>",
        "btn_add_rec_expense": "➕ Recurring Expense",
        "btn_add_rec_income": "➕ Recurring Income",
        "rec_ask_title_expense": (
            "📉 <b>New Recurring Expense</b>\n\n"
            "Pick a preset or type a title in chat (e.g. <i>Apartment Rent, Internet, Subscriptions, Gym</i>):"
        ),
        "rec_ask_title_income": (
            "📈 <b>New Recurring Income</b>\n\n"
            "Pick a preset or type a title in chat (e.g. <i>Salary, Stipend, Rental Income</i>):"
        ),
        "rec_ask_amount": "💰 Enter the amount for <b>“{title}”</b> ({currency}):",
        "rec_ask_period": "📅 Select frequency for <b>“{title}”</b>:",
        "period_daily": "Daily",
        "period_weekly": "Weekly",
        "period_monthly": "Monthly",
        "period_yearly": "Yearly",
        "rec_ask_date": (
            "🗓 Enter the next execution date in <code>DD.MM.YYYY</code> format "
            "or choose a quick option:"
        ),
        "btn_date_today": "Today ({date})",
        "btn_date_tomorrow": "Tomorrow ({date})",
        "btn_date_next_month": "1st of Next Month ({date})",
        "rec_created": (
            "✅ <b>Recurring Operation Created!</b>\n\n"
            "📌 <b>Title:</b> {title}\n"
            "💰 <b>Amount:</b> {amount}\n"
            "🔁 <b>Frequency:</b> {period}\n"
            "📅 <b>Next Date:</b> {next_date}"
        ),
        "rec_detail": (
            "🔄 <b>Recurring Operation #{rec_id}</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "📌 <b>Title:</b> {title}\n"
            "📊 <b>Type:</b> {type_label}\n"
            "💰 <b>Amount:</b> {amount}\n"
            "🔁 <b>Frequency:</b> {period}\n"
            "📅 <b>Next Date:</b> {next_date}\n"
            "⚡ <b>Status:</b> {status}"
        ),
        "status_active": "✅ Active",
        "status_paused": "⏸ Paused",
        "btn_toggle_rec": "⏯ Pause / Resume",
        "btn_delete_rec": "🗑 Delete",
        "rec_deleted": "🗑 Recurring operation deleted.",
        "rec_auto_notification": (
            "🔔 <b>Recurring Operation Executed!</b>\n\n"
            "<b>{formatted_amount}</b> — {title}\n"
            "📅 Next Date: {next_date}\n"
            "💼 <b>New Balance:</b> <b>{balance}</b>"
        ),

        # Partner Mode
        "partner_unlinked_card": (
            "🤝 <b>Partner Mode</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Link your account with your partner to track finances together:\n"
            "• Instant notifications whenever your partner logs an expense\n"
            "• View your partner's monthly income, expenses, statistics, and history\n\n"
            "🔑 <b>Your Personal Partner Code:</b>\n"
            "<code>{partner_code}</code>\n\n"
            "<i>Share this code with your partner, or tap «🔗 Link Partner» below to enter your partner's code. "
            "Two accounts are linked permanently.</i>"
        ),
        "btn_link_partner": "🔗 Link Partner",
        "prompt_enter_partner_code": (
            "🔗 <b>Link Partner Account</b>\n\n"
            "Your personal code: <code>{partner_code}</code>\n\n"
            "Send your partner's code in chat (e.g. <code>JNL-AB12CD</code>):"
        ),
        "partner_link_success": (
            "🎉 <b>Accounts Permanently Linked!</b>\n\n"
            "🤝 Your partner: <b>{partner_name}</b>"
        ),
        "partner_linked_notification": (
            "🤝 <b>Partner Mode Activated!</b>\n\n"
            "<b>{user_name}</b> has linked their account with yours.\n"
            "You will now receive notifications for new expenses and can view shared statistics in «🤝 Partner»."
        ),
        "partner_error_invalid_code": (
            "⚠️ Partner code not found. Please check the code and send it again:"
        ),
        "partner_error_self_code": (
            "⚠️ That is your own partner code. Please enter your partner's code:"
        ),
        "partner_error_already_linked": (
            "ℹ️ Your account is already permanently linked with a partner."
        ),
        "partner_error_target_linked": (
            "⚠️ That user is already linked with another partner."
        ),
        "partner_dashboard_card": (
            "🤝 <b>Partner Dashboard</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "👤 <b>Partner:</b> {partner_name}\n"
            "🔑 <b>Your code:</b> <code>{partner_code}</code>\n\n"
            "💼 <b>Partner's Balance:</b> <b>{partner_balance}</b>\n"
            "📈 <b>Partner's Monthly Income:</b> <code>{partner_month_income}</code>\n"
            "📉 <b>Partner's Monthly Expenses:</b> <code>{partner_month_expense}</code>\n"
            "  • 💳 Card: <code>{partner_month_card}</code>\n"
            "  • 💵 Cash: <code>{partner_month_cash}</code>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "📊 <b>Your Monthly Summary:</b>\n"
            "📈 Income: <code>{my_month_income}</code> | 📉 Expenses: <code>{my_month_expense}</code>"
        ),
        "btn_partner_stats": "📊 Partner Statistics",
        "btn_partner_history": "🕒 Partner History",
        "btn_partner_refresh": "🔄 Refresh",
        "btn_back_partner": "⬅️ Back to Partner",
        "btn_back_partner_history": "⬅️ Partner History",
        "partner_stats_title": "🤝 <b>Partner Statistics: {partner_name}</b>\n\n{stats_body}",
        "partner_history_title": (
            "🕒 <b>Partner History: {partner_name}</b> (Total: {total})\n"
            "Page {page} of {total_pages}\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "<i>Tap an entry below to view transaction details:</i>"
        ),
        "partner_history_empty": (
            "🕒 <b>Your partner ({partner_name}) has no transactions yet.</b>"
        ),
        "partner_tx_detail_view": (
            "🤝 <b>Partner Transaction ({partner_name}) #{tx_id}</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "📌 <b>Type:</b> {type_label}\n"
            "💰 <b>Amount:</b> <b>{formatted_amount}</b>\n"
            "💳 <b>Payment:</b> {payment_method}\n"
            "💱 <b>Currency:</b> {currency}\n"
            "📝 <b>Description:</b> {description}\n"
            "📅 <b>Date:</b> {date}\n"
            "🕒 <b>Time:</b> {time}"
        ),
        "partner_expense_alert": (
            "🤝 <b>New Partner Expense ({partner_name})</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "<b>{formatted_amount}</b>\n"
            "📝 <b>Description:</b> {description}\n"
            "💳 <b>Payment:</b> {payment_method}\n"
            "📅 <b>Time:</b> {date} at {time}\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "📉 <b>Partner's Monthly Expenses:</b> <code>{month_expense}</code>\n"
            "📈 <b>Partner's Monthly Income:</b> <code>{month_income}</code>"
        ),

        # Profile & Settings
        "profile_card": (
            "👤 <b>My Profile & Settings</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "👤 <b>Name:</b> {name}\n"
            "📱 <b>Phone:</b> {phone}\n"
            "🌍 <b>Country:</b> {country}\n"
            "💱 <b>Primary Currency:</b> {currency}\n"
            "🕒 <b>Timezone:</b> {timezone}\n"
            "🌐 <b>Language:</b> English 🇬🇧\n"
            "📅 <b>Registered:</b> {reg_date}\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🔔 <b>Recurring Payment Alerts:</b> {notify_rec}\n"
            "⏰ <b>Daily Expense Reminders ({reminder_hour}:00):</b> {daily_rem}"
        ),
        "prompt_choose_lang": (
            "🌐 <b>Choose your language / Выберите язык / Sprache wählen:</b>"
        ),
        "enabled": "✅ On",
        "disabled": "❌ Off",
        "not_specified": "Not set",
        "btn_edit_name": "✏️ Name",
        "btn_edit_phone": "📱 Phone",
        "btn_edit_country": "🌍 Country",
        "btn_edit_currency": "💱 Currency",
        "btn_edit_tz": "🕒 Timezone",
        "btn_edit_lang": "🌐 Language / Язык / Sprache",
        "btn_toggle_notify_rec": "🔔 Recurring Alerts",
        "btn_toggle_daily_rem": "⏰ Expense Reminders",
        "btn_export_csv": "📥 Export History (CSV)",
        "btn_delete_account": "⚠️ Delete Account",
        "prompt_new_name": "✏️ Enter your new name:",
        "prompt_new_phone": "📱 Share your contact using the button or type a new phone number:",
        "prompt_new_currency": (
            "💱 <b>Select your primary currency</b> below or type any 3-letter "
            "ISO 4217 currency code (e.g. <code>EUR</code>, <code>USD</code>, <code>UZS</code>, <code>GBP</code>):"
        ),
        "prompt_new_tz": (
            "🕒 <b>Select your timezone</b> below or type an IANA timezone name "
            "(e.g. <code>Europe/Berlin</code>, <code>Asia/Tashkent</code>, <code>America/New_York</code>):"
        ),
        "profile_updated": "✅ Profile settings updated!",
        "invalid_currency": "⚠️ Unrecognized ISO 4217 currency code. Try e.g. <code>EUR</code>, <code>USD</code>, <code>UZS</code>.",
        "invalid_timezone": "⚠️ Unrecognized timezone. Example valid format: <code>Europe/Berlin</code> or <code>Asia/Tashkent</code>.",
        "confirm_delete_account": (
            "⚠️ <b>Delete Account</b>\n\n"
            "Are you sure you want to permanently delete your profile, all transaction history, and recurring payments?\n"
            "<i>This action cannot be undone!</i>"
        ),
        "btn_confirm_delete_yes": "🗑 Yes, delete permanently",
        "btn_confirm_delete_no": "✅ No, keep my account",
        "account_deleted": "👋 Your account and all financial data have been deleted. Send /start if you ever wish to begin again.",
        "daily_reminder_msg": (
            "⏰ <b>Daily Expense Reminder</b>\n\n"
            "Don't forget to log today's expenses! Simply send an amount in chat (e.g. <code>6.1 lidl</code>)."
        ),
        "system_error_safe": (
            "⚠️ A temporary technical issue occurred. Your data is safe, please try again."
        ),
        "db_save_error": (
            "⚠️ Could not save the transaction due to a temporary database issue. Please try sending the amount again."
        ),
        "unknown_command": (
            "ℹ️ Unknown command. Use /menu to open the main menu or simply send an amount in chat."
        ),
        "kb_expense": "➕ Expense",
        "kb_income": "👛 Income",
        "kb_stats": "📊 Statistics",
        "kb_history": "🕒 History",
        "kb_menu": "🏠 Main Menu",
        "kb_partner": "🤝 Partner",
        "kb_profile": "👤 Profile",
        "btn_change_cat": "🏷 Category",
        "choose_cat_prompt": "🏷 <b>Select category for transaction #{tx_id}:</b>",
        "cat_updated": "✅ Category updated to: {category}",
        "prompt_add_expense_cat": (
            "➖ <b>Add Expense — {category}</b>\n\n"
            "Send the amount and (optionally) a description:\n"
            "• <code>6.1</code>\n"
            "• <code>12.50 Note</code>"
        ),
        "prompt_add_income_cat": (
            "➕ <b>Add Income — {category}</b>\n\n"
            "Send the amount and (optionally) a description:\n"
            "• <code>1500</code>\n"
            "• <code>200 Note</code>"
        ),
        "btn_back_categories": "⬅️ Back to Categories",
        "btn_back_tx": "⬅️ Back to Transaction",
        "btn_flip_type": "🔄 Switch Type (Expense ↔ Income)",
        "tx_type_flipped": "✅ Transaction type updated!",
        "btn_edit_rec_amount": "💰 Amount",
        "btn_edit_rec_title": "✏️ Title",
        "btn_edit_rec_period": "🔁 Period",
        "btn_edit_rec_date": "📅 Date",
        "rec_updated": "✅ Recurring operation updated!",
        "rec_edit_title_prompt": "✏️ <b>Edit Title for “{title}”</b>\n\nEnter a new title or choose a preset:",
        "rec_edit_amount_prompt": "💰 <b>Edit Amount for “{title}”</b>\n\nEnter the new amount ({currency}):",
        "rec_edit_period_prompt": "🔁 <b>Select new frequency for “{title}”:</b>",
        "rec_edit_date_prompt": (
            "🗓 <b>Edit Next Date for “{title}”</b>\n\n"
            "Enter a date in <code>DD.MM.YYYY</code> format or pick an option below:"
        ),
        "btn_back_rec": "⬅️ Back",
        "btn_back_profile": "⬅️ Back to Profile",
        "btn_edit_rem_hour": "🕒 Reminder Time ({hour}:00)",
        "prompt_new_rem_hour": "🕒 <b>Select your daily reminder time:</b>",
    },
    "de": {
        # Registration
        "welcome_start": (
            "👋 <b>Willkommen beim Personal Finance Bot!</b>\n\n"
            "Ihr persönlicher Finanzassistent in Telegram — erfassen Sie jede "
            "Ausgabe und Einnahme in nur 2–3 Sekunden.\n\n"
            "🌐 Sprache wählen / Choose language / Выберите язык:"
        ),
        "ask_name": (
            "👤 <b>Schritt 1 von 3 — Wie heißen Sie?</b>\n\n"
            "Geben Sie Ihren Namen im Chat ein oder tippen Sie unten auf den Button:"
        ),
        "ask_phone": (
            "📱 <b>Schritt 2 von 3 — Telefonnummer</b>\n\n"
            "Tippen Sie unten auf <b>„📱 Kontakt teilen“</b> oder geben Sie Ihre Nummer manuell ein:"
        ),
        "btn_share_contact": "📱 Kontakt teilen",
        "btn_skip_phone": "Überspringen",
        "ask_location": (
            "📍 <b>Schritt 3 von 3 — Standort</b>\n\n"
            "Teilen Sie Ihren Standort, damit der Bot automatisch Ihr Land, "
            "Ihre Hauptwährung und Ihre Zeitzone erkennt.\n\n"
            "<i>Der Standort wird nur für die Ersteinrichtung verwendet und nicht gespeichert. "
            "Sie können Ihr Land auch manuell auswählen.</i>"
        ),
        "btn_share_location": "📍 Standort teilen",
        "btn_choose_country_manual": "🌍 Land manuell wählen",
        "choose_country_prompt": "🌍 <b>Wählen Sie Ihr Land aus der Liste:</b>",
        "reg_summary": (
            "✅ <b>Profileinstellungen erkannt!</b>\n\n"
            "👤 <b>Name:</b> {name}\n"
            "📱 <b>Telefon:</b> {phone}\n"
            "🌍 <b>Land:</b> {country}\n"
            "💱 <b>Hauptwährung:</b> {currency}\n"
            "🕒 <b>Zeitzone:</b> {timezone}\n\n"
            "Stimmt alles? Bestätigen Sie zum Starten oder passen Sie ein Feld an:"
        ),
        "btn_confirm_reg": "✅ Alles richtig, starten!",
        "btn_change_country": "🌍 Land ändern",
        "btn_change_currency": "💱 Währung ändern",
        "btn_change_tz": "🕒 Zeitzone ändern",
        "reg_completed": (
            "🎉 <b>Registrierung abgeschlossen!</b>\n\n"
            "💡 <b>So erfassen Sie Buchungen in 2 Sekunden:</b>\n"
            "Senden Sie einfach jederzeit einen Betrag in den Chat:\n"
            "• <code>5</code> — Ausgabe von 5 {sym}\n"
            "• <code>6.1 lidl</code> — Ausgabe mit automatischer Kategorie 🛒 Lebensmittel\n"
            "• <code>12.50 Mittagessen</code> — Ausgabe mit Beschreibung\n"
            "• <code>+1500 Gehalt</code> — Einnahme mit Beschreibung"
        ),

        # Main Menu
        "main_menu_card": (
            "💼 <b>Personal Finance Bot</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🟢 <b>{balance}</b>\n"
            "<i>Aktueller Kontostand</i>\n\n"
            "📈 <b>Einnahmen (Monat):</b> <code>{month_income}</code>\n"
            "📉 <b>Ausgaben (Monat):</b>  <code>{month_expense}</code>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "💡 <i>Senden Sie einfach einen Betrag in den Chat (z.B. <code>6.1 lidl</code> oder <code>+500</code>)!</i>"
        ),
        "btn_add_expense": "➕ Ausgabe hinzufügen",
        "btn_add_income": "👛 Einnahme hinzufügen",
        "btn_stats": "📊 Statistik",
        "btn_history": "🕒 Verlauf",
        "btn_recurring": "🔄 Regelmäßige Buchungen",
        "btn_partner": "🤝 Partner",
        "btn_profile": "👤 Mein Profil & Einstellungen",
        "btn_webapp": "📱 Dashboard öffnen (Mini App)",
        "btn_back_menu": "🏠 Hauptmenü",
        "btn_cancel": "❌ Abbrechen",

        # Transactions & Payment Methods
        "prompt_add_expense": (
            "➖ <b>Ausgabe hinzufügen</b>\n\n"
            "Wählen Sie unten eine Kategorie oder senden Sie direkt Betrag und Geschäft/Beschreibung:\n"
            "• <code>6.1 lidl</code>\n"
            "• <code>12.50 Kaffee & Croissant</code>\n"
            "• <code>45 ikea</code>"
        ),
        "prompt_add_income": (
            "➕ <b>Einnahme hinzufügen</b>\n\n"
            "Wählen Sie unten eine Kategorie oder senden Sie direkt Betrag und Beschreibung:\n"
            "• <code>1500 Gehalt</code>\n"
            "• <code>+200 Stipendium</code>\n"
            "• <code>50 Geschenk</code>"
        ),
        "expense_saved": (
            "✅ <b>Ausgabe gespeichert</b>  <i>Erfolgreich</i>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "<b>{formatted_amount}</b>\n"
            "📝 <b>Beschreibung:</b> {description}\n"
            "💳 <b>Zahlung:</b> {payment_method}\n"
            "📅 <b>Datum:</b> {date}\n"
            "🕒 <b>Uhrzeit:</b> {time}\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "💼 <b>Neuer Kontostand:</b> <b>{balance}</b>"
        ),
        "income_saved": (
            "✅ <b>Einnahme gespeichert</b>  <i>Erfolgreich</i>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "<b>{formatted_amount}</b>\n"
            "📝 <b>Beschreibung:</b> {description}\n"
            "💳 <b>Methode:</b> {payment_method}\n"
            "📅 <b>Datum:</b> {date}\n"
            "🕒 <b>Uhrzeit:</b> {time}\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "💼 <b>Neuer Kontostand:</b> <b>{balance}</b>"
        ),
        "pay_card": "💳 Karte",
        "pay_cash": "💵 Bargeld",
        "pay_updated": "✅ Zahlungsmethode: {method}",
        "no_description_expense": "Ausgabe",
        "no_description_income": "Einnahme",
        "btn_edit_tx": "✏️ Bearbeiten",
        "btn_delete_tx": "🗑 Löschen",
        "tx_deleted": "🗑 Buchung gelöscht. Neuer Kontostand: <b>{balance}</b>",
        "tx_not_found": "⚠️ Buchung nicht gefunden.",
        "prompt_edit_tx": (
            "✏️ <b>Buchung #{tx_id} bearbeiten</b>\n\n"
            "Aktueller Eintrag: <b>{formatted_amount}</b> — {description}\n"
            "💳 <b>Zahlungsmethode:</b> {payment_method}\n\n"
            "Wechseln Sie unten per Button <b>Bargeld / Karte</b> oder <b>Kategorie</b>, "
            "oder senden Sie einen neuen Betrag bzw. Text (z.B. <code>15 Abendessen</code>):"
        ),
        "tx_updated": (
            "✅ <b>Buchung aktualisiert!</b>\n\n"
            "<b>{formatted_amount}</b> — {description}\n"
            "💳 <b>Zahlungsmethode:</b> {payment_method}\n"
            "💼 <b>Neuer Kontostand:</b> <b>{balance}</b>"
        ),
        "invalid_tx_input": (
            "⚠️ Betrag konnte nicht erkannt werden.\n"
            "Senden Sie eine Zahl, z.B.: <code>5</code>, <code>6.1 lidl</code> oder <code>+1500 Gehalt</code>."
        ),

        # History
        "history_title": (
            "🕒 <b>Transaktionsverlauf</b> (Gesamt: {total})\n"
            "Seite {page} von {total_pages}\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "<i>Tippen Sie unten auf einen Eintrag für Details, Bargeld/Karte oder Bearbeitung:</i>"
        ),
        "history_empty": (
            "🕒 <b>Transaktionsverlauf ist leer</b>\n\n"
            "Sie haben noch keine Buchungen erfasst. Senden Sie einfach einen Betrag in den Chat (z.B. <code>6.1 lidl</code>)!"
        ),
        "tx_detail_view": (
            "📄 <b>Buchungsdetails #{tx_id}</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "📌 <b>Typ:</b> {type_label}\n"
            "💰 <b>Betrag:</b> <b>{formatted_amount}</b>\n"
            "💳 <b>Zahlung:</b> {payment_method}\n"
            "💱 <b>Währung:</b> {currency}\n"
            "📝 <b>Beschreibung:</b> {description}\n"
            "📅 <b>Datum:</b> {date}\n"
            "🕒 <b>Uhrzeit:</b> {time}"
        ),
        "type_expense": "📉 Ausgabe",
        "type_income": "📈 Einnahme",
        "btn_back_history": "⬅️ Zum Verlauf",

        # Statistics
        "stats_card": (
            "📊 <b>Finanzstatistik</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "💼 <b>Aktueller Kontostand:</b> <b>{balance}</b>\n\n"
            "📉 <b>Ausgaben:</b>\n"
            "• Heute: <code>{today_expense}</code>\n"
            "• Diese Woche: <code>{week_expense}</code>\n"
            "• Dieser Monat: <code>{month_expense}</code>\n"
            "• Gesamt: <code>{total_expense}</code>\n\n"
            "📈 <b>Einnahmen:</b>\n"
            "• Heute: <code>{today_income}</code>\n"
            "• Diese Woche: <code>{week_income}</code>\n"
            "• Dieser Monat: <code>{month_income}</code>\n"
            "• Gesamt: <code>{total_income}</code>\n\n"
            "⚖️ <b>Differenz (Einnahmen − Ausgaben im Monat):</b> <b>{net_diff}</b>\n"
            "🕒 <i>Zeitzone: {timezone}</i>"
        ),
        "stats_payment_breakdown": (
            "\n\n💳 <b>Ausgaben nach Zahlungsart (Monat):</b>\n"
            "• 💳 Karte: <code>{month_card}</code> ({card_pct}%)\n"
            "• 💵 Bargeld: <code>{month_cash}</code> ({cash_pct}%)"
        ),
        "stats_category_header": "\n\n🏷 <b>Nach Kategorien (Monat):</b>",

        # Recurring Transactions
        "recurring_menu_title": (
            "🔄 <b>Regelmäßige Einnahmen & Ausgaben</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Der Bot bucht diese Vorgänge automatisch am geplanten Datum.\n\n"
            "{list_text}"
        ),
        "recurring_empty": "<i>Sie haben noch keine regelmäßigen Buchungen.</i>",
        "btn_add_rec_expense": "➕ Regelm. Ausgabe",
        "btn_add_rec_income": "➕ Regelm. Einnahme",
        "rec_ask_title_expense": (
            "📉 <b>Neue regelmäßige Ausgabe</b>\n\n"
            "Wählen Sie eine Vorlage oder geben Sie einen Namen ein (z.B. <i>Miete, Internet, Abos, Fitnessstudio</i>):"
        ),
        "rec_ask_title_income": (
            "📈 <b>Neue regelmäßige Einnahme</b>\n\n"
            "Wählen Sie eine Vorlage oder geben Sie einen Namen ein (z.B. <i>Gehalt, Stipendium, Mieteinnahmen</i>):"
        ),
        "rec_ask_amount": "💰 Geben Sie den Betrag für <b>„{title}“</b> ({currency}) ein:",
        "rec_ask_period": "📅 Wählen Sie das Intervall für <b>„{title}“</b>:",
        "period_daily": "Täglich",
        "period_weekly": "Wöchentlich",
        "period_monthly": "Monatlich",
        "period_yearly": "Jährlich",
        "rec_ask_date": (
            "🗓 Geben Sie das nächste Ausführungsdatum im Format <code>TT.MM.JJJJ</code> ein "
            "oder wählen Sie eine Schnelloption:"
        ),
        "btn_date_today": "Heute ({date})",
        "btn_date_tomorrow": "Morgen ({date})",
        "btn_date_next_month": "1. des nächsten Monats ({date})",
        "rec_created": (
            "✅ <b>Regelmäßige Buchung erstellt!</b>\n\n"
            "📌 <b>Name:</b> {title}\n"
            "💰 <b>Betrag:</b> {amount}\n"
            "🔁 <b>Intervall:</b> {period}\n"
            "📅 <b>Nächstes Datum:</b> {next_date}"
        ),
        "rec_detail": (
            "🔄 <b>Regelmäßige Buchung #{rec_id}</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "📌 <b>Name:</b> {title}\n"
            "📊 <b>Typ:</b> {type_label}\n"
            "💰 <b>Betrag:</b> {amount}\n"
            "🔁 <b>Intervall:</b> {period}\n"
            "📅 <b>Nächstes Datum:</b> {next_date}\n"
            "⚡ <b>Status:</b> {status}"
        ),
        "status_active": "✅ Aktiv",
        "status_paused": "⏸ Pausiert",
        "btn_toggle_rec": "⏯ Pause / Fortsetzen",
        "btn_delete_rec": "🗑 Löschen",
        "rec_deleted": "🗑 Regelmäßige Buchung gelöscht.",
        "rec_auto_notification": (
            "🔔 <b>Regelmäßige Buchung ausgeführt!</b>\n\n"
            "<b>{formatted_amount}</b> — {title}\n"
            "📅 Nächstes Datum: {next_date}\n"
            "💼 <b>Neuer Kontostand:</b> <b>{balance}</b>"
        ),

        # Partner Mode
        "partner_unlinked_card": (
            "🤝 <b>Partner-Modus</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Verbinden Sie Ihr Konto dauerhaft mit Ihrem Partner:\n"
            "• Sofortige Benachrichtigung, wenn Ihr Partner eine Ausgabe einträgt\n"
            "• Einblick in monatliche Einnahmen, Ausgaben, Statistik und Verlauf Ihres Partners\n\n"
            "🔑 <b>Ihr persönlicher Partner-Code:</b>\n"
            "<code>{partner_code}</code>\n\n"
            "<i>Teilen Sie diesen Code mit Ihrem Partner oder tippen Sie unten auf „🔗 Partner verbinden“, "
            "um den Code Ihres Partners einzugeben. Die Verbindung beider Konten ist dauerhaft.</i>"
        ),
        "btn_link_partner": "🔗 Partner verbinden",
        "prompt_enter_partner_code": (
            "🔗 <b>Partner-Konto verbinden</b>\n\n"
            "Ihr persönlicher Code: <code>{partner_code}</code>\n\n"
            "Senden Sie den Partner-Code der zweiten Person in den Chat (z.B. <code>JNL-AB12CD</code>):"
        ),
        "partner_link_success": (
            "🎉 <b>Konten dauerhaft verbunden!</b>\n\n"
            "🤝 Ihr Partner: <b>{partner_name}</b>"
        ),
        "partner_linked_notification": (
            "🤝 <b>Partner-Modus aktiviert!</b>\n\n"
            "<b>{user_name}</b> hat sein/ihr Konto mit Ihrem verbunden.\n"
            "Sie erhalten nun Benachrichtigungen über neue Ausgaben und sehen die Partner-Statistik unter „🤝 Partner“."
        ),
        "partner_error_invalid_code": (
            "⚠️ Partner-Code nicht gefunden. Bitte prüfen Sie den Code und senden Sie ihn erneut:"
        ),
        "partner_error_self_code": (
            "⚠️ Das ist Ihr eigener Code. Bitte geben Sie den Partner-Code der anderen Person ein:"
        ),
        "partner_error_already_linked": (
            "ℹ️ Ihr Konto ist bereits dauerhaft mit einem Partner verbunden."
        ),
        "partner_error_target_linked": (
            "⚠️ Dieser Nutzer ist bereits mit einem anderen Partner verbunden."
        ),
        "partner_dashboard_card": (
            "🤝 <b>Partner-Übersicht</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "👤 <b>Partner:</b> {partner_name}\n"
            "🔑 <b>Ihr Code:</b> <code>{partner_code}</code>\n\n"
            "💼 <b>Kontostand des Partners:</b> <b>{partner_balance}</b>\n"
            "📈 <b>Monatliche Einnahmen (Partner):</b> <code>{partner_month_income}</code>\n"
            "📉 <b>Monatliche Ausgaben (Partner):</b> <code>{partner_month_expense}</code>\n"
            "  • 💳 Karte: <code>{partner_month_card}</code>\n"
            "  • 💵 Bargeld: <code>{partner_month_cash}</code>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "📊 <b>Ihre Monatsübersicht:</b>\n"
            "📈 Einnahmen: <code>{my_month_income}</code> | 📉 Ausgaben: <code>{my_month_expense}</code>"
        ),
        "btn_partner_stats": "📊 Partner-Statistik",
        "btn_partner_history": "🕒 Partner-Verlauf",
        "btn_partner_refresh": "🔄 Aktualisieren",
        "btn_back_partner": "⬅️ Zurück zum Partner",
        "btn_back_partner_history": "⬅️ Zum Partner-Verlauf",
        "partner_stats_title": "🤝 <b>Partner-Statistik: {partner_name}</b>\n\n{stats_body}",
        "partner_history_title": (
            "🕒 <b>Partner-Verlauf: {partner_name}</b> (Gesamt: {total})\n"
            "Seite {page} von {total_pages}\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "<i>Tippen Sie unten auf einen Eintrag, um Details anzusehen:</i>"
        ),
        "partner_history_empty": (
            "🕒 <b>Ihr Partner ({partner_name}) hat noch keine Buchungen.</b>"
        ),
        "partner_tx_detail_view": (
            "🤝 <b>Partner-Buchung ({partner_name}) #{tx_id}</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "📌 <b>Typ:</b> {type_label}\n"
            "💰 <b>Betrag:</b> <b>{formatted_amount}</b>\n"
            "💳 <b>Zahlung:</b> {payment_method}\n"
            "💱 <b>Währung:</b> {currency}\n"
            "📝 <b>Beschreibung:</b> {description}\n"
            "📅 <b>Datum:</b> {date}\n"
            "🕒 <b>Uhrzeit:</b> {time}"
        ),
        "partner_expense_alert": (
            "🤝 <b>Neue Ausgabe Ihres Partners ({partner_name})</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "<b>{formatted_amount}</b>\n"
            "📝 <b>Beschreibung:</b> {description}\n"
            "💳 <b>Zahlung:</b> {payment_method}\n"
            "📅 <b>Zeit:</b> {date} um {time}\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "📉 <b>Ausgaben des Partners (Monat):</b> <code>{month_expense}</code>\n"
            "📈 <b>Einnahmen des Partners (Monat):</b> <code>{month_income}</code>"
        ),

        # Profile & Settings
        "profile_card": (
            "👤 <b>Mein Profil & Einstellungen</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "👤 <b>Name:</b> {name}\n"
            "📱 <b>Telefon:</b> {phone}\n"
            "🌍 <b>Land:</b> {country}\n"
            "💱 <b>Hauptwährung:</b> {currency}\n"
            "🕒 <b>Zeitzone:</b> {timezone}\n"
            "🌐 <b>Sprache:</b> Deutsch 🇩🇪\n"
            "📅 <b>Registriert am:</b> {reg_date}\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🔔 <b>Benachrichtigungen für regelm. Zahlungen:</b> {notify_rec}\n"
            "⏰ <b>Tägliche Erinnerung ({reminder_hour}:00):</b> {daily_rem}"
        ),
        "prompt_choose_lang": (
            "🌐 <b>Sprache wählen / Choose language / Выберите язык:</b>"
        ),
        "enabled": "✅ Ein",
        "disabled": "❌ Aus",
        "not_specified": "Nicht angegeben",
        "btn_edit_name": "✏️ Name",
        "btn_edit_phone": "📱 Telefon",
        "btn_edit_country": "🌍 Land",
        "btn_edit_currency": "💱 Währung",
        "btn_edit_tz": "🕒 Zeitzone",
        "btn_edit_lang": "🌐 Sprache / Language / Язык",
        "btn_toggle_notify_rec": "🔔 Regelm. Zahlungen",
        "btn_toggle_daily_rem": "⏰ Ausgaben-Erinnerung",
        "btn_export_csv": "📥 Verlauf exportieren (CSV)",
        "btn_delete_account": "⚠️ Konto löschen",
        "prompt_new_name": "✏️ Geben Sie Ihren neuen Namen ein:",
        "prompt_new_phone": "📱 Teilen Sie Ihren Kontakt per Button oder geben Sie Ihre Telefonnummer ein:",
        "prompt_new_currency": (
            "💱 <b>Wählen Sie Ihre Hauptwährung</b> unten aus oder senden Sie einen "
            "dreistelligen ISO-4217-Code (z.B. <code>EUR</code>, <code>USD</code>, <code>CHF</code>, <code>PLN</code>):"
        ),
        "prompt_new_tz": (
            "🕒 <b>Wählen Sie Ihre Zeitzone</b> unten aus oder senden Sie einen IANA-Namen "
            "(z.B. <code>Europe/Berlin</code>, <code>Europe/Vienna</code>, <code>Europe/Zurich</code>):"
        ),
        "profile_updated": "✅ Profileinstellungen erfolgreich aktualisiert!",
        "invalid_currency": "⚠️ Unbekannter ISO-4217-Währungscode. Beispiel: <code>EUR</code>, <code>USD</code>, <code>CHF</code>.",
        "invalid_timezone": "⚠️ Unbekannte Zeitzone. Beispiel: <code>Europe/Berlin</code> oder <code>Asia/Tashkent</code>.",
        "confirm_delete_account": (
            "⚠️ <b>Konto löschen</b>\n\n"
            "Sind Sie sicher, dass Sie Ihr Profil, den gesamten Transaktionsverlauf und alle regelmäßigen Zahlungen dauerhaft löschen möchten?\n"
            "<i>Diese Aktion kann nicht rückgängig gemacht werden!</i>"
        ),
        "btn_confirm_delete_yes": "🗑 Ja, endgültig löschen",
        "btn_confirm_delete_no": "✅ Nein, Konto behalten",
        "account_deleted": "👋 Ihr Konto und alle Finanzdaten wurden gelöscht. Senden Sie /start, um neu zu beginnen.",
        "daily_reminder_msg": (
            "⏰ <b>Erinnerung an Ihre Ausgaben</b>\n\n"
            "Vergessen Sie nicht, Ihre heutigen Ausgaben einzutragen! Senden Sie einfach einen Betrag in den Chat (z.B. <code>6.1 lidl</code>)."
        ),
        "system_error_safe": (
            "⚠️ Eine vorübergehende technische Verzögerung ist aufgetreten. Ihre Daten sind sicher, bitte versuchen Sie es erneut."
        ),
        "db_save_error": (
            "⚠️ Die Buchung konnte wegen eines vorübergehenden Datenbankfehlers nicht gespeichert werden. Bitte senden Sie den Betrag erneut."
        ),
        "unknown_command": (
            "ℹ️ Unbekannter Befehl. Nutzen Sie /menu für das Hauptmenü oder senden Sie einfach einen Betrag in den Chat."
        ),
        "kb_expense": "➕ Ausgabe",
        "kb_income": "👛 Einnahme",
        "kb_stats": "📊 Statistik",
        "kb_history": "🕒 Verlauf",
        "kb_menu": "🏠 Hauptmenü",
        "kb_partner": "🤝 Partner",
        "kb_profile": "👤 Profil",
        "btn_change_cat": "🏷 Kategorie",
        "choose_cat_prompt": "🏷 <b>Kategorie für Buchung #{tx_id} wählen:</b>",
        "cat_updated": "✅ Kategorie geändert auf: {category}",
        "prompt_add_expense_cat": (
            "➖ <b>Ausgabe hinzufügen — {category}</b>\n\n"
            "Senden Sie den Betrag und (optional) eine Beschreibung:\n"
            "• <code>6.1</code>\n"
            "• <code>12.50 Notiz</code>"
        ),
        "prompt_add_income_cat": (
            "➕ <b>Einnahme hinzufügen — {category}</b>\n\n"
            "Senden Sie den Betrag und (optional) eine Beschreibung:\n"
            "• <code>1500</code>\n"
            "• <code>200 Notiz</code>"
        ),
        "btn_back_categories": "⬅️ Zu den Kategorien",
        "btn_back_tx": "⬅️ Zur Buchung",
        "btn_flip_type": "🔄 Typ wechseln (Ausgabe ↔ Einnahme)",
        "tx_type_flipped": "✅ Buchungstyp geändert!",
        "btn_edit_rec_amount": "💰 Betrag",
        "btn_edit_rec_title": "✏️ Name",
        "btn_edit_rec_period": "🔁 Intervall",
        "btn_edit_rec_date": "📅 Datum",
        "rec_updated": "✅ Regelmäßige Buchung aktualisiert!",
        "rec_edit_title_prompt": "✏️ <b>Name ändern für „{title}“</b>\n\nGeben Sie einen neuen Namen ein oder wählen Sie eine Vorlage:",
        "rec_edit_amount_prompt": "💰 <b>Betrag ändern für „{title}“</b>\n\nGeben Sie den neuen Betrag ({currency}) ein:",
        "rec_edit_period_prompt": "🔁 <b>Neues Intervall für „{title}“ wählen:</b>",
        "rec_edit_date_prompt": (
            "🗓 <b>Nächstes Datum ändern für „{title}“</b>\n\n"
            "Geben Sie ein Datum im Format <code>TT.MM.JJJJ</code> ein oder wählen Sie unten:"
        ),
        "btn_back_rec": "⬅️ Zurück",
        "btn_back_profile": "⬅️ Zurück zum Profil",
        "btn_edit_rem_hour": "🕒 Erinnerungszeit ({hour}:00)",
        "prompt_new_rem_hour": "🕒 <b>Wählen Sie Ihre tägliche Erinnerungszeit:</b>",
    },
}


def normalize_lang(lang: str = "ru") -> str:
    raw = (lang or "ru").lower().strip()
    if raw.startswith("de"):
        return "de"
    if raw.startswith("en"):
        return "en"
    return "ru"


def t(key: str, lang: str = "ru", **kwargs) -> str:
    """Translate a key into the given language ('ru', 'en', or 'de') and format placeholders."""
    lang_code = normalize_lang(lang)
    template = TRANSLATIONS.get(lang_code, TRANSLATIONS["ru"]).get(
        key, TRANSLATIONS["ru"].get(key, key)
    )
    if kwargs:
        return template.format(**kwargs)
    return template


def payment_method_label(method: str, lang: str = "ru") -> str:
    if (method or "card").lower() == "cash":
        return t("pay_cash", lang)
    return t("pay_card", lang)


def period_label(period: str, lang: str = "ru") -> str:
    mapping = {
        "daily": t("period_daily", lang),
        "weekly": t("period_weekly", lang),
        "monthly": t("period_monthly", lang),
        "yearly": t("period_yearly", lang),
    }
    return mapping.get(period, period)
