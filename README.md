# personal-weather-assistant
simple weather assistant that recommends clothes or activities

Give it a **city** and a **date**: it fetches the forecast from
[OpenWeatherMap](https://openweathermap.org/api) and asks an LLM on [Groq](https://console.groq.com)
to recommend clothing, activities and practical tips.

- **Backend:** Python and FastAPI, in `app/`
- **Frontend:** React, TypeScript and Vite, in `frontend/`. See [Frontend](#frontend).

## Project layout

```
app/
  main.py               FastAPI app, CORS, error handling
  routes.py             HTTP endpoints (/api/v1/...)
  models.py             Request/response schemas
  config.py             Settings from env vars / .env
  dependencies.py       Wires services into routes
  services/weather.py   OpenWeatherMap client + daily aggregation
  services/recommender.py  Groq client + prompt
tests/                  pytest suite (all external APIs mocked)
scripts/manual_test.sh  curl smoke test against a running server
frontend/
  src/App.tsx           Page layout and request state
  src/api.ts            Backend client
  src/types.ts          TypeScript mirror of app/models.py
  src/components/       SearchForm, WeatherResult
  src/App.test.tsx      Vitest + Testing Library tests
```

## Requirements

- Python 3.11+
- An OpenWeatherMap API key (free tier is enough) — https://home.openweathermap.org/api_keys
  (new keys can take up to ~2 hours to activate)
- A Groq API key — https://console.groq.com/keys
- Node.js 20.19+ or 22.12+ (frontend only)

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

cp .env.example .env      # then edit .env and add your API keys
```

(With [uv](https://docs.astral.sh/uv/): `uv venv && uv pip install -e ".[dev]"`. A uv-created venv has
no `pip`, so stick to `uv pip` there and don't mix the two tools in the same `.venv`.)

**Troubleshooting `error: externally-managed-environment`:** this means `pip` resolved to the
system pip instead of the venv's. Check with `which pip`, which should point into `.venv/bin/`. If
it doesn't, recreate the venv with `rm -rf .venv && python3 -m venv .venv`. On Debian/Ubuntu, you
may first need `sudo apt install python3-venv`. You can also always call the venv's pip directly with
`.venv/bin/python -m pip install -e ".[dev]"`.

### Configuration (`.env` or environment variables)

| Variable               | Required | Default                   | Description                                  |
|------------------------|----------|---------------------------|----------------------------------------------|
| `OPENWEATHER_API_KEY`  | yes      | –                         | OpenWeatherMap key                           |
| `GROQ_API_KEY`         | yes      | –                         | Groq key                                     |
| `GROQ_MODEL`           | no       | `openai/gpt-oss-120b`     | Any Groq chat model that supports JSON mode (e.g. `openai/gpt-oss-20b` for faster replies) |
| `HTTP_TIMEOUT_SECONDS` | no       | `15`                      | Timeout for outgoing API calls               |
| `CORS_ORIGINS`         | no       | `["*"]`                   | JSON list of allowed frontend origins        |

## Running the server

```bash
uvicorn app.main:app --reload
```

The API is served at http://localhost:8000. Interactive docs (Swagger UI) are at
http://localhost:8000/docs, and the OpenAPI schema (handy for generating a frontend client) is at
http://localhost:8000/openapi.json.

## API

### `POST /api/v1/recommendations`

Request:

```json
{ "city": "Zagreb", "date": "2026-10-05", "units": "metric" }
```

- `date` is `YYYY-MM-DD`. It can be anything from today up to **5 days ahead**, because the
  OpenWeatherMap free tier only provides a 5-day forecast.
- `units` is optional: `metric` (default; °C, m/s) or `imperial` (°F, mph).

Response (shortened):

```json
{
  "location": { "name": "Zagreb", "country": "HR", "state": "City of Zagreb", "lat": 45.81, "lon": 15.98 },
  "units": "metric",
  "weather": {
    "date": "2026-10-05",
    "temp_min": 9.1, "temp_max": 17.4,
    "feels_like_min": 7.8, "feels_like_max": 16.9,
    "humidity_avg": 71, "wind_speed_max": 4.2,
    "precipitation_probability": 60, "rain_mm": 2.3, "snow_mm": 0.0,
    "conditions": ["overcast clouds", "light rain"],
    "hourly": [ { "time": "14:00", "temperature": 17.4, "feels_like": 16.9, "description": "light rain", "precipitation_probability": 60, "wind_speed": 4.2 } ]
  },
  "recommendation": {
    "summary": "A mild, cloudy day with showers likely in the afternoon.",
    "clothing": ["Light waterproof jacket", "Long trousers", "Water-resistant shoes"],
    "activities": ["Morning walk in Maksimir Park", "Afternoon at a museum"],
    "tips": ["Carry an umbrella after noon"]
  }
}
```

`hourly` times are in the city's local time.

### `GET /api/v1/weather?city=Zagreb&date=2026-10-05&units=metric`

Returns the same response without `recommendation`. It doesn't call Groq, so it's fast and free to use.

### `GET /health`

Returns `{"status": "ok"}`.

### Errors

Errors come back as `{"detail": "..."}`:

| Status | When                                                              |
|--------|-------------------------------------------------------------------|
| 404    | City not found                                                    |
| 422    | Invalid input, or date outside the available forecast range       |
| 502    | OpenWeatherMap or Groq failed (bad key, outage, malformed output) |
| 503    | An API key is not configured                                      |

## Running the tests

The test suite mocks OpenWeatherMap and Groq (using [respx](https://lundberg.github.io/respx/)),
so it needs **no API keys and no network access**.

```bash
pytest                                   # run everything
pytest -v                                # verbose, one line per test
pytest tests/test_api.py                 # one file
pytest -k recommender                    # tests matching a keyword
pytest tests/test_api.py::test_health    # a single test
```

| File                             | Covers                                                                     |
|----------------------------------|----------------------------------------------------------------------------|
| `tests/test_weather_service.py`  | Forecast aggregation, timezones, date range, OpenWeatherMap error handling |
| `tests/test_recommender.py`      | Groq request format, response parsing, malformed or failed responses       |
| `tests/test_api.py`              | Endpoints end-to-end: validation, status codes, CORS                       |

## Testing manually (real APIs)

1. Put real keys in `.env` and start the server: `uvicorn app.main:app --reload`
2. Then use any of these:

**Smoke-test script.** It calls `/health`, `/api/v1/weather` and `/api/v1/recommendations`:

```bash
scripts/manual_test.sh                          # Zagreb, tomorrow
scripts/manual_test.sh "Split" 2026-10-06       # custom city and date
scripts/manual_test.sh London 2026-10-06 http://localhost:8000
```

**Swagger UI.** Open http://localhost:8000/docs, expand an endpoint, click *Try it out*, fill in
the fields and click *Execute*.

**curl:**

```bash
curl -X POST http://localhost:8000/api/v1/recommendations \
  -H "Content-Type: application/json" \
  -d '{"city": "Zagreb", "date": "2026-10-05"}'

curl "http://localhost:8000/api/v1/weather?city=Zagreb&date=2026-10-05"
```

**Error cases to try:**

- An unknown city such as `"city": "Atlantis123"` should return 404.
- A date more than 5 days ahead, or in the past, should return 422.
- Remove a key from `.env` and restart the server. It should return 503.

## Frontend

A single-page React app. Enter a city, pick a date (the picker only allows today through 5 days
ahead) and choose °C or °F. It shows the day's overview, an hourly strip and the clothing,
activities and tips cards.

### Run it (development)

You need two terminals:

```bash
# Terminal 1 — backend (from the repo root)
source .venv/bin/activate
uvicorn app.main:app --reload

# Terminal 2 — frontend
cd frontend
npm install        # first time only
npm run dev
```

Open http://localhost:5173. The Vite dev server forwards `/api/*` requests to
`http://localhost:8000`, so you don't need any CORS setup. If the backend runs somewhere else,
start Vite with `BACKEND_URL=http://host:port npm run dev`.

### Frontend tests

The tests mock `fetch`, so the backend doesn't need to be running.

```bash
cd frontend
npm test              # run once
npm run test:watch    # re-run on file changes
npx tsc -b            # type-check only
```

### Production build

```bash
cd frontend
VITE_API_BASE_URL=https://your-api.example.com npm run build   # output goes to frontend/dist/
npm run preview                                                # serve the build locally
```

Leave out `VITE_API_BASE_URL` if the API is served from the same origin as the static files. If it's
on a different origin, add the frontend's origin to the backend's `CORS_ORIGINS`.

## Known limitations

- Only the next ~5 days are supported, because of the OpenWeatherMap free tier.
- The forecast comes in 3-hour slots that start from the current time. Late in the evening, there
  may be no slots left for "today", and the API returns 422 with the available dates.
- If several cities share a name, the first match from OpenWeatherMap is used. Add a country
  code to choose one, e.g. `"Paris, US"`.
