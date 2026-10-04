import datetime as dt

import httpx
import pytest

from app.errors import CityNotFoundError, DateOutOfRangeError, UpstreamServiceError
from app.services.weather import WeatherService, aggregate_forecast
from tests.conftest import GEOCODE_ZAGREB, OWM_BASE, make_forecast

TODAY = dt.date(2026, 10, 4)


class TestAggregateForecast:
    def test_aggregates_entries_for_the_requested_day(self):
        weather = aggregate_forecast(make_forecast(TODAY), TODAY + dt.timedelta(days=1))

        assert weather.date == TODAY + dt.timedelta(days=1)
        assert len(weather.hourly) == 8
        assert weather.temp_min == 10.0  # 00:00
        assert weather.temp_max == 17.0  # 21:00
        assert weather.feels_like_min == 8.0
        assert weather.feels_like_max == 15.0
        assert weather.humidity_avg == 60
        assert weather.wind_speed_max == 5.0
        assert weather.precipitation_probability == 80
        assert weather.rain_mm == 1.2  # 1.25 rounded
        assert weather.snow_mm == 0.0
        assert weather.conditions == ["scattered clouds", "light rain"]

    def test_hourly_slots_use_city_local_time(self):
        # UTC+2: entries at 00:00..21:00 UTC show up as 02:00..23:00 local.
        weather = aggregate_forecast(make_forecast(TODAY, tz_offset_seconds=7200), TODAY + dt.timedelta(days=1))

        assert [h.time for h in weather.hourly] == [
            "02:00", "05:00", "08:00", "11:00", "14:00", "17:00", "20:00", "23:00",
        ]
        rainy = next(h for h in weather.hourly if h.time == "17:00")
        assert rainy.description == "light rain"
        assert rainy.precipitation_probability == 80

    def test_date_outside_forecast_raises_with_available_range(self):
        with pytest.raises(DateOutOfRangeError, match=r"Available dates: 2026-10-04 to 2026-10-08"):
            aggregate_forecast(make_forecast(TODAY), TODAY + dt.timedelta(days=10))

    def test_empty_forecast_raises(self):
        with pytest.raises(DateOutOfRangeError):
            aggregate_forecast({"list": [], "city": {}}, TODAY)


class TestWeatherService:
    @pytest.fixture
    async def service(self):
        async with httpx.AsyncClient() as client:
            yield WeatherService(client, "key", OWM_BASE, today=lambda: TODAY)

    async def test_fetches_geocode_and_forecast(self, service, mock_api):
        geo = mock_api.get(f"{OWM_BASE}/geo/1.0/direct").respond(json=GEOCODE_ZAGREB)
        forecast = mock_api.get(f"{OWM_BASE}/data/2.5/forecast").respond(json=make_forecast(TODAY))

        location, weather = await service.get_daily_weather("Zagreb", TODAY, "imperial")

        assert location.name == "Zagreb" and location.country == "HR"
        assert weather.date == TODAY
        assert geo.calls.last.request.url.params["q"] == "Zagreb"
        assert geo.calls.last.request.url.params["appid"] == "key"
        params = forecast.calls.last.request.url.params
        assert params["lat"] == "45.81" and params["lon"] == "15.98"
        assert params["units"] == "imperial"

    async def test_unknown_city(self, service, mock_api):
        mock_api.get(f"{OWM_BASE}/geo/1.0/direct").respond(json=[])

        with pytest.raises(CityNotFoundError, match="Atlantis"):
            await service.get_daily_weather("Atlantis", TODAY)

    @pytest.mark.parametrize("offset_days", [-2, 6, 30])
    async def test_date_out_of_range_does_not_call_api(self, service, mock_api, offset_days):
        geo = mock_api.get(f"{OWM_BASE}/geo/1.0/direct").respond(json=GEOCODE_ZAGREB)

        with pytest.raises(DateOutOfRangeError):
            await service.get_daily_weather("Zagreb", TODAY + dt.timedelta(days=offset_days))
        assert not geo.called

    async def test_invalid_api_key(self, service, mock_api):
        mock_api.get(f"{OWM_BASE}/geo/1.0/direct").respond(401, json={"cod": 401})

        with pytest.raises(UpstreamServiceError, match="API key"):
            await service.get_daily_weather("Zagreb", TODAY)

    async def test_server_error(self, service, mock_api):
        mock_api.get(f"{OWM_BASE}/geo/1.0/direct").respond(json=GEOCODE_ZAGREB)
        mock_api.get(f"{OWM_BASE}/data/2.5/forecast").respond(500, text="boom")

        with pytest.raises(UpstreamServiceError, match="HTTP 500"):
            await service.get_daily_weather("Zagreb", TODAY)

    async def test_network_error(self, service, mock_api):
        mock_api.get(f"{OWM_BASE}/geo/1.0/direct").mock(side_effect=httpx.ConnectError("down"))

        with pytest.raises(UpstreamServiceError, match="Could not reach"):
            await service.get_daily_weather("Zagreb", TODAY)
