"""
S3 — Public Citizen Advisory Portal tests.

The public summary endpoint must be reachable WITHOUT any authentication token.
"""

import pytest
from httpx import AsyncClient

DELHI_CITY_ID = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
NONEXISTENT_ID = "00000000-0000-0000-0000-000000000000"


@pytest.mark.asyncio
async def test_public_summary_no_auth_required(client: AsyncClient) -> None:
    """Core S3 requirement: endpoint is reachable with zero credentials."""
    resp = await client.get(f"/api/v1/cities/{DELHI_CITY_ID}/public/summary")
    assert resp.status_code == 200
    assert resp.json()["error"] is None


@pytest.mark.asyncio
async def test_public_summary_response_shape(client: AsyncClient) -> None:
    resp = await client.get(f"/api/v1/cities/{DELHI_CITY_ID}/public/summary")
    data = resp.json()["data"]

    assert "city" in data
    assert data["city"]["id"] == DELHI_CITY_ID
    assert data["city"]["name"] == "Delhi"

    assert "aqi" in data
    assert "aqi_level" in data
    assert data["aqi_level"] in (
        "Good",
        "Satisfactory",
        "Moderate",
        "Poor",
        "Very Poor",
        "Severe",
        "Unknown",
    )

    assert "pollutants" in data
    pollutants = data["pollutants"]
    assert "pm25" in pollutants
    assert "pm10" in pollutants
    assert "no2" in pollutants

    assert "advisories" in data
    assert isinstance(data["advisories"], dict)

    assert "all_cities" in data
    assert isinstance(data["all_cities"], list)
    assert any(c["name"] == "Delhi" for c in data["all_cities"])


@pytest.mark.asyncio
async def test_public_summary_aqi_from_seeded_readings(client: AsyncClient) -> None:
    """With seeded station readings, AQI should be a non-null integer."""
    resp = await client.get(f"/api/v1/cities/{DELHI_CITY_ID}/public/summary")
    data = resp.json()["data"]
    # Seeded readings guarantee a real AQI value
    assert data["aqi"] is not None
    assert isinstance(data["aqi"], int)
    assert 0 < data["aqi"] <= 500


@pytest.mark.asyncio
async def test_public_summary_aqi_level_matches_value(client: AsyncClient) -> None:
    """aqi_level must be consistent with the numeric aqi."""
    resp = await client.get(f"/api/v1/cities/{DELHI_CITY_ID}/public/summary")
    data = resp.json()["data"]
    aqi = data["aqi"]
    level = data["aqi_level"]
    if aqi is None:
        assert level == "Unknown"
    elif aqi <= 50:
        assert level == "Good"
    elif aqi <= 100:
        assert level == "Satisfactory"
    elif aqi <= 200:
        assert level == "Moderate"
    elif aqi <= 300:
        assert level == "Poor"
    elif aqi <= 400:
        assert level == "Very Poor"
    else:
        assert level == "Severe"


@pytest.mark.asyncio
async def test_public_summary_unknown_city_404(client: AsyncClient) -> None:
    resp = await client.get(f"/api/v1/cities/{NONEXISTENT_ID}/public/summary")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_public_summary_last_updated_iso_format(client: AsyncClient) -> None:
    """last_updated, when present, must be a parseable ISO datetime string."""
    from datetime import datetime

    resp = await client.get(f"/api/v1/cities/{DELHI_CITY_ID}/public/summary")
    last_updated = resp.json()["data"]["last_updated"]
    if last_updated is not None:
        # Should not raise
        datetime.fromisoformat(last_updated.replace("Z", "+00:00"))
