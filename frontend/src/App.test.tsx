import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import App from "./App";
import type { RecommendationResponse } from "./types";
import { weatherIcon } from "./weatherIcon";

const RESPONSE: RecommendationResponse = {
  location: { name: "Zagreb", country: "HR", state: "City of Zagreb", lat: 45.81, lon: 15.98 },
  units: "metric",
  weather: {
    date: "2026-10-05",
    temp_min: 9.4,
    temp_max: 17.6,
    feels_like_min: 8,
    feels_like_max: 17,
    humidity_avg: 70,
    wind_speed_max: 4.2,
    precipitation_probability: 60,
    rain_mm: 2.3,
    snow_mm: 0,
    conditions: ["light rain", "overcast clouds"],
    hourly: [
      { time: "09:00", temperature: 11, feels_like: 10, description: "overcast clouds", precipitation_probability: 0, wind_speed: 2 },
      { time: "15:00", temperature: 16.8, feels_like: 17, description: "light rain", precipitation_probability: 60, wind_speed: 4.2 },
    ],
  },
  recommendation: {
    summary: "Mild with afternoon showers.",
    clothing: ["Light rain jacket"],
    activities: ["Museum of Broken Relationships"],
    tips: ["Carry an umbrella"],
  },
};

function mockFetch(status: number, body: unknown) {
  return vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } }),
  );
}

async function search(city = "Zagreb") {
  const user = userEvent.setup();
  render(<App />);
  await user.type(screen.getByLabelText("City"), city);
  await user.click(screen.getByRole("button", { name: "Get advice" }));
}

describe("App", () => {
  it("sends the form values and renders weather and recommendations", async () => {
    const fetchSpy = mockFetch(200, RESPONSE);

    await search("  Zagreb ");

    expect(await screen.findByText("Zagreb, City of Zagreb, HR")).toBeInTheDocument();
    expect(screen.getByText("18°C")).toBeInTheDocument();
    expect(screen.getByText("Mild with afternoon showers.")).toBeInTheDocument();
    expect(screen.getByText("Light rain jacket")).toBeInTheDocument();
    expect(screen.getByText("Museum of Broken Relationships")).toBeInTheDocument();
    expect(screen.getByText("Carry an umbrella")).toBeInTheDocument();
    expect(screen.getByText("15:00")).toBeInTheDocument();

    const [url, init] = fetchSpy.mock.calls[0];
    expect(url).toBe("/api/v1/recommendations");
    const body = JSON.parse(init!.body as string);
    expect(body.city).toBe("Zagreb");
    expect(body.units).toBe("metric");
    expect(body.date).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  });

  it("shows the backend error message", async () => {
    mockFetch(404, { detail: "City 'Atlantis' was not found." });

    await search("Atlantis");

    expect(await screen.findByRole("alert")).toHaveTextContent("City 'Atlantis' was not found.");
  });

  it("shows validation errors returned as a list", async () => {
    mockFetch(422, { detail: [{ msg: "Input should be a valid date" }] });

    await search();

    expect(await screen.findByRole("alert")).toHaveTextContent("Input should be a valid date");
  });

  it("explains when the backend is unreachable", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new TypeError("Failed to fetch"));

    await search();

    expect(await screen.findByRole("alert")).toHaveTextContent("Is the backend running?");
  });

  it("disables the button until a city is entered", () => {
    render(<App />);
    expect(screen.getByRole("button", { name: "Get advice" })).toBeDisabled();
  });
});

describe("weatherIcon", () => {
  it.each([
    ["light rain", "🌧️"],
    ["thunderstorm with rain", "⛈️"],
    ["clear sky", "☀️"],
    ["overcast clouds", "☁️"],
    ["something unknown", "🌡️"],
  ])("%s -> %s", (description, icon) => {
    expect(weatherIcon(description)).toBe(icon);
  });
});
