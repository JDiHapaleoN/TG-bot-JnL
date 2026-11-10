"""Bilingual (Russian & English) translations and message templates."""

from typing import Dict

TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "ru": {
        # Registration
        "welcome_start": (
            "👋 <b>Добро пожаловать в Personal Finance Bot!</b>\n\n"
            "Ваш личный финансовый помощник в Telegram, который позволяет учитывать "
            "каждый доход и расход за 2–3 секунды.\n\n"
            "🌐 Выберите язык интерфейса / Choose your language:"
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
            "• <code>12.50</code> — расход 12.50 {sym}\n"
            "• <code>5 Обед</code> или <code>5 | Обед в McDonald's</code> — расход с описанием\n"
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
            "💡 <i>Отправьте число в чат (например <code>15 Обед</code> или <code>+500</code>) для мгновенной записи!</i>"
        ),
        "btn_add_expense": "➕ Добавить расход",
        "btn_add_income": "👛 Добавить доход",
        "btn_stats": "📊 Статистика",
        "btn_history": "🕒 История",
        "btn_recurring": "🔄 Регулярные операции",
        "btn_profile": "👤 Мой профиль и настройки",
        "btn_webapp": "📱 Открыть Dashboard (Mini App)",
        "btn_back_menu": "🏠 Главное меню",
        "btn_cancel": "❌ Отмена",

        # Transactions
        "prompt_add_expense": (
            "➖ <b>Добавление расхода</b>\n\n"
            "Отправьте сумму и (по желанию) описание:\n"
            "• <code>5</code>\n"
            "• <code>12.50 Кофе и круассан</code>\n"
            "• <code>25 | Продукты</code>"
        ),
        "prompt_add_income": (
            "➕ <b>Добавление дохода</b>\n\n"
            "Отправьте сумму и (по желанию) описание:\n"
            "• <code>1500 Зарплата</code>\n"
            "• <code>+200 Стипендия</code>\n"
            "• <code>50 | Подарок</code>"
        ),
        "expense_saved": (
            "✅ <b>Расход сохранён</b>  <i>Успешно</i>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "<b>{formatted_amount}</b>\n"
            "📝 <b>Описание:</b> {description}\n"
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
            "📅 <b>Дата:</b> {date}\n"
            "🕒 <b>Время:</b> {time}\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "💼 <b>Новый баланс:</b> <b>{balance}</b>"
        ),
        "no_description_expense": "Расход",
        "no_description_income": "Доход",
        "btn_edit_tx": "✏️ Изменить",
        "btn_delete_tx": "🗑 Удалить",
        "tx_deleted": "🗑 Операция удалена. Новый баланс: <b>{balance}</b>",
        "tx_not_found": "⚠️ Операция не найдена.",
        "prompt_edit_tx": (
            "✏️ <b>Редактирование операции #{tx_id}</b>\n\n"
            "Текущая запись: <b>{formatted_amount}</b> — {description}\n\n"
            "Отправьте новую сумму и описание (например: <code>15 Ужин</code> или <code>+500 Бонус</code>):"
        ),
        "tx_updated": (
            "✅ <b>Операция обновлена!</b>\n\n"
            "<b>{formatted_amount}</b> — {description}\n"
            "💼 <b>Новый баланс:</b> <b>{balance}</b>"
        ),
        "invalid_tx_input": (
            "⚠️ Не удалось распознать сумму.\n"
            "Отправьте число, например: <code>5</code>, <code>12.50 Обед</code> или <code>+1500 Зарплата</code>."
        ),

        # History
        "history_title": (
            "🕒 <b>История операций</b> (Всего: {total})\n"
            "Страница {page} из {total_pages}\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "<i>Нажмите на номер операции ниже для редактирования или удаления:</i>"
        ),
        "history_empty": (
            "🕒 <b>История операций пуста</b>\n\n"
            "Вы ещё не добавили ни одной записи. Отправьте любую сумму в чат (например, <code>5 Обед</code>)!"
        ),
        "tx_detail_view": (
            "📄 <b>Детали операции #{tx_id}</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "📌 <b>Тип:</b> {type_label}\n"
            "💰 <b>Сумма:</b> <b>{formatted_amount}</b>\n"
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
        "enabled": "✅ Вкл",
        "disabled": "❌ Выкл",
        "not_specified": "Не указан",
        "btn_edit_name": "✏️ Имя",
        "btn_edit_phone": "📱 Телефон",
        "btn_edit_country": "🌍 Страна",
        "btn_edit_currency": "💱 Валюта",
        "btn_edit_tz": "🕒 Часовой пояс",
        "btn_edit_lang": "🌐 Язык / Language",
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
            "Не забудьте записать сегодняшние расходы! Просто отправьте сумму в чат (например: <code>12.50 Ужин</code>)."
        ),
    },
    "en": {
        # Registration
        "welcome_start": (
            "👋 <b>Welcome to Personal Finance Bot!</b>\n\n"
            "Your personal finance assistant in Telegram that lets you track every "
            "expense and income in 2–3 seconds.\n\n"
            "🌐 Choose your language / Выберите язык интерфейса:"
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
            "• <code>12.50</code> — expense of 12.50 {sym}\n"
            "• <code>5 Lunch</code> or <code>5 | Lunch at McDonald's</code> — expense with description\n"
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
            "💡 <i>Send any number in chat (e.g. <code>15 Lunch</code> or <code>+500</code>) for instant logging!</i>"
        ),
        "btn_add_expense": "➕ Add Expense",
        "btn_add_income": "👛 Add Income",
        "btn_stats": "📊 Statistics",
        "btn_history": "🕒 History",
        "btn_recurring": "🔄 Recurring Operations",
        "btn_profile": "👤 My Profile & Settings",
        "btn_webapp": "📱 Open Dashboard (Mini App)",
        "btn_back_menu": "🏠 Main Menu",
        "btn_cancel": "❌ Cancel",

        # Transactions
        "prompt_add_expense": (
            "➖ <b>Add Expense</b>\n\n"
            "Send the amount and (optionally) a description:\n"
            "• <code>5</code>\n"
            "• <code>12.50 Coffee & croissant</code>\n"
            "• <code>25 | Groceries</code>"
        ),
        "prompt_add_income": (
            "➕ <b>Add Income</b>\n\n"
            "Send the amount and (optionally) a description:\n"
            "• <code>1500 Salary</code>\n"
            "• <code>+200 Stipend</code>\n"
            "• <code>50 | Gift</code>"
        ),
        "expense_saved": (
            "✅ <b>Expense Saved</b>  <i>Success</i>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "<b>{formatted_amount}</b>\n"
            "📝 <b>Description:</b> {description}\n"
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
            "📅 <b>Date:</b> {date}\n"
            "🕒 <b>Time:</b> {time}\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "💼 <b>New Balance:</b> <b>{balance}</b>"
        ),
        "no_description_expense": "Expense",
        "no_description_income": "Income",
        "btn_edit_tx": "✏️ Edit",
        "btn_delete_tx": "🗑 Delete",
        "tx_deleted": "🗑 Transaction deleted. New balance: <b>{balance}</b>",
        "tx_not_found": "⚠️ Transaction not found.",
        "prompt_edit_tx": (
            "✏️ <b>Edit Transaction #{tx_id}</b>\n\n"
            "Current entry: <b>{formatted_amount}</b> — {description}\n\n"
            "Send the new amount and description (e.g., <code>15 Dinner</code> or <code>+500 Bonus</code>):"
        ),
        "tx_updated": (
            "✅ <b>Transaction Updated!</b>\n\n"
            "<b>{formatted_amount}</b> — {description}\n"
            "💼 <b>New Balance:</b> <b>{balance}</b>"
        ),
        "invalid_tx_input": (
            "⚠️ Could not parse the amount.\n"
            "Send a number, for example: <code>5</code>, <code>12.50 Lunch</code>, or <code>+1500 Salary</code>."
        ),

        # History
        "history_title": (
            "🕒 <b>Transaction History</b> (Total: {total})\n"
            "Page {page} of {total_pages}\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "<i>Tap a transaction button below to view details, edit, or delete:</i>"
        ),
        "history_empty": (
            "🕒 <b>Transaction History is Empty</b>\n\n"
            "You haven't logged any transactions yet. Simply send an amount in chat (e.g. <code>5 Lunch</code>)!"
        ),
        "tx_detail_view": (
            "📄 <b>Transaction Details #{tx_id}</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "📌 <b>Type:</b> {type_label}\n"
            "💰 <b>Amount:</b> <b>{formatted_amount}</b>\n"
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
        "enabled": "✅ On",
        "disabled": "❌ Off",
        "not_specified": "Not set",
        "btn_edit_name": "✏️ Name",
        "btn_edit_phone": "📱 Phone",
        "btn_edit_country": "🌍 Country",
        "btn_edit_currency": "💱 Currency",
        "btn_edit_tz": "🕒 Timezone",
        "btn_edit_lang": "🌐 Language / Язык",
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
            "Don't forget to log today's expenses! Simply send an amount in chat (e.g. <code>12.50 Dinner</code>)."
        ),
    },
}


def t(key: str, lang: str = "ru", **kwargs) -> str:
    """Translate a key into the given language ('ru' or 'en') and format placeholders."""
    lang_code = "en" if (lang or "").lower().startswith("en") else "ru"
    template = TRANSLATIONS.get(lang_code, TRANSLATIONS["ru"]).get(
        key, TRANSLATIONS["ru"].get(key, key)
    )
    if kwargs:
        return template.format(**kwargs)
    return template


def period_label(period: str, lang: str = "ru") -> str:
    mapping = {
        "daily": t("period_daily", lang),
        "weekly": t("period_weekly", lang),
        "monthly": t("period_monthly", lang),
        "yearly": t("period_yearly", lang),
    }
    return mapping.get(period, period)

