import datetime as dt
import json

import httpx
import pytest

from app.errors import UpstreamServiceError
from app.models import Location
from app.services.recommender import GroqRecommender, build_user_prompt
from app.services.weather import aggregate_forecast
from tests.conftest import GROQ_BASE, RECOMMENDATION, groq_completion, make_forecast

DAY = dt.date(2026, 10, 4)
LOCATION = Location(name="Zagreb", country="HR", state="City of Zagreb", lat=45.81, lon=15.98)
WEATHER = aggregate_forecast(make_forecast(DAY), DAY)


@pytest.fixture
async def recommender():
    async with httpx.AsyncClient() as client:
        yield GroqRecommender(client, "groq-key", "test-model", GROQ_BASE)


async def test_returns_parsed_recommendation(recommender, mock_api):
    route = mock_api.post(f"{GROQ_BASE}/chat/completions").respond(json=groq_completion(RECOMMENDATION))

    result = await recommender.recommend(LOCATION, WEATHER, "metric")

    assert result.model_dump() == RECOMMENDATION
    request = route.calls.last.request
    assert request.headers["Authorization"] == "Bearer groq-key"
    body = json.loads(request.content)
    assert body["model"] == "test-model"
    assert body["response_format"] == {"type": "json_object"}
    assert body["messages"][0]["role"] == "system"
    assert "Zagreb, City of Zagreb, HR" in body["messages"][1]["content"]


async def test_tips_are_optional(recommender, mock_api):
    content = {k: v for k, v in RECOMMENDATION.items() if k != "tips"}
    mock_api.post(f"{GROQ_BASE}/chat/completions").respond(json=groq_completion(content))

    result = await recommender.recommend(LOCATION, WEATHER)

    assert result.tips == []


@pytest.mark.parametrize(
    "completion",
    [
        groq_completion("not json at all"),
        groq_completion({"summary": "missing lists"}),
        {"choices": []},
        {"unexpected": True},
    ],
)
async def test_malformed_response(recommender, mock_api, completion):
    mock_api.post(f"{GROQ_BASE}/chat/completions").respond(json=completion)

    with pytest.raises(UpstreamServiceError, match="unexpected response format"):
        await recommender.recommend(LOCATION, WEATHER)


async def test_invalid_api_key(recommender, mock_api):
    mock_api.post(f"{GROQ_BASE}/chat/completions").respond(401)

    with pytest.raises(UpstreamServiceError, match="API key"):
        await recommender.recommend(LOCATION, WEATHER)


async def test_rate_limited(recommender, mock_api):
    mock_api.post(f"{GROQ_BASE}/chat/completions").respond(429, text="rate limit")

    with pytest.raises(UpstreamServiceError, match="HTTP 429"):
        await recommender.recommend(LOCATION, WEATHER)


async def test_network_error(recommender, mock_api):
    mock_api.post(f"{GROQ_BASE}/chat/completions").mock(side_effect=httpx.ReadTimeout("slow"))

    with pytest.raises(UpstreamServiceError, match="Could not reach Groq"):
        await recommender.recommend(LOCATION, WEATHER)


@pytest.mark.parametrize("units, temp, wind", [("metric", "°C", "m/s"), ("imperial", "°F", "mph")])
def test_user_prompt_mentions_units(units, temp, wind):
    prompt = build_user_prompt(LOCATION, WEATHER, units)

    assert temp in prompt and wind in prompt
    assert "Sunday, 2026-10-04" in prompt
    assert '"temp_max"' in prompt
