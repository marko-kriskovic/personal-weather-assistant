import { useState } from "react";

import { getRecommendation } from "./api";
import { SearchForm } from "./components/SearchForm";
import { WeatherResult } from "./components/WeatherResult";
import type { RecommendationRequest, RecommendationResponse } from "./types";

export default function App() {
  const [result, setResult] = useState<RecommendationResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSearch(request: RecommendationRequest) {
    setLoading(true);
    setError(null);
    try {
      setResult(await getRecommendation(request));
    } catch (err) {
      setResult(null);
      setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="app">
      <header>
        <h1>⛅ Weather Assistant</h1>
        <p className="muted">What to wear and what to do, based on the forecast.</p>
      </header>

      <SearchForm loading={loading} onSubmit={handleSearch} />

      {error && (
        <p className="error card" role="alert">
          {error}
        </p>
      )}
      {loading && !result && <p className="muted loading">Checking the forecast…</p>}
      {result && <WeatherResult result={result} />}
    </main>
  );
}
