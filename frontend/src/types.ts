// Mirrors the backend schemas in app/models.py.

export type Units = "metric" | "imperial";

export interface RecommendationRequest {
  city: string;
  date: string; // YYYY-MM-DD
  units: Units;
}

export interface Location {
  name: string;
  country: string | null;
  state: string | null;
  lat: number;
  lon: number;
}

export interface HourlyForecast {
  time: string;
  temperature: number;
  feels_like: number;
  description: string;
  precipitation_probability: number;
  wind_speed: number;
}

export interface DailyWeather {
  date: string;
  temp_min: number;
  temp_max: number;
  feels_like_min: number;
  feels_like_max: number;
  humidity_avg: number;
  wind_speed_max: number;
  precipitation_probability: number;
  rain_mm: number;
  snow_mm: number;
  conditions: string[];
  hourly: HourlyForecast[];
}

export interface Recommendation {
  summary: string;
  clothing: string[];
  activities: string[];
  tips: string[];
}

export interface RecommendationResponse {
  location: Location;
  units: Units;
  weather: DailyWeather;
  recommendation: Recommendation;
}
