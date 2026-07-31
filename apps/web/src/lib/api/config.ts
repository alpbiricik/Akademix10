import type { DataSourceMode } from "@/lib/api/types";

const envMode = process.env.NEXT_PUBLIC_DATA_SOURCE_MODE;

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export const DATA_SOURCE_MODE: DataSourceMode = envMode === "api" ? "api" : "mock";

export function isApiMode() {
  return DATA_SOURCE_MODE === "api";
}
