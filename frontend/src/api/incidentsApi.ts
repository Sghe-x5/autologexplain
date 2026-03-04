import { baseUrl } from "@/consts/api.const";
import { createApi, fetchBaseQuery } from "@reduxjs/toolkit/query/react";

export type IncidentStatus =
  | "open"
  | "acknowledged"
  | "mitigated"
  | "resolved"
  | "reopened";

export type IncidentSeverity =
  | "critical"
  | "error"
  | "warning"
  | "info"
  | "debug";

export interface Incident {
  incident_id: string;
  fingerprint: string;
  title: string;
  status: IncidentStatus;
  service: string;
  environment: string;
  category: string;
  severity: IncidentSeverity;
  opened_at: string;
  acknowledged_at: string | null;
  mitigated_at: string | null;
  resolved_at: string | null;
  last_seen_at: string;
  root_cause_service: string;
  root_cause_score: number;
  impact_score: number;
  burn_rate_5m: number;
  burn_rate_1h: number;
  burn_rate_6h: number;
  affected_services: number;
  critical_rate: number;
  prod_weight: number;
  evidence: string[];
  context_json: string;
  context?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  max_version?: number;
}

export interface IncidentListResponse {
  items: Incident[];
  count: number;
}

export interface IncidentEvent {
  event_id: string;
  incident_id: string;
  event_type: string;
  event_time: string;
  actor: string;
  payload: Record<string, unknown>;
}

export interface IncidentTimelineResponse {
  incident_id: string;
  events: IncidentEvent[];
}

export interface IncidentEvidenceResponse {
  incident_id: string;
  evidence: string[];
  candidate_evidence: {
    event_id: string;
    event_time: string;
    payload: Record<string, unknown>;
  }[];
}

export interface IncidentListParams {
  status?: IncidentStatus;
  service?: string;
  environment?: string;
  category?: string;
  severity?: IncidentSeverity;
  q?: string;
  limit?: number;
  offset?: number;
}

export interface PatchStatusRequest {
  status: IncidentStatus;
  actor?: string;
  note?: string;
}

export interface SimilarMatch {
  incident_id: string;
  score: number;
  breakdown: Record<string, number>;
  incident: Incident;
}

export interface SimilarResponse {
  incident_id: string;
  matches: SimilarMatch[];
}

export interface PostmortemResponse {
  incident_id: string;
  markdown: string;
}

export const incidentsApi = createApi({
  reducerPath: "incidentsApi",
  baseQuery: fetchBaseQuery({ baseUrl }),
  tagTypes: ["Incident", "IncidentTimeline", "IncidentEvidence"],
  endpoints: (build) => ({
    listIncidents: build.query<IncidentListResponse, IncidentListParams>({
      query: (params) => ({
        url: "/incidents",
        params: {
          limit: params.limit ?? 50,
          offset: params.offset ?? 0,
          ...(params.status ? { status: params.status } : {}),
          ...(params.service ? { service: params.service } : {}),
          ...(params.environment ? { environment: params.environment } : {}),
          ...(params.category ? { category: params.category } : {}),
          ...(params.severity ? { severity: params.severity } : {}),
          ...(params.q ? { q: params.q } : {}),
        },
      }),
      providesTags: (result) =>
        result
          ? [
              ...result.items.map((i) => ({
                type: "Incident" as const,
                id: i.incident_id,
              })),
              { type: "Incident" as const, id: "LIST" },
            ]
          : [{ type: "Incident" as const, id: "LIST" }],
    }),

    getIncident: build.query<Incident, string>({
      query: (id) => ({ url: `/incidents/${id}` }),
      providesTags: (_r, _e, id) => [{ type: "Incident", id }],
    }),

    getIncidentTimeline: build.query<
      IncidentTimelineResponse,
      { id: string; limit?: number }
    >({
      query: ({ id, limit = 100 }) => ({
        url: `/incidents/${id}/timeline`,
        params: { limit },
      }),
      providesTags: (_r, _e, { id }) => [{ type: "IncidentTimeline", id }],
    }),

    getIncidentEvidence: build.query<IncidentEvidenceResponse, { id: string }>({
      query: ({ id }) => ({ url: `/incidents/${id}/evidence` }),
      providesTags: (_r, _e, { id }) => [{ type: "IncidentEvidence", id }],
    }),

    updateStatus: build.mutation<
      Incident,
      { id: string } & PatchStatusRequest
    >({
      query: ({ id, status, actor, note }) => ({
        url: `/incidents/${id}/status`,
        method: "PATCH",
        body: { status, actor, note },
      }),
      invalidatesTags: (_r, _e, { id }) => [
        { type: "Incident", id },
        { type: "Incident", id: "LIST" },
        { type: "IncidentTimeline", id },
      ],
    }),

    getSimilar: build.query<SimilarResponse, { id: string; k?: number }>({
      query: ({ id, k = 5 }) => ({
        url: `/incidents/${id}/similar`,
        params: { k },
      }),
    }),

    getPostmortem: build.query<PostmortemResponse, { id: string }>({
      query: ({ id }) => ({ url: `/incidents/${id}/postmortem` }),
    }),
  }),
});

export const {
  useListIncidentsQuery,
  useGetIncidentQuery,
  useGetIncidentTimelineQuery,
  useGetIncidentEvidenceQuery,
  useUpdateStatusMutation,
  useGetSimilarQuery,
  useLazyGetPostmortemQuery,
} = incidentsApi;
