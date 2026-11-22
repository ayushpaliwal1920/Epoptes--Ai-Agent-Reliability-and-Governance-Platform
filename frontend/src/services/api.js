const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");

export async function apiRequest(
  endpoint,
  { token, apiKey, method = "GET", body, signal } = {},
) {
  const headers = {};

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  if (apiKey) {
    headers["X-Agent-Key"] = apiKey;
  }

  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
    signal,
  });

  const contentType = response.headers.get("content-type") || "";
  const result = contentType.includes("application/json")
    ? await response.json()
    : await response.text();

  if (!response.ok) {
    const detail =
      typeof result === "object" && result !== null
        ? result.detail || result.message
        : result;
    const error = new Error(detail || `Request failed (${response.status})`);
    error.status = response.status;
    throw error;
  }

  return result;
}

export const login = (credentials) =>
  apiRequest("/api/v1/auth/login", { method: "POST", body: credentials });

export const register = (details) =>
  apiRequest("/api/v1/auth/register", { method: "POST", body: details });

export const listAgents = (token, signal) =>
  apiRequest("/api/v1/agents", { token, signal });

export const createAgent = (token, details) =>
  apiRequest("/api/v1/agents", { token, method: "POST", body: details });

export const deactivateAgent = (token, agentId) =>
  apiRequest(`/api/v1/agents/${agentId}/deactivate`, {
    token,
    method: "PATCH",
  });

export const rotateAgentKey = (token, agentId) =>
  apiRequest(`/api/v1/agents/${agentId}/rotate-key`, {
    token,
    method: "POST",
  });

export const listSecurityEvents = (token, signal) =>
  apiRequest("/api/v1/security/events", { token, signal });

export const getAgentRuns = (apiKey, signal) =>
  apiRequest("/api/v1/runs/", { apiKey, signal });

export const getRunTraces = (runId, apiKey, signal) =>
  apiRequest(`/api/v1/runs/${runId}/traces/`, { apiKey, signal });
