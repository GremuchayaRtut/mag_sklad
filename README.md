# МагСклад

**МагСклад** — SaaS система управления товарами для розничных магазинов.  
Позволяет вести учёт товаров, остатков, поставок, продаж и инвентаризаций в нескольких торговых точках.

---

## Быстрый старт с Docker

### 1. Скопируйте переменные окружения

```bash
cp .env.example .env
```

Заполните обязательные поля в `.env` (как минимум `POSTGRES_PASSWORD` и `SECRET_KEY`).

### 2. Запустите контейнеры

```bash
docker-compose up --build
```

### 3. Примените миграции

```bash
docker-compose exec app alembic upgrade head
```

После этого API доступен по адресу **http://localhost** (через nginx) или **http://localhost:8000** (напрямую).

---

## Переменные окружения

| Переменная | Описание |
|---|---|
| `DATABASE_URL` | Строка подключения к PostgreSQL (`postgresql+asyncpg://...`) |
| `SECRET_KEY` | Секретный ключ для подписи JWT-токенов |
| `GOOGLE_CLIENT_ID` | OAuth 2.0 Client ID от Google |
| `GOOGLE_CLIENT_SECRET` | OAuth 2.0 Client Secret от Google |
| `CLOUDFLARE_R2_BUCKET` | Имя бакета Cloudflare R2 для хранения фото |
| `CLOUDFLARE_R2_ACCESS_KEY` | Access Key для R2 |
| `CLOUDFLARE_R2_SECRET_KEY` | Secret Key для R2 |
| `CLOUDFLARE_R2_ENDPOINT` | Endpoint URL бакета R2 |
| `TELEGRAM_BOT_TOKEN` | Токен Telegram-бота для уведомлений |
| `TELEGRAM_ADMIN_CHAT_ID` | ID чата администратора в Telegram |
| `POSTGRES_DB` | Имя базы данных (для docker-compose, по умолчанию `mag_sklad`) |
| `POSTGRES_USER` | Пользователь БД (по умолчанию `mag_sklad`) |
| `POSTGRES_PASSWORD` | Пароль пользователя БД |

---

## Документация API

После запуска документация доступна по адресам:

- **Swagger UI**: http://localhost/docs
- **ReDoc**: http://localhost/redoc

---

## Продакшен-запуск

```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

---

## Структура проекта

```
app/
├── main.py          # Точка входа FastAPI
├── config.py        # Настройки через pydantic-settings
├── database.py      # Async SQLAlchemy engine и сессия
├── models/          # SQLAlchemy ORM-модели
├── schemas/         # Pydantic схемы запросов/ответов
├── api/v1/          # API роутеры (v1)
├── core/            # Безопасность, исключения
└── utils/           # Пагинация и утилиты
alembic/             # Миграции базы данных
docker/              # Dockerfile и конфиг nginx
```
