"""Thin async wrapper around the Anthropic SDK.

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
    """Return a singleton AsyncAnthropic client, or None if no key is configured."""
    global _client  # noqa: PLW0603
    if not settings.CLAUDE_API_KEY:
        return None
    if _client is None:
        try:
            import anthropic  # noqa: PLC0415

            _client = anthropic.AsyncAnthropic(api_key=settings.CLAUDE_API_KEY)
        except ImportError:
            logger.warning("anthropic package not installed — Claude features disabled")
    return _client


async def generate_text(
    prompt: str,
    *,
    system: str = "You are a helpful environmental compliance assistant.",
    max_tokens: int = 500,
    model: str | None = None,
) -> str | None:
    """Call Claude and return the text response, or None on failure/missing key."""
    client = get_anthropic_client()
    if client is None:
        return None

    _model = model or settings.CLAUDE_MODEL

    async def _call() -> str:
        msg = await client.messages.create(
            model=_model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text.strip()

    try:
        return await _call()
    except Exception as exc:
        logger.warning("Claude API call failed (%s) — retrying once", exc)
        try:
            return await _call()
        except Exception as exc2:
            logger.error("Claude API retry also failed: %s", exc2)
            return None
