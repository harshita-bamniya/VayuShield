"""Tests for Module 09 — Groq API Integration.

All tests mock the Groq client — no real API calls are made.
The key behaviour under test:
  - Evidence brief falls back to template when key absent / AI returns None
  - Evidence brief uses AI text when Groq responds
  - Advisory body uses AI text when Groq responds
  - /ai-brief endpoint returns updated item
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.core import llm_client as _llm_client

DELHI_CITY_ID = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"


# ── helper ────────────────────────────────────────────────────────────────────


def _mock_claude_response(text: str):
    """Return a mock that behaves like groq.AsyncGroq().chat.completions.create()."""
    message = MagicMock()
    message.content = text

    choice = MagicMock()
    choice.message = message

    completion = MagicMock()
    completion.choices = [choice]

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value=completion)
    return mock_client


# ── generate_text unit tests ──────────────────────────────────────────────────


@pytest.mark.anyio
async def test_generate_text_returns_none_when_no_key():
    """generate_text returns None when GROQ_API_KEY is empty."""
    from app.core import claude_client

    with patch.object(claude_client, "get_anthropic_client", return_value=None):
        result = await claude_client.generate_text("Hello")
    assert result is None


@pytest.mark.anyio
async def test_generate_text_returns_ai_text_when_client_available():
    """generate_text returns the AI response text when client is available."""
    from app.core import claude_client

    mock_client = _mock_claude_response("AI generated enforcement brief text.")

    with patch.object(_llm_client, "get_groq_client", return_value=mock_client):
        result = await claude_client.generate_text("Generate a brief.")

    assert result == "AI generated enforcement brief text."


@pytest.mark.anyio
async def test_generate_text_falls_back_on_exception():
    """generate_text returns None if both the initial call and retry fail."""
    from app.core import claude_client

    mock_client = MagicMock()
    mock_client.messages.create = AsyncMock(side_effect=RuntimeError("API down"))

    with patch.object(claude_client, "get_anthropic_client", return_value=mock_client):
        result = await claude_client.generate_text("Generate a brief.")

    assert result is None


# ── evidence brief unit tests ─────────────────────────────────────────────────


@pytest.mark.anyio
async def test_evidence_brief_uses_ai_text():
    """_generate_evidence_brief returns AI text when Claude is available."""
    from app.modules.enforcement.service import _generate_evidence_brief

    ai_text = "AI-generated 5-sentence enforcement brief for testing purposes."
    mock_client = _mock_claude_response(ai_text)

    with patch.object(_llm_client, "get_groq_client", return_value=mock_client):
        result = await _generate_evidence_brief(
            source_name="Delhi Power Plant",
            source_type="industrial",
            permit_status="expired",
            priority_score=0.85,
            attribution_pct=35.0,
            peak_aqi_24h=320.0,
            days_since=45,
        )

    assert result == ai_text


@pytest.mark.anyio
async def test_evidence_brief_falls_back_to_template_when_no_key():
    """_generate_evidence_brief falls back to template when Claude unavailable."""
    from app.core import claude_client
    from app.modules.enforcement.service import _generate_evidence_brief

    with patch.object(claude_client, "get_anthropic_client", return_value=None):
        result = await _generate_evidence_brief(
            source_name="Test Source",
            source_type="vehicular",
            permit_status="active",
            priority_score=0.40,
            attribution_pct=15.0,
            peak_aqi_24h=180.0,
            days_since=10,
        )

    assert "Test Source" in result
    assert "vehicular" in result
    assert "0.40" in result


# ── advisory body unit tests ──────────────────────────────────────────────────


@pytest.mark.anyio
async def test_advisory_body_uses_ai_text():
    """_build_advisory_text returns AI body when Claude is available."""
    from app.modules.advisory.service import _build_advisory_text

    ai_body = "AI-generated advisory body text about air quality."
    mock_client = _mock_claude_response(ai_body)

    with patch.object(_llm_client, "get_groq_client", return_value=mock_client):
        title, body = await _build_advisory_text("en", "Poor", "vehicular", 260)

    assert body == ai_body
    assert "Poor" in title or "Warning" in title  # title still comes from template


@pytest.mark.anyio
async def test_advisory_body_falls_back_to_template():
    """_build_advisory_text falls back to template when Claude unavailable."""
    from app.core import claude_client
    from app.modules.advisory.service import _build_advisory_text

    with patch.object(claude_client, "get_anthropic_client", return_value=None):
        title, body = await _build_advisory_text("en", "Moderate", "vehicular", 180)

    assert "180" in body
    assert "vehicular" in body


# ── API endpoint tests ────────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_ai_brief_endpoint_requires_auth(client: AsyncClient):
    resp = await client.post(f"/api/v1/cities/{DELHI_CITY_ID}/enforcement/nonexistent-id/ai-brief")
    assert resp.status_code == 401


@pytest.mark.anyio
async def test_ai_brief_endpoint_not_found(client: AsyncClient, sysadmin_token: str):
    resp = await client.post(
        f"/api/v1/cities/{DELHI_CITY_ID}/enforcement/00000000-0000-0000-0000-000000000000/ai-brief",
        headers={"Authorization": f"Bearer {sysadmin_token}"},
    )
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_ai_brief_endpoint_updates_brief(client: AsyncClient, sysadmin_token: str):
    """Fetch the first enforcement item, then call ai-brief with a mocked Claude."""
    from app.core import claude_client

    # Get any existing enforcement item
    queue_resp = await client.get(
        f"/api/v1/cities/{DELHI_CITY_ID}/enforcement",
        headers={"Authorization": f"Bearer {sysadmin_token}"},
    )
    assert queue_resp.status_code == 200
    items = queue_resp.json()["data"]["items"]
    if not items:
        pytest.skip("No enforcement queue items seeded")

    item_id = items[0]["id"]
    ai_text = "Mocked AI enforcement brief — five professional sentences about compliance."
    mock_client = _mock_claude_response(ai_text)

    with patch.object(claude_client, "get_anthropic_client", return_value=mock_client):
        resp = await client.post(
            f"/api/v1/cities/{DELHI_CITY_ID}/enforcement/{item_id}/ai-brief",
            headers={"Authorization": f"Bearer {sysadmin_token}"},
        )

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["evidence_brief_text"] == ai_text
