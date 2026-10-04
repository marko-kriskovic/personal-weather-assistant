class WeatherAssistantError(Exception):
    """Base class for errors that map to a specific HTTP status code."""

    status_code: int = 500

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class CityNotFoundError(WeatherAssistantError):
    status_code = 404


class DateOutOfRangeError(WeatherAssistantError):
    status_code = 422


class UpstreamServiceError(WeatherAssistantError):
    status_code = 502


class ConfigurationError(WeatherAssistantError):
    status_code = 503
