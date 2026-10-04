import type { RecommendationRequest, RecommendationResponse } from "./types";

const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
  }
}

// FastAPI returns `detail` as a string for app errors and as a list for validation errors.
function describeError(detail: unknown, status: number): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length > 0) {
    return detail.map((d) => d?.msg ?? String(d)).join("; ");
  }
  return `Request failed (HTTP ${status})`;
}

export async function getRecommendation(req: RecommendationRequest): Promise<RecommendationResponse> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}/api/v1/recommendations`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req),
    });
  } catch {
    throw new ApiError("Could not reach the server. Is the backend running?", 0);
  }

  const data = await response.json().catch(() => null);
  if (!response.ok) {
    throw new ApiError(describeError(data?.detail, response.status), response.status);
  }
  return data as RecommendationResponse;
}
