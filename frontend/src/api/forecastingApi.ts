import { baseUrl } from "@/consts/api.const";
import { createApi, fetchBaseQuery } from "@reduxjs/toolkit/query/react";
import type { RiskResponse, ForecasterInfo } from "./rcaApi";

export const forecastingApi = createApi({
  reducerPath: "forecastingApi",
  baseQuery: fetchBaseQuery({ baseUrl }),
  tagTypes: ["Risk", "ForecasterInfo"],
  endpoints: (build) => ({
    getForecasterInfo: build.query<ForecasterInfo, void>({
      query: () => ({ url: "/forecasting/info" }),
      providesTags: ["ForecasterInfo"],
    }),
    getCurrentRisk: build.query<RiskResponse, { hours?: number }>({
      query: ({ hours = 2 }) => ({
        url: "/forecasting/risk",
        params: { hours },
      }),
      providesTags: ["Risk"],
    }),
  }),
});

export const { useGetForecasterInfoQuery, useGetCurrentRiskQuery } = forecastingApi;
