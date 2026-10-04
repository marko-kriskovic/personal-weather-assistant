import datetime as dt
import json

import pytest
import respx
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.main import create_app

OWM_BASE = "https://api.openweathermap.org"
GROQ_BASE = "https://api.groq.com/openai/v1"


def utc_today() -> dt.date:
    return dt.datetime.now(dt.timezone.utc).date()


def make_forecast(start: dt.date, days: int = 5, tz_offset_seconds: int = 0) -> dict:
    """Build an OpenWeatherMap-style 5 day / 3 hour forecast payload.

    Entries start at 00:00 UTC on `start`. Temperature rises through the day
    (10 + hour/3 degrees); the 15:00 UTC slot is rainy.
    """
    start_dt = dt.datetime.combine(start, dt.time(0), tzinfo=dt.timezone.utc)
    items = []
    for i in range(days * 8):
        when = start_dt + dt.timedelta(hours=3 * i)
        rainy = when.hour == 15
        item = {
            "dt": int(when.timestamp()),
            "main": {"temp": 10 + when.hour / 3, "feels_like": 8 + when.hour / 3, "humidity": 60},
            "weather": [{"main": "Rain" if rainy else "Clouds",
                         "description": "light rain" if rainy else "scattered clouds"}],
            "wind": {"speed": 3.0 + (2 if rainy else 0)},
            "pop": 0.8 if rainy else 0.1,
        }
        if rainy:
            item["rain"] = {"3h": 1.25}
        items.append(item)
    return {"list": items, "city": {"name": "Zagreb", "timezone": tz_offset_seconds}}


GEOCODE_ZAGREB = [{"name": "Zagreb", "country": "HR", "state": "City of Zagreb", "lat": 45.81, "lon": 15.98}]

RECOMMENDATION = {
    "summary": "Cloudy with afternoon showers.",
    "clothing": ["Light jacket", "Waterproof shoes"],
    "activities": ["Visit the Museum of Broken Relationships", "Coffee on Tkalčićeva"],
    "tips": ["Carry an umbrella after 3 PM"],
}


def groq_completion(content: dict | str) -> dict:
    text = content if isinstance(content, str) else json.dumps(content)
    return {"choices": [{"index": 0, "message": {"role": "assistant", "content": text}}]}


@pytest.fixture
def settings() -> Settings:
    return Settings(
        _env_file=None,
        openweather_api_key="test-owm-key",
        groq_api_key="test-groq-key",
    )


@pytest.fixture
def client(settings):
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: settings
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def mock_api():
    """Intercepts all httpx traffic; unmatched requests fail the test."""
    with respx.mock(assert_all_called=False) as router:
        yield router
