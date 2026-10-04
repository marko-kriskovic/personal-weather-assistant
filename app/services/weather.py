"""OpenWeatherMap client.

Uses the free-tier Geocoding API and the 5 day / 3 hour Forecast API, so the
supported date range is today up to 5 days ahead (in the city's local time).
"""

import datetime as dt
from collections import Counter
from typing import Any, Callable

import httpx

from app.errors import CityNotFoundError, DateOutOfRangeError, UpstreamServiceError
from app.models import DailyWeather, HourlyForecast, Location, Units

MAX_FORECAST_DAYS = 5


def _utc_today() -> dt.date:
    return dt.datetime.now(dt.timezone.utc).date()


class WeatherService:
    def __init__(
        self,
        client: httpx.AsyncClient,
        api_key: str,
        base_url: str = "https://api.openweathermap.org",
        today: Callable[[], dt.date] = _utc_today,
    ):
        self._client = client
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._today = today

    async def get_daily_weather(
        self, city: str, date: dt.date, units: Units = "metric"
    ) -> tuple[Location, DailyWeather]:
        self._check_date_in_range(date)
        location = await self.geocode(city)
        forecast = await self._get(
            "/data/2.5/forecast",
            {"lat": location.lat, "lon": location.lon, "units": units},
        )
        return location, aggregate_forecast(forecast, date)

    async def geocode(self, city: str) -> Location:
        results = await self._get("/geo/1.0/direct", {"q": city, "limit": 1})
        if not results:
            raise CityNotFoundError(f"City '{city}' was not found.")
        first = results[0]
        return Location(
            name=first["name"],
            country=first.get("country"),
            state=first.get("state"),
            lat=first["lat"],
            lon=first["lon"],
        )

    def _check_date_in_range(self, date: dt.date) -> None:
        # Cheap pre-check before calling the API. One day of slack on either
        # side accounts for timezones; aggregate_forecast does the exact check.
        today = self._today()
        if not (today - dt.timedelta(days=1) <= date <= today + dt.timedelta(days=MAX_FORECAST_DAYS)):
            raise DateOutOfRangeError(
                f"Forecast is only available from today up to {MAX_FORECAST_DAYS} days ahead "
                f"({today.isoformat()} to {(today + dt.timedelta(days=MAX_FORECAST_DAYS)).isoformat()})."
            )

    async def _get(self, path: str, params: dict[str, Any]) -> Any:
        try:
            response = await self._client.get(
                f"{self._base_url}{path}", params={**params, "appid": self._api_key}
            )
        except httpx.RequestError as exc:
            raise UpstreamServiceError(f"Could not reach OpenWeatherMap: {exc}") from exc

        if response.status_code == 401:
            raise UpstreamServiceError("OpenWeatherMap rejected the API key.")
        if response.is_error:
            raise UpstreamServiceError(
                f"OpenWeatherMap returned HTTP {response.status_code}: {response.text[:200]}"
            )
        return response.json()


def aggregate_forecast(forecast: dict[str, Any], date: dt.date) -> DailyWeather:
    """Collapse the 3-hourly forecast entries that fall on `date` (city local time) into one day."""
    tz = dt.timezone(dt.timedelta(seconds=forecast.get("city", {}).get("timezone", 0)))

    entries: list[tuple[dt.datetime, dict[str, Any]]] = [
        (dt.datetime.fromtimestamp(item["dt"], tz), item) for item in forecast.get("list", [])
    ]
    day_entries = [(when, item) for when, item in entries if when.date() == date]

    if not day_entries:
        if entries:
            first, last = entries[0][0].date(), entries[-1][0].date()
            raise DateOutOfRangeError(
                f"No forecast data for {date.isoformat()}. "
                f"Available dates: {first.isoformat()} to {last.isoformat()}."
            )
        raise DateOutOfRangeError(f"No forecast data for {date.isoformat()}.")

    temps = [item["main"]["temp"] for _, item in day_entries]
    feels = [item["main"]["feels_like"] for _, item in day_entries]
    humidity = [item["main"]["humidity"] for _, item in day_entries]
    winds = [item.get("wind", {}).get("speed", 0.0) for _, item in day_entries]
    pops = [item.get("pop", 0.0) for _, item in day_entries]
    descriptions = [
        item["weather"][0]["description"] for _, item in day_entries if item.get("weather")
    ]

    return DailyWeather(
        date=date,
        temp_min=round(min(temps), 1),
        temp_max=round(max(temps), 1),
        feels_like_min=round(min(feels), 1),
        feels_like_max=round(max(feels), 1),
        humidity_avg=round(sum(humidity) / len(humidity)),
        wind_speed_max=round(max(winds), 1),
        precipitation_probability=round(max(pops) * 100),
        rain_mm=round(sum(item.get("rain", {}).get("3h", 0.0) for _, item in day_entries), 1),
        snow_mm=round(sum(item.get("snow", {}).get("3h", 0.0) for _, item in day_entries), 1),
        conditions=[desc for desc, _ in Counter(descriptions).most_common()],
        hourly=[
            HourlyForecast(
                time=when.strftime("%H:%M"),
                temperature=round(item["main"]["temp"], 1),
                feels_like=round(item["main"]["feels_like"], 1),
                description=item["weather"][0]["description"] if item.get("weather") else "",
                precipitation_probability=round(item.get("pop", 0.0) * 100),
                wind_speed=round(item.get("wind", {}).get("speed", 0.0), 1),
            )
            for when, item in day_entries
        ],
    )
