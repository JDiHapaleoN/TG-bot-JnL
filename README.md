# Personal Finance Bot (JnL-Bot)

Telegram-бот + Telegram Mini App (WebApp) для быстрого учёта личных финансов (расходов, доходов, регулярных платежей и статистики) за 2–3 секунды с гарантией сохранности данных и строгой изоляцией (Least Privilege) на VPS.

---

## 🏛️ Архитектура и строгая изоляция данных

Код, конфигурация и пользовательские данные **физически разделены** и работают под выделенным непривилегированным системным пользователем `jnl-bot` (`User=jnl-bot`, `Group=jnl-bot`, `/usr/sbin/nologin`, без прав `root` и без `sudo`):

| Компонент | Канонический путь на сервере | Права / Режим systemd | Назначение |
|---|---|---|---|
| **Исходный код и `.venv`** | `/opt/jnl-bot/` (точка входа: `/opt/jnl-bot/main.py`) | `0755` / `ReadOnlyPaths` | Изолированный Git-репозиторий и виртуальное окружение Python (SQLite 3.51.3+) |
| **Постоянная база данных** | `/var/lib/jnl-bot/data/finance_bot.db` | `0700` / `ReadWritePaths` | Рабочая база данных SQLite (`journal_mode=WAL`, `synchronous=FULL`, `busy_timeout=15000`) |
| **Локальные резервные копии** | `/var/lib/jnl-bot/backups/` | `0700` / `ReadWritePaths` | Горячие онлайн-бэкапы через SQLite Online Backup API с SHA-256 манифестами |
| **Единый файл конфигурации** | `/var/lib/jnl-bot/.env` | `0600` / `ReadOnlyPaths` | Единственный канонический источник конфигурации и секретов в production |
| **Облачные копии** | S3-совместимое хранилище (опционально) | AES-256-GCM (PBKDF2 600k) | Клиентское шифрование с поддержкой заголовка `JNL-ENC1` и обратной совместимостью |

Каталоги клиентских сайтов и панели управления (`-/home`, `-/var/www`, `-/root`, `-/usr/local/hestia`, `-/etc/nginx`, `-/etc/apache2`, `-/etc/php`) заблокированы на уровне пространства имён ядра (`InaccessiblePaths`, `ProtectSystem=strict`, `ProtectHome=true`, `NoNewPrivileges=true`).

---

## ✨ Возможности

1. **Мгновенный учёт расходов и доходов (2–3 секунды)**:
   - `5` → Расход `− €5.00`
   - `12.50` или `12,50` → Расход `− €12.50`
   - `5 | Обед в McDonald's` или `5 Обед` → Расход `− €5.00` с категорией и описанием
   - `+1500` → Доход `+ €1,500.00`
   - `+200 Стипендия` → Доход `+ €200.00`
2. **Регистрация и настройка (`/start`)**:
   - Язык (`Русский` / `English`).
   - Имя пользователя.
   - Номер телефона через кнопку **Telegram Contact**.
   - Офлайн-геолокация: определение страны, валюты (ISO 4217) и часового пояса без внешних API.
3. **Безопасность и целостность данных**:
   - SQLite **3.51.3+** (с официальным исправлением уязвимости гонки `WAL-reset`) в режиме **WAL** + `PRAGMA synchronous=FULL`.
   - Точные расчёты сумм через **Python Decimal** (без ошибок округления `float`).
   - Идемпотентность Telegram Updates (`ProcessedUpdate`) и транзакций (`idempotency_key`).
   - Изоляция пользователей на уровне БД (проверка владения для всех CRUD-операций).
   - Защита от split-brain через эксклюзивную блокировку `/var/lib/jnl-bot/data/bot.lock` (`fcntl.flock`).
   - Маскирование токенов и ключей шифрования в логах (`SecretRedactingFilter`).

---

## ☁️ Безопасная установка на Ubuntu VPS

> **Правило безопасности:** Никогда не передавайте `BOT_TOKEN` аргументом командной строки (аргументы процессов видны в `ps aux` и `/proc`). Инсталлятор автоматически отклонит запуск, если ему переданы аргументы командной строки, и никогда не запускает `apt-get` автоматически.

### Шаг 1. Подготовка секрета в каноническом файле `/var/lib/jnl-bot/.env`
```bash
sudo install -d -m 750 /var/lib/jnl-bot
sudo install -m 600 /dev/null /var/lib/jnl-bot/.env
sudo nano /var/lib/jnl-bot/.env
```
Минимальное содержимое `/var/lib/jnl-bot/.env`:
```env
APP_ENV=production
BOT_TOKEN=ваш_токен_от_BotFather
DATABASE_URL=sqlite+aiosqlite:////var/lib/jnl-bot/data/finance_bot.db
BACKUP_DIR=/var/lib/jnl-bot/backups
WEBAPP_HOST=127.0.0.1
WEBAPP_PORT=0
S3_BACKUP_ENABLED=false
```

### Шаг 2. Запуск изолированного инсталлятора (без аргументов)
```bash
git clone https://github.com/JDiHapaleoN/TG-bot-JnL.git /opt/jnl-bot
sudo /opt/jnl-bot/deploy/install_vps.sh
```
*(Если `/var/lib/jnl-bot/.env` ещё не был создан, скрипт в интерактивном терминале запросит `BOT_TOKEN` со скрытым вводом `read -s`).*

Что делает `install_vps.sh`:
1. Проверяет наличие `python3`, `python3-venv` и `git` без автоматического запуска `apt-get`.
2. Проверяет канонические пути (`realpath`), отсутствие неожиданных симлинков и точек монтирования (`mountpoint`).
3. Создаёт непривилегированного системного пользователя и группу `jnl-bot`.
4. Создаёт верифицированный бэкап существующей базы данных перед любыми операциями с репозиторием.
5. Собирает и проверяет изолированный SQLite 3.51.3+ внутри `/opt/jnl-bot/.venv` и выполняет fail-closed проверку `python -m bot.database.check_sqlite`.
6. Устанавливает и проверяет через `systemd-analyze verify` unit-файлы:
   - `jnl-bot.service` (`ExecStart=/opt/jnl-bot/.venv/bin/python /opt/jnl-bot/main.py`, `User=jnl-bot`).
   - `jnl-bot-updater.service` (`User=jnl-bot`, запускается вручную при остановленном боте).
   - `jnl-bot-updater.timer` (**отключён по умолчанию**; расписание при ручном включении: `OnBootSec=15min`, `OnUnitActiveSec=1h`, однако для серверов с сайтом клиента рекомендуется только контролируемое обновление).

---

## 🔄 Контролируемая процедура обновления (Controlled Update Workflow)

Чтобы полностью исключить привилегированный `sudo` внутри песочницы `NoNewPrivileges=true` и гарантировать эксклюзивный доступ к базе данных при миграциях, обновление выполняется в 5 контролируемых шагов:

```bash
# 1. Администратор останавливает ТОЛЬКО сервис бота
sudo systemctl stop jnl-bot.service

# 2. Запуск непривилегированного апдейтера от имени пользователя jnl-bot (без root и без sudo)
sudo -u jnl-bot /opt/jnl-bot/deploy/auto_update.sh
# (или через systemd: sudo systemctl start jnl-bot-updater.service)

# 3. Апдейтер проверяет, что бот остановлен, создаёт верифицированный pre-update бэкап,
#    обновляет код и .venv, тестирует миграции на изолированной копии, применяет миграции,
#    проверяет целостность БД и прогоняет тесты. При ошибке после старта миграции БД
#    автоматически откатывает И код, И базу данных из pre-update бэкапа.

# 4. После успешного завершения апдейтера администратор запускает бота
sudo systemctl start jnl-bot.service

# 5. Проверка статуса сервиса
sudo systemctl status jnl-bot.service --no-pager
```

---

## 🔐 Настройка облачного бэкапа (S3) и безопасное восстановление

В файле `/var/lib/jnl-bot/.env` укажите параметры вашего S3-хранилища:

```env
S3_BACKUP_ENABLED=true
S3_ENDPOINT_URL=https://s3.eu-central-1.amazonaws.com
S3_ACCESS_KEY_ID=ваш_access_key
S3_SECRET_ACCESS_KEY=ваш_secret_key
S3_BUCKET_NAME=название_bucket
S3_REGION_NAME=eu-central-1
S3_ENCRYPTION_KEY=секретная_фраза_минимум_32_символа
S3_RETENTION_DAYS=30
S3_PBKDF2_ITERATIONS=600000
ADMIN_TELEGRAM_ID=ваш_telegram_id
```

### Команды работы с облачным бэкапом (от имени `jnl-bot`):
```bash
# Загрузка последней локальной резервной копии в S3
sudo -u jnl-bot /opt/jnl-bot/.venv/bin/python -m bot.services.cloud_backup --upload-latest

# Список зашифрованных копий в S3
sudo -u jnl-bot /opt/jnl-bot/.venv/bin/python -m bot.services.cloud_backup --list
```

### ⚠️ Безопасное восстановление из резервной копии
**Никогда не восстанавливайте облачный бэкап напрямую поверх активной рабочей базы данных.** Всегда восстанавливайте копию сначала во временный изолированный файл и проверяйте её целостность:

```bash
# 1. Скачивание и расшифровка во временный изолированный файл (бот может продолжать работу)
sudo -u jnl-bot /opt/jnl-bot/.venv/bin/python -m bot.services.cloud_backup \
    --restore-latest \
    --target /var/lib/jnl-bot/backups/restored_verify.db

# 2. Проверка целостности (PRAGMA integrity_check, SHA-256 и количество записей)
sudo -u jnl-bot /opt/jnl-bot/.venv/bin/python -m bot.services.backup \
    --verify /var/lib/jnl-bot/backups/restored_verify.db

# 3. Только после успешной верификации: остановка бота и контролируемый перенос в рабочую БД
sudo systemctl stop jnl-bot.service
sudo -u jnl-bot /opt/jnl-bot/.venv/bin/python -m bot.services.backup \
    --restore /var/lib/jnl-bot/backups/restored_verify.db \
    --target /var/lib/jnl-bot/data/finance_bot.db
sudo rm -f /var/lib/jnl-bot/backups/restored_verify.db*
sudo systemctl start jnl-bot.service
```

---

## 🛠️ Диагностика SQLite и тестирование

Проверка runtime-версии SQLite (>= 3.51.3), директив PRAGMA и конкурентной записи WAL:
```bash
/opt/jnl-bot/.venv/bin/python -m bot.database.check_sqlite
```

Запуск полного набора автоматизированных тестов (все тесты используют исключительно изолированные временные базы данных):
```bash
/opt/jnl-bot/.venv/bin/python -m unittest discover -s tests -v
```
