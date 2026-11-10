# Personal Finance Bot (JnL-Bot) — MVP

Telegram-бот + Telegram Mini App (WebApp) для быстрого учёта личных финансов (расходов, доходов, регулярных платежей и статистики) за 2–3 секунды.

---

## ✨ Возможности MVP

1. **Мгновенный учёт расходов и доходов в чате (за 2–3 секунды)**:
   - `5` → Расход `− €5.00`
   - `12.50` или `12,50` → Расход `− €12.50`
   - `5 | Обед в McDonald's` или `5 Обед` → Расход `− €5.00` с описанием
   - `+1500` → Доход `+ €1,500.00`
   - `+200 Стипендия` → Доход `+ €200.00` с описанием
2. **Регистрация и первоначальная настройка (`/start`)**:
   - Выбор языка (`Русский` / `English`).
   - Ввод имени (или выбор имени профиля Telegram в 1 клик).
   - Отправка номера телефона через кнопку **Telegram Contact** (или ввод вручную / пропуск).
   - Отправка **геолокации** → автоматическое офлайн-определение страны, основной валюты (ISO 4217) и часового пояса (`timezonefinder` + локальный справочник стран без внешних API).
3. **Гибридный интерфейс (Чат + Telegram Mini App / WebApp)**:
   - Полноценное меню и управление прямо в чате Telegram (Inline-кнопки + команды `/start`, `/menu`, `/stats`, `/history`, `/recurring`, `/profile`).
   - Встроенный **Telegram Mini App (WebApp)** в тёмной теме.
4. **История операций, статистика и регулярные платежи**:
   - Постраничный просмотр всех записей, редактирование и удаление.
   - Статистика за день, неделю, месяц и всё время + текущий баланс.
   - Автоматические регулярные доходы и расходы по расписанию + уведомления и напоминания.
   - Экспорт истории в `CSV` и поддержка международных валют **ISO 4217**.

---

## ☁️ Безопасная установка на VPS (Ubuntu / Zomro) 24/7 рядом с работающим сайтом

Бот полностью изолирован и **не затрагивает существующий сайт, веб-сервер (Nginx/Apache) или базы данных**:
- Код и зависимости ставятся в отдельную папку `/opt/jnl-bot/.venv`.
- База данных бота хранится в локальном файле `/opt/jnl-bot/data/finance_bot.db` (SQLite).
- Бот работает через исходящий Long Polling к `api.telegram.org` (не занимает порты `80` / `443`).

### Пошаговая установка на VPS по SSH

Подключитесь к вашему VPS по SSH и выполните:

```bash
# 1. Клонируем репозиторий в отдельную директорию /opt/jnl-bot
sudo git clone https://github.com/JDiHapaleoN/TG-bot-JnL.git /opt/jnl-bot
sudo chown -R $USER:$USER /opt/jnl-bot
cd /opt/jnl-bot

# 2. Создаём изолированное виртуальное окружение и ставим зависимости
sudo apt-get update && sudo apt-get install -y python3-venv python3-pip
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

# 3. Создаём файл .env и вписываем BOT_TOKEN
cp .env.example .env
nano .env
```

Внутри `.env` укажите ваш токен (если веб-сервер Mini App на VPS не нужен, можно поставить `WEBAPP_PORT=0`):
```env
BOT_TOKEN=ваш_токен_бота
DATABASE_URL=sqlite+aiosqlite:///./data/finance_bot.db
WEBAPP_HOST=127.0.0.1
WEBAPP_PORT=8095
WEBAPP_URL=
```

```bash
# 4. Включаем автозапуск 24/7 через systemd
sudo cp /opt/jnl-bot/deploy/jnl-bot.service /etc/systemd/system/jnl-bot.service
sudo systemctl daemon-reload
sudo systemctl enable --now jnl-bot.service

# 5. Проверяем, что бот работает
sudo systemctl status jnl-bot.service
```

> ⚠️ **Важно:** перед запуском бота на VPS остановите локально запущенную копию на компьютере, так как с одним токеном Telegram позволяет держать активным только одно Long Polling соединение одновременно.

---

## 💻 Локальный запуск и тесты

```bash
cp .env.example .env
.venv/bin/pip install -r requirements.txt
.venv/bin/python main.py
```

Запуск тестов:
```bash
.venv/bin/python -m unittest discover -s tests -v
```
