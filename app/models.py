import datetime as dt
from typing import Literal

from pydantic import BaseModel, Field

Units = Literal["metric", "imperial"]


class RecommendationRequest(BaseModel):
    city: str = Field(min_length=1, max_length=100, examples=["Zagreb"])
    date: dt.date = Field(examples=["2026-10-05"])
    units: Units = "metric"


class Location(BaseModel):
    name: str
    country: str | None = None
    state: str | None = None
    lat: float
    lon: float


class HourlyForecast(BaseModel):
    time: str = Field(description="Local time of day, HH:MM")
    temperature: float
    feels_like: float
    description: str
    precipitation_probability: int = Field(description="Percent, 0-100")
    wind_speed: float


class DailyWeather(BaseModel):
    date: dt.date
    temp_min: float
    temp_max: float
    feels_like_min: float
    feels_like_max: float
    humidity_avg: int
    wind_speed_max: float
    precipitation_probability: int = Field(description="Highest chance of precipitation during the day, percent")
    rain_mm: float
    snow_mm: float
    conditions: list[str] = Field(description="Distinct weather descriptions, most frequent first")
    hourly: list[HourlyForecast]


class WeatherResponse(BaseModel):
    location: Location
    units: Units
    weather: DailyWeather


class Recommendation(BaseModel):
    summary: str
    clothing: list[str]
    activities: list[str]
    tips: list[str] = []


class RecommendationResponse(WeatherResponse):
    recommendation: Recommendation
