import { useState, type FormEvent } from "react";

import { addDays, MAX_DAYS_AHEAD, toIsoDate } from "../dates";
import type { RecommendationRequest, Units } from "../types";

interface Props {
  loading: boolean;
  onSubmit: (request: RecommendationRequest) => void;
}

export function SearchForm({ loading, onSubmit }: Props) {
  const today = new Date();
  const [city, setCity] = useState("");
  const [date, setDate] = useState(toIsoDate(addDays(today, 1)));
  const [units, setUnits] = useState<Units>("metric");

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const trimmed = city.trim();
    if (trimmed) onSubmit({ city: trimmed, date, units });
  }

  return (
    <form className="search card" onSubmit={handleSubmit}>
      <label className="field field-city">
        <span>City</span>
        <input
          type="text"
          placeholder="e.g. Zagreb or Paris, FR"
          value={city}
          onChange={(e) => setCity(e.target.value)}
          maxLength={100}
          required
          autoFocus
        />
      </label>
      <label className="field">
        <span>Date</span>
        <input
          type="date"
          value={date}
          min={toIsoDate(today)}
          max={toIsoDate(addDays(today, MAX_DAYS_AHEAD))}
          onChange={(e) => setDate(e.target.value)}
          required
        />
      </label>
      <label className="field">
        <span>Units</span>
        <select value={units} onChange={(e) => setUnits(e.target.value as Units)}>
          <option value="metric">°C</option>
          <option value="imperial">°F</option>
        </select>
      </label>
      <button type="submit" disabled={loading || !city.trim()}>
        {loading ? "Thinking…" : "Get advice"}
      </button>
    </form>
  );
}
