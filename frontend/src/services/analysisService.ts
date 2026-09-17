import { apiGet } from "./api";
import type { AnalysisDetailResponse, AnalysisListResponse } from "../types/analysisHistory";

export function listAnalyses(page = 1, pageSize = 10): Promise<AnalysisListResponse> {
  return apiGet<AnalysisListResponse>(`/api/analyses?page=${page}&page_size=${pageSize}`);
}

export function getAnalysisDetail(analysisId: string): Promise<AnalysisDetailResponse> {
  return apiGet<AnalysisDetailResponse>(`/api/analyses/${encodeURIComponent(analysisId)}`);
}
