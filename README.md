# Personal Finance Bot (JnL-Bot)

Telegram-бот + Telegram Mini App (WebApp) для быстрого учёта личных финансов (расходов, доходов, регулярных платежей и статистики) за 2–3 секунды с гарантией сохранности данных и отказоустойчивостью enterprise-уровня.

---

## 🏛️ Архитектура и хранение данных

Код и пользовательские данные **полностью разделены**:

| Компонент | Расположение на сервере | Назначение |
|---|---|---|
| **Исходный код** | `/opt/jnl-bot/` | Изолированный репозиторий Git и виртуальное окружение `.venv` |
| **Постоянная база данных** | `/var/lib/jnl-bot/data/finance_bot.db` | Рабочая база данных SQLite (режим WAL, synchronous=FULL) |
| **Локальные резервные копии** | `/var/backups/jnl-bot/` | Горячие онлайн-бэкапы с SHA-256 манифестами |
| **Облачные копии** | S3-совместимое хранилище | Клиентское AES-256-GCM шифрование, ротация 30 дней |

Символическая ссылка `/opt/jnl-bot/data -> /var/lib/jnl-bot/data` гарантирует обратную совместимость, защищая базу от перезаписи при любых Git-операциях.

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
   - SQLite в режиме **WAL** (Write-Ahead Logging) + `PRAGMA synchronous=FULL`.
   - Точные расчёты сумм через **Python Decimal** (без ошибок округления `float`).
   - Идемпотентность Telegram Updates (`ProcessedUpdate`) и транзакций (`idempotency_key`).
   - Изоляция пользователей на уровне БД (проверка владения для всех CRUD-операций).
   - Защита от split-brain через `bot.lock` (`fcntl.flock`).
   - Маскирование токенов и секретов в логах (`SecretRedactingFilter`).
4. **Резервное копирование и миграции**:
   - Обязательный верифицированный бэкап перед любым обновлением из GitHub.
   - Тестирование миграций на изолированной копии БД перед применением к рабочей базе.
   - Миграции по методологии **Expand and Contract** (100% обратная совместимость при rollback).
   - Клиентское шифрование AES-256-GCM для удалённого S3-хранилища.
   - Ротация бэкапов (хранение до 30 локальных и удалённых версий).

---

## ☁️ Установка на Ubuntu VPS (24/7 рядом с сайтом)

Установка полностью автоматизирована и безопасна для соседних сайтов, Nginx, HestiaCP и баз данных MySQL/PostgreSQL:

```bash
# Выполните от root на сервере:
curl -fsSL https://raw.githubusercontent.com/JDiHapaleoN/TG-bot-JnL/main/deploy/install_vps.sh | bash -s -- "ВАШ_ТОКЕН_БОТА"
```

Скрипт выполнит:
1. Создание защищённых системных директорий `/var/lib/jnl-bot/data` и `/var/backups/jnl-bot`.
2. Клонирование репозитория в `/opt/jnl-bot`.
3. Создание изолированного виртуального окружения `.venv`.
4. Настройку `.env` с привязкой к `/var/lib/jnl-bot/data/finance_bot.db`.
5. Проверку версии SQLite runtime и WAL-режима.
6. Регистрацию и запуск сервисов `systemd`:
   - `jnl-bot.service` (работа бота 24/7 с автоперезапуском при падении).
   - `jnl-bot-updater.timer` (безопасный опрос GitHub каждые 60 секунд с проверкой pre-update бэкапа и автоматическим rollback при ошибках).

---

## 🔐 Настройка независимого облачного бэкапа (S3)

Для защиты от полной потери сервера (Disaster Recovery) настройте отправку шифрованных копий в S3-совместимое хранилище (AWS S3, Cloudflare R2, MinIO, Yandex Object Storage).

В файле `/var/lib/jnl-bot/.env` (или `/opt/jnl-bot/.env`) добавьте параметры:

```env
S3_BACKUP_ENABLED=true
S3_ENDPOINT_URL=https://s3.eu-central-1.amazonaws.com # или URL Cloudflare R2 / Yandex Cloud
S3_ACCESS_KEY_ID=ваш_access_key
S3_SECRET_ACCESS_KEY=ваш_secret_key
S3_BUCKET_NAME=название_bucket
S3_REGION_NAME=eu-central-1
S3_ENCRYPTION_KEY=секретная_фраза_для_шифрования_aes256
S3_RETENTION_DAYS=30
```

Проверка работы S3:
```bash
# Загрузка последней резервной копии в облако
/opt/jnl-bot/.venv/bin/python -m bot.services.cloud_backup --upload-latest

# Просмотр резервных копий в облаке
/opt/jnl-bot/.venv/bin/python -m bot.services.cloud_backup --list

# Тестовое восстановление после катастрофы
/opt/jnl-bot/.venv/bin/python -m bot.services.cloud_backup --restore-latest --target /var/lib/jnl-bot/data/finance_bot.db
```

---

## 🛠️ Диагностика SQLite и тестирование

Проверка runtime-версии SQLite, директив PRAGMA и конкурентной записи WAL:
```bash
/opt/jnl-bot/.venv/bin/python -m bot.database.check_sqlite
```

Запуск всех автоматизированных тестов (36 тестов: юнит, аудит, инфраструктура):
```bash
/opt/jnl-bot/.venv/bin/python -m unittest discover -s tests -v
```
