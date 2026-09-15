import { apiGet } from "./api";
import type { HealthStatus } from "../types/health";

export function getHealth(): Promise<HealthStatus> {
  return apiGet<HealthStatus>("/api/health");
}
