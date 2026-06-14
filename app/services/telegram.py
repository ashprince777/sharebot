import logging
import httpx
from typing import Optional
from app.core.config import settings

logger = logging.getLogger(__name__)


async def send_telegram_message(
    message: str, chat_id: Optional[str] = None, parse_mode: str = "HTML"
) -> bool:
    """
    Send an asynchronous alert message via Telegram Bot API.
    Uses credentials from environment settings unless explicit overrides are passed.
    """
    token = settings.TELEGRAM_BOT_TOKEN
    target_chat = chat_id or settings.TELEGRAM_CHAT_ID

    if not token or not target_chat:
        logger.warning(
            "Telegram notifications bypassed. TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID is not configured."
        )
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": target_chat,
        "text": message,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            res_data = response.json()
            if not res_data.get("ok"):
                logger.error(f"Telegram returned error: {res_data.get('description')}")
                return False
            return True
    except httpx.HTTPStatusError as e:
        logger.error(f"Telegram HTTP error status {e.response.status_code}: {e.response.text}")
        return False
    except Exception as e:
        logger.error(f"Failed to send Telegram message: {str(e)}")
        return False
