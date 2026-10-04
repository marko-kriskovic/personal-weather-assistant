"""Groq-backed recommender (Groq exposes an OpenAI-compatible chat completions API)."""

import json

import httpx
from pydantic import ValidationError

from app.errors import UpstreamServiceError
from app.models import DailyWeather, Location, Recommendation, Units

SYSTEM_PROMPT = """You are a friendly personal weather assistant.
Given a location and a day's weather forecast, recommend what to wear and what to do.

Respond ONLY with a JSON object of this exact shape:
{
  "summary": "1-2 sentence plain-language overview of the day's weather",
  "clothing": ["specific clothing item or layering advice", ...],
  "activities": ["activity suggestion suited to the weather and location", ...],
  "tips": ["practical tip or warning, e.g. umbrella, sunscreen, hydration", ...]
}

Guidelines:
- Give 3-6 clothing items, 3-5 activities and 0-4 tips.
- Base advice on temperature range, feels-like, precipitation, wind and how the day changes hour by hour.
- Mix indoor and outdoor activities when the weather is mixed; prefer indoor ones in bad weather.
- Where natural, suggest activities typical for the given city.
- Keep each item short (under 20 words)."""


class GroqRecommender:
    def __init__(
        self,
        client: httpx.AsyncClient,
        api_key: str,
        model: str = "openai/gpt-oss-120b",
        base_url: str = "https://api.groq.com/openai/v1",
    ):
        self._client = client
        self._api_key = api_key
        self._model = model
        self._base_url = base_url.rstrip("/")

    async def recommend(
        self, location: Location, weather: DailyWeather, units: Units = "metric"
    ) -> Recommendation:
        payload = {
            "model": self._model,
            "temperature": 0.6,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_user_prompt(location, weather, units)},
            ],
        }
        try:
            response = await self._client.post(
                f"{self._base_url}/chat/completions",
                json=payload,
                headers={"Authorization": f"Bearer {self._api_key}"},
            )
        except httpx.RequestError as exc:
            raise UpstreamServiceError(f"Could not reach Groq: {exc}") from exc

        if response.status_code == 401:
            raise UpstreamServiceError("Groq rejected the API key.")
        if response.is_error:
            raise UpstreamServiceError(
                f"Groq returned HTTP {response.status_code}: {response.text[:200]}"
            )

        try:
            content = response.json()["choices"][0]["message"]["content"]
            return Recommendation.model_validate(json.loads(content))
        except (KeyError, IndexError, TypeError, json.JSONDecodeError, ValidationError) as exc:
            raise UpstreamServiceError("Groq returned an unexpected response format.") from exc


def build_user_prompt(location: Location, weather: DailyWeather, units: Units) -> str:
    temp_unit = "°C" if units == "metric" else "°F"
    wind_unit = "m/s" if units == "metric" else "mph"
    place = ", ".join(p for p in (location.name, location.state, location.country) if p)
    return (
        f"Location: {place}\n"
        f"Date: {weather.date.strftime('%A, %Y-%m-%d')}\n"
        f"Units: temperature in {temp_unit}, wind in {wind_unit}, precipitation in mm\n"
        f"Forecast:\n{weather.model_dump_json(indent=2)}"
    )
