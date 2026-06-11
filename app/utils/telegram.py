import httpx

from app.config import settings


async def send_telegram_message(text: str) -> None:
    if not settings.TELEGRAM_BOT_TOKEN:
        print(f"[TELEGRAM] {text}")
        return

    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": settings.TELEGRAM_ADMIN_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
    }
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            await client.post(url, json=payload)
    except Exception as exc:  # never let Telegram failures crash the app
        print(f"[TELEGRAM ERROR] {exc}")


async def notify_new_registration(user_email: str, business_name: str) -> None:
    text = (
        "🆕 <b>Новая регистрация — МагСклад</b>\n"
        f"📧 Email: {user_email}\n"
        f"🏪 Бизнес: {business_name}"
    )
    await send_telegram_message(text)


async def notify_error(error: str, context: str = "") -> None:
    text = (
        "🚨 <b>Ошибка — МагСклад</b>\n"
        f"📍 {context}\n"
        f"❌ {error}"
    )
    await send_telegram_message(text)
