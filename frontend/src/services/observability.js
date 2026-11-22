import { apiRequest } from "./api";

export const getObservabilityOverview = (key, signal) =>
  apiRequest("/api/v1/metrics/overview", { apiKey: key, signal });

export const getModelUsage = (key, signal) =>
  apiRequest("/api/v1/metrics/models", { apiKey: key, signal });

export const getToolUsage = (key, signal) =>
  apiRequest("/api/v1/metrics/tools", { apiKey: key, signal });

export const getAgentRuns = (key, signal) =>
  apiRequest("/api/v1/runs/", { apiKey: key, signal });

export const getRunTraces = (runId, key, signal) =>
  apiRequest(`/api/v1/runs/${runId}/traces/`, { apiKey: key, signal });