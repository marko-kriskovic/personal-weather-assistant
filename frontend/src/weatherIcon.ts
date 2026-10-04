const ICONS: [keyword: string, icon: string][] = [
  ["thunder", "⛈️"],
  ["snow", "❄️"],
  ["sleet", "🌨️"],
  ["drizzle", "🌦️"],
  ["rain", "🌧️"],
  ["mist", "🌫️"],
  ["fog", "🌫️"],
  ["haze", "🌫️"],
  ["few clouds", "🌤️"],
  ["scattered clouds", "⛅"],
  ["cloud", "☁️"],
  ["clear", "☀️"],
];

/** Picks an emoji for an OpenWeatherMap description like "light rain". */
export function weatherIcon(description: string): string {
  const text = description.toLowerCase();
  return ICONS.find(([keyword]) => text.includes(keyword))?.[1] ?? "🌡️";
}
