"""WhatsApp delivery connector — Twilio WhatsApp Business API.

When TWILIO_ENABLED=true: sends a real WhatsApp message via Twilio.
When TWILIO_ENABLED=false (default): returns a realistic mock delivery log
so the integration is demonstrable without live credentials.
"""

from datetime import UTC, datetime

import httpx

from app.core.config import settings
from app.core.logging import logger


def _mock_phone(lang: str) -> str:
    """Return a redacted demo phone number per language region."""
    return {
        "hi": "+91-98765-XXXXX",
        "kn": "+91-80432-XXXXX",
        "ta": "+91-44987-XXXXX",
    }.get(lang, "+91-11234-XXXXX")


def _truncate(text: str, max_chars: int = 1000) -> str:
    return text if len(text) <= max_chars else text[:max_chars] + "…"


async def send_whatsapp_advisory(
    *,
    phone: str | None,
    message: str,
    advisory_id: str,
    language: str = "en",
) -> dict:
    """Send a WhatsApp message and return a delivery result dict.

    Returns:
        {
          "status": "sent" | "mock" | "error",
          "channel": "whatsapp",
          "phone": str,
          "sent_at": ISO-8601 str,
          "mock": bool,
          "sid": str | None,   # Twilio message SID when real
          "error": str | None,
        }
    """
    target_phone = phone or settings.TWILIO_DEFAULT_PHONE or _mock_phone(language)
    sent_at = datetime.now(UTC).isoformat()

    if not settings.TWILIO_ENABLED:
        logger.info(
            "WhatsApp mock delivery (TWILIO_ENABLED=false)",
            advisory_id=advisory_id,
            language=language,
            phone=target_phone,
        )
        return {
            "status": "mock",
            "channel": "whatsapp",
            "phone": target_phone,
            "sent_at": sent_at,
            "mock": True,
            "sid": f"MOCK_SM_{advisory_id[:8].upper()}",
            "error": None,
        }

    # Real Twilio send
    url = f"https://api.twilio.com/2010-04-01/Accounts/{settings.TWILIO_ACCOUNT_SID}/Messages.json"
    payload = {
        "From": f"whatsapp:{settings.TWILIO_WHATSAPP_FROM}",
        "To": f"whatsapp:{target_phone}",
        "Body": _truncate(message),
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                url,
                data=payload,
                auth=(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN),
            )
        if resp.status_code in (200, 201):
            sid = resp.json().get("sid")
            logger.info(
                "WhatsApp sent via Twilio",
                advisory_id=advisory_id,
                sid=sid,
                phone=target_phone,
            )
            return {
                "status": "sent",
                "channel": "whatsapp",
                "phone": target_phone,
                "sent_at": sent_at,
                "mock": False,
                "sid": sid,
                "error": None,
            }
        error_msg = resp.text[:200]
        logger.warning(
            "Twilio returned non-2xx",
            status=resp.status_code,
            body=error_msg,
        )
        return {
            "status": "error",
            "channel": "whatsapp",
            "phone": target_phone,
            "sent_at": sent_at,
            "mock": False,
            "sid": None,
            "error": f"Twilio HTTP {resp.status_code}: {error_msg}",
        }
    except Exception as exc:
        logger.warning("WhatsApp send failed", error=str(exc))
        return {
            "status": "error",
            "channel": "whatsapp",
            "phone": target_phone,
            "sent_at": sent_at,
            "mock": False,
            "sid": None,
            "error": str(exc),
        }
