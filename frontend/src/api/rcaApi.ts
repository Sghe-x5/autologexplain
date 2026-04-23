import { baseUrl } from "@/consts/api.const";
import { createApi, fetchBaseQuery } from "@reduxjs/toolkit/query/react";

export type AlertLevel = "none" | "warning" | "ticket" | "page";

export interface RcaTimelineEntry {
  time: string;
  service: string;
  category: string;
  severity: string;
  count: number;
  z_score: number;
}

export interface RcaReport {
  id: string;
  incident_fingerprint: string;
  root_cause_service: string;
  root_cause_category: string;
  cascade_path: string[];
  affected_services: string[];
  anomaly_score: number;
  alert_level: AlertLevel;
  timeline: RcaTimelineEntry[];
  evidence_templates: string[];
  summary: string;
  confidence: number;
  created_at: string;
}

export interface GraphEdge {
  from: string;
  to: string;
  weight: number;
}

export interface DependencyGraphResponse {
  nodes: string[];
  edges: GraphEdge[];
  hours: number;
  min_weight: number;
}

export interface LogTemplate {
  template: string;
  count: number;
}

export interface LogTemplatesResponse {
  templates: LogTemplate[];
  total_logs: number;
  unique_templates: number;
  hours: number;
}

export interface SloWindow {
  label: string;
  error_count: number;
  total_count: number;
  error_rate: number;
  burn_rate: number;
  threshold: number;
  is_burning: boolean;
}

export interface ServiceSloStatus {
  service: string;
  slo_target: number;
  allowed_error_rate: number;
  alert_level: AlertLevel;
  windows: SloWindow[];
}

export interface SloResponse {
  services: ServiceSloStatus[];
  count: number;
  hours: number;
}

export interface DetectorMetric {
  threshold: number;
  precision: number;
  recall: number;
  f1: number;
  tp: number;
  fp: number;
  fn: number;
  tn: number;
}

export interface DetectorReport {
  name: string;
  roc_auc: number;
  pr_auc: number;
  best: DetectorMetric;
  "at_threshold_3.5": DetectorMetric;
}

export interface MetricsResponse {
  dataset: { points: number; positives: number; negatives: number };
  results: DetectorReport[];
}

// ─── Forecasting types ────────────────────────────────────────────────

export interface FeatureContribution {
  name: string;
  value: number;
  shap: number;
  direction: "up" | "down";
}

export interface RiskPrediction {
  service: string;
  environment: string;
  minute: string;
  risk_score: number;
  top_features: FeatureContribution[];
}

export interface RiskResponse {
  predictions: RiskPrediction[];
  horizon_minutes: number;
}

export interface ForecasterInfo {
  horizon_minutes: number;
  split_strategy: string;
  train_size: number;
  test_size: number;
  metrics: {
    roc_auc: number;
    pr_auc: number;
    f1_best: number;
    precision_best: number;
    recall_best: number;
    best_threshold: number;
  };
  feature_importance: Record<string, number>;
  feature_names: string[];
}

export const rcaApi = createApi({
  reducerPath: "rcaApi",
  baseQuery: fetchBaseQuery({ baseUrl }),
  tagTypes: ["RcaReport", "Graph", "Templates", "Slo"],
  endpoints: (build) => ({
    analyzeIncident: build.mutation<
      RcaReport,
      { fingerprint: string; hours?: number; use_llm?: boolean }
    >({
      query: ({ fingerprint, hours = 6, use_llm = false }) => ({
        url: `/rca/analyze/${fingerprint}`,
        method: "POST",
        body: { hours, use_llm },
      }),
      invalidatesTags: [{ type: "RcaReport", id: "LIST" }],
    }),

    listReports: build.query<{ reports: RcaReport[]; count: number }, void>({
      query: () => ({ url: "/rca/reports" }),
      providesTags: [{ type: "RcaReport", id: "LIST" }],
    }),

    getDependencyGraph: build.query<
      DependencyGraphResponse,
      { hours?: number; min_weight?: number }
    >({
      query: ({ hours = 24, min_weight = 1 }) => ({
        url: "/rca/graph",
        params: { hours, min_weight },
      }),
      providesTags: ["Graph"],
    }),

    getLogTemplates: build.query<
      LogTemplatesResponse,
      { hours?: number; limit?: number; top_n?: number }
    >({
      query: ({ hours = 4, limit = 500, top_n = 10 }) => ({
        url: "/rca/templates",
        params: { hours, limit, top_n },
      }),
      providesTags: ["Templates"],
    }),

    getSloStatus: build.query<SloResponse, { hours?: number }>({
      query: ({ hours = 4 }) => ({
        url: "/rca/slo",
        params: { hours },
      }),
      providesTags: ["Slo"],
    }),

    getDetectorMetrics: build.query<MetricsResponse, void>({
      query: () => ({ url: "/rca/metrics" }),
    }),
  }),
});

export const {
  useAnalyzeIncidentMutation,
  useListReportsQuery,
  useGetDependencyGraphQuery,
  useGetLogTemplatesQuery,
  useGetSloStatusQuery,
  useGetDetectorMetricsQuery,
} = rcaApi;
