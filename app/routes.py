import datetime as dt
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.dependencies import get_recommender, get_weather_service
from app.models import (
    RecommendationRequest,
    RecommendationResponse,
    Units,
    WeatherResponse,
)
from app.services.recommender import GroqRecommender
from app.services.weather import WeatherService

router = APIRouter(prefix="/api/v1")

ERROR_RESPONSES = {
    404: {"description": "City not found"},
    422: {"description": "Invalid input or date outside the forecast range"},
    502: {"description": "OpenWeatherMap or Groq failed"},
    503: {"description": "API keys not configured"},
}


@router.get("/weather", response_model=WeatherResponse, responses=ERROR_RESPONSES)
async def get_weather(
    weather_service: Annotated[WeatherService, Depends(get_weather_service)],
    city: Annotated[str, Query(min_length=1, max_length=100)],
    date: dt.date,
    units: Units = "metric",
) -> WeatherResponse:
    """Daily weather summary for a city and date (no AI recommendation)."""
    location, weather = await weather_service.get_daily_weather(city, date, units)
    return WeatherResponse(location=location, units=units, weather=weather)


@router.post("/recommendations", response_model=RecommendationResponse, responses=ERROR_RESPONSES)
async def create_recommendation(
    body: RecommendationRequest,
    weather_service: Annotated[WeatherService, Depends(get_weather_service)],
    recommender: Annotated[GroqRecommender, Depends(get_recommender)],
) -> RecommendationResponse:
    """Weather for a city and date plus clothing and activity recommendations."""
    location, weather = await weather_service.get_daily_weather(body.city, body.date, body.units)
    recommendation = await recommender.recommend(location, weather, body.units)
    return RecommendationResponse(
        location=location, units=body.units, weather=weather, recommendation=recommendation
    )
