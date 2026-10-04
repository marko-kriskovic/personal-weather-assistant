from typing import Annotated

import httpx
from fastapi import Depends, Request

from app.config import Settings, get_settings
from app.errors import ConfigurationError
from app.services.recommender import GroqRecommender
from app.services.weather import WeatherService

SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_http_client(request: Request) -> httpx.AsyncClient:
    return request.app.state.http_client


HttpClientDep = Annotated[httpx.AsyncClient, Depends(get_http_client)]


def get_weather_service(client: HttpClientDep, settings: SettingsDep) -> WeatherService:
    if not settings.openweather_api_key:
        raise ConfigurationError("OPENWEATHER_API_KEY is not configured.")
    return WeatherService(client, settings.openweather_api_key, settings.openweather_base_url)


def get_recommender(client: HttpClientDep, settings: SettingsDep) -> GroqRecommender:
    if not settings.groq_api_key:
        raise ConfigurationError("GROQ_API_KEY is not configured.")
    return GroqRecommender(
        client, settings.groq_api_key, settings.groq_model, settings.groq_base_url
    )
