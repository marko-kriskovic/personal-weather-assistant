"""End-to-end API tests. External HTTP calls are mocked with respx."""

import datetime as dt

import pytest

from app.config import Settings, get_settings
from tests.conftest import (
    GEOCODE_ZAGREB,
    GROQ_BASE,
    OWM_BASE,
    RECOMMENDATION,
    groq_completion,
    make_forecast,
    utc_today,
)


@pytest.fixture
def owm_ok(mock_api):
    mock_api.get(f"{OWM_BASE}/geo/1.0/direct").respond(json=GEOCODE_ZAGREB)
    mock_api.get(f"{OWM_BASE}/data/2.5/forecast").respond(json=make_forecast(utc_today()))
    return mock_api


def tomorrow() -> str:
    return (utc_today() + dt.timedelta(days=1)).isoformat()


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_recommendation_happy_path(client, owm_ok):
    owm_ok.post(f"{GROQ_BASE}/chat/completions").respond(json=groq_completion(RECOMMENDATION))

    response = client.post("/api/v1/recommendations", json={"city": "Zagreb", "date": tomorrow()})

    assert response.status_code == 200
    data = response.json()
    assert data["location"]["name"] == "Zagreb"
    assert data["units"] == "metric"
    assert data["weather"]["date"] == tomorrow()
    assert data["weather"]["temp_max"] == 17.0
    assert len(data["weather"]["hourly"]) == 8
    assert data["recommendation"] == RECOMMENDATION


def test_weather_endpoint(client, owm_ok):
    response = client.get("/api/v1/weather", params={"city": "Zagreb", "date": tomorrow(), "units": "imperial"})

    assert response.status_code == 200
    assert response.json()["units"] == "imperial"
    assert response.json()["weather"]["conditions"] == ["scattered clouds", "light rain"]


@pytest.mark.parametrize(
    "body",
    [
        {"date": "2026-10-05"},
        {"city": "Zagreb"},
        {"city": "", "date": "2026-10-05"},
        {"city": "Zagreb", "date": "05.10.2026"},
        {"city": "Zagreb", "date": "2026-10-05", "units": "kelvin"},
    ],
)
def test_invalid_request_body(client, mock_api, body):
    assert client.post("/api/v1/recommendations", json=body).status_code == 422


def test_date_too_far_ahead(client, mock_api):
    far = (utc_today() + dt.timedelta(days=14)).isoformat()

    response = client.post("/api/v1/recommendations", json={"city": "Zagreb", "date": far})

    assert response.status_code == 422
    assert "5 days ahead" in response.json()["detail"]


def test_city_not_found(client, mock_api):
    mock_api.get(f"{OWM_BASE}/geo/1.0/direct").respond(json=[])

    response = client.post("/api/v1/recommendations", json={"city": "Atlantis", "date": tomorrow()})

    assert response.status_code == 404
    assert "Atlantis" in response.json()["detail"]


def test_groq_failure_returns_502(client, owm_ok):
    owm_ok.post(f"{GROQ_BASE}/chat/completions").respond(500)

    response = client.post("/api/v1/recommendations", json={"city": "Zagreb", "date": tomorrow()})

    assert response.status_code == 502
    assert "Groq" in response.json()["detail"]


def test_missing_api_keys_returns_503(client, mock_api):
    client.app.dependency_overrides[get_settings] = lambda: Settings(_env_file=None)

    response = client.post("/api/v1/recommendations", json={"city": "Zagreb", "date": tomorrow()})

    assert response.status_code == 503
    assert "OPENWEATHER_API_KEY" in response.json()["detail"]


def test_cors_allows_frontend_origin(client):
    response = client.options(
        "/api/v1/recommendations",
        headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "POST"},
    )

    assert response.status_code == 200
    assert "access-control-allow-origin" in response.headers
