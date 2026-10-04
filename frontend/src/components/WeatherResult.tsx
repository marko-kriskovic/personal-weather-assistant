import { formatLongDate } from "../dates";
import type { RecommendationResponse } from "../types";
import { weatherIcon } from "../weatherIcon";

interface Props {
  result: RecommendationResponse;
}

export function WeatherResult({ result }: Props) {
  const { location, weather, recommendation, units } = result;
  const deg = units === "metric" ? "°C" : "°F";
  const windUnit = units === "metric" ? "m/s" : "mph";
  const place = [location.name, location.state, location.country].filter(Boolean).join(", ");
  const mainCondition = weather.conditions[0] ?? "";

  return (
    <section className="result">
      <div className="card overview">
        <div className="overview-icon" aria-hidden>
          {weatherIcon(mainCondition)}
        </div>
        <div className="overview-main">
          <h2>{place}</h2>
          <p className="muted">{formatLongDate(weather.date)}</p>
          <p className="temps">
            <strong>{Math.round(weather.temp_max)}{deg}</strong>
            <span className="muted"> / {Math.round(weather.temp_min)}{deg}</span>
          </p>
          <p className="conditions">{weather.conditions.join(", ")}</p>
        </div>
        <dl className="stats">
          <div>
            <dt>Feels like</dt>
            <dd>
              {Math.round(weather.feels_like_min)}–{Math.round(weather.feels_like_max)}{deg}
            </dd>
          </div>
          <div>
            <dt>Precipitation</dt>
            <dd>
              {weather.precipitation_probability}%
              {weather.rain_mm > 0 && ` · ${weather.rain_mm} mm`}
              {weather.snow_mm > 0 && ` · ${weather.snow_mm} mm snow`}
            </dd>
          </div>
          <div>
            <dt>Wind</dt>
            <dd>up to {weather.wind_speed_max} {windUnit}</dd>
          </div>
          <div>
            <dt>Humidity</dt>
            <dd>{weather.humidity_avg}%</dd>
          </div>
        </dl>
      </div>

      <ol className="hourly" aria-label="Hourly forecast">
        {weather.hourly.map((h) => (
          <li key={h.time} className="hour" title={h.description}>
            <span className="muted">{h.time}</span>
            <span className="hour-icon" aria-label={h.description}>
              {weatherIcon(h.description)}
            </span>
            <strong>{Math.round(h.temperature)}{deg}</strong>
            <span className="hour-pop">{h.precipitation_probability > 0 ? `💧${h.precipitation_probability}%` : " "}</span>
          </li>
        ))}
      </ol>

      <p className="summary card">{recommendation.summary}</p>

      <div className="advice">
        <AdviceList title="What to wear" icon="🧥" items={recommendation.clothing} />
        <AdviceList title="Things to do" icon="🎯" items={recommendation.activities} />
        {recommendation.tips.length > 0 && <AdviceList title="Tips" icon="💡" items={recommendation.tips} />}
      </div>
    </section>
  );
}

function AdviceList({ title, icon, items }: { title: string; icon: string; items: string[] }) {
  return (
    <div className="card advice-card">
      <h3>
        <span aria-hidden>{icon}</span> {title}
      </h3>
      <ul>
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </div>
  );
}
