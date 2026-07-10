"""Thin async wrapper around the Groq SDK.

Usage:
    from app.core.claude_client import generate_text

    text = await generate_text(prompt, system="...")
    if text is None:
        text = fallback_template_string

All functions return None (never raise) when the key is absent or the API
call fails — callers are expected to fall back to template-based text.
"""

from __future__ import annotations

import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

_client = None


def get_anthropic_client():
    """Return a singleton Groq async client, or None if no key is configured."""
    global _client  # noqa: PLW0603
    if not settings.GROQ_API_KEY:
        return None
    if _client is None:
        try:
            from groq import AsyncGroq  # noqa: PLC0415

            _client = AsyncGroq(api_key=settings.GROQ_API_KEY)
        except ImportError:
            logger.warning("groq package not installed — AI features disabled")
    return _client


async def generate_text(
    prompt: str,
    *,
    system: str = "You are a helpful environmental compliance assistant.",
    max_tokens: int = 500,
    model: str | None = None,
) -> str | None:
    """Call Groq and return the text response, or None on failure/missing key."""
    client = get_anthropic_client()
    if client is None:
        return None

    _model = model or settings.GROQ_MODEL

    async def _call() -> str:
        resp = await client.chat.completions.create(
            model=_model,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
        )
        return resp.choices[0].message.content.strip()

    try:
        return await _call()
    except Exception as exc:
        logger.warning("Groq API call failed (%s) — retrying once", exc)
        try:
            return await _call()
        except Exception as exc2:
            logger.error("Groq API retry also failed: %s", exc2)
            return None
