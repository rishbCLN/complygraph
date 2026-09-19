"use client";

import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { apiFetch } from "./api";
import type {
  Assessment,
  Asset,
  AssetControl,
  AssetField,
  AuditEvent,
  Connector,
  Control,
  ControlEvidence,
  DashboardSummary,
  DataGraph,
  DataPosture,
  DataRequest,
  Evidence,
  Finding,
  Flow,
  Incident,
  Investigation,
  Me,
  Obligation,
  Organization,
  Page,
  ProcessingActivity,
  Regulation,
  Scan,
  SearchResults,
  SeverityCount,
  Task,
  TopFinding,
  Vendor,
} from "./types";

export function useMe() {
  return useQuery({
    queryKey: ["me"],
    queryFn: () => apiFetch<Me>("/auth/me"),
    retry: false,
    staleTime: 60_000,
  });
}

export function useLogoutMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => apiFetch("/auth/logout", { method: "POST" }),
    onSuccess: () => qc.clear(),
  });
}

export function useOrganization() {
  return useQuery({
    queryKey: ["organization"],
    queryFn: () => apiFetch<Organization>("/organization"),
  });
}

export function useDashboardSummary() {
  return useQuery({
    queryKey: ["dashboard", "summary"],
    queryFn: () => apiFetch<DashboardSummary>("/dashboard/summary"),
  });
}

export function useRiskTrend() {
  return useQuery({
    queryKey: ["dashboard", "risk-trend"],
    queryFn: () => apiFetch<SeverityCount[]>("/dashboard/risk-trend"),
  });
}

export function useTopFindings(limit = 8) {
  return useQuery({
    queryKey: ["dashboard", "top-findings", limit],
    queryFn: () =>
      apiFetch<TopFinding[]>(`/dashboard/top-findings?limit=${limit}`),
  });
}

export function useDataPosture() {
  return useQuery({
    queryKey: ["dashboard", "data-posture"],
    queryFn: () => apiFetch<DataPosture>("/dashboard/data-posture"),
  });
}

export function useFindings(params: {
  severity?: string;
  status?: string;
  page?: number;
} = {}) {
  const qs = new URLSearchParams();
  if (params.severity) qs.set("severity", params.severity);
  if (params.status) qs.set("status", params.status);
  qs.set("page", String(params.page || 1));
  qs.set("page_size", "100");
  return useQuery({
    queryKey: ["findings", params],
    queryFn: () => apiFetch<Page<Finding>>(`/findings?${qs.toString()}`),
  });
}

export function useFinding(id: string) {
  return useQuery({
    queryKey: ["finding", id],
    queryFn: () => apiFetch<Finding>(`/findings/${id}`),
    enabled: !!id,
  });
}

export function useInvestigations(findingId?: string) {
  const qs = findingId ? `?finding_id=${findingId}` : "";
  return useQuery({
    queryKey: ["investigations", findingId || "all"],
    queryFn: () => apiFetch<Investigation[]>(`/ai/investigations${qs}`),
  });
}

export function useAiMode() {
  return useQuery({
    queryKey: ["ai", "mode"],
    queryFn: () => apiFetch<{ ai_mode: string; model: string }>("/ai/mode"),
  });
}

export function useInvestigateMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (findingId: string) =>
      apiFetch<{ investigation_id: string; status: string }>(
        `/findings/${findingId}/investigate`,
        { method: "POST" },
      ),
    onSuccess: (_data, findingId) => {
      qc.invalidateQueries({ queryKey: ["investigations", findingId] });
      qc.invalidateQueries({ queryKey: ["investigations", "all"] });
    },
  });
}

export function useFindingTransition() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (args: {
      id: string;
      action: "resolve" | "accept-risk" | "assign";
      note?: string;
    }) =>
      apiFetch<Finding>(`/findings/${args.id}/${args.action}`, {
        method: "POST",
        body: { note: args.note },
      }),
    onSuccess: (_data, args) => {
      qc.invalidateQueries({ queryKey: ["finding", args.id] });
      qc.invalidateQueries({ queryKey: ["findings"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}

export function useControls(params: { category?: string; search?: string } = {}) {
  const qs = new URLSearchParams();
  if (params.category) qs.set("category", params.category);
  if (params.search) qs.set("search", params.search);
  return useQuery({
    queryKey: ["controls", params],
    queryFn: () => apiFetch<Control[]>(`/controls?${qs.toString()}`),
  });
}

export function useControl(id: string) {
  return useQuery({
    queryKey: ["control", id],
    queryFn: () => apiFetch<Control>(`/controls/${id}`),
    enabled: !!id,
  });
}

export function useControlAssessment(id: string) {
  return useQuery({
    queryKey: ["control", id, "assessment"],
    queryFn: () => apiFetch<Assessment | null>(`/controls/${id}/assessment`),
    enabled: !!id,
  });
}

export function useControlEvidence(id: string) {
  return useQuery({
    queryKey: ["control", id, "evidence"],
    queryFn: () => apiFetch<ControlEvidence[]>(`/controls/${id}/evidence`),
    enabled: !!id,
  });
}

export function useAssessControlMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      apiFetch<Assessment>(`/controls/${id}/assess`, { method: "POST" }),
    onSuccess: (_data, id) => {
      qc.invalidateQueries({ queryKey: ["control", id] });
      qc.invalidateQueries({ queryKey: ["controls"] });
    },
  });
}

export function useAssets(params: { search?: string; classification?: string } = {}) {
  const qs = new URLSearchParams();
  if (params.search) qs.set("search", params.search);
  if (params.classification) qs.set("classification", params.classification);
  qs.set("page_size", "200");
  return useQuery({
    queryKey: ["assets", params],
    queryFn: () => apiFetch<Page<Asset>>(`/assets?${qs.toString()}`),
  });
}

export function useAsset(id: string) {
  return useQuery({
    queryKey: ["asset", id],
    queryFn: () => apiFetch<Asset>(`/assets/${id}`),
    enabled: !!id,
  });
}

export function useAssetFields(id: string) {
  return useQuery({
    queryKey: ["asset", id, "fields"],
    queryFn: () => apiFetch<AssetField[]>(`/assets/${id}/fields`),
    enabled: !!id,
  });
}

export function useVendors() {
  return useQuery({
    queryKey: ["vendors"],
    queryFn: () => apiFetch<Vendor[]>("/vendors"),
  });
}

export function useRegulations() {
  return useQuery({
    queryKey: ["regulations"],
    queryFn: () => apiFetch<Regulation[]>("/regulations"),
  });
}

export function useObligations(regulationId: string) {
  return useQuery({
    queryKey: ["regulation", regulationId, "obligations"],
    queryFn: () =>
      apiFetch<Obligation[]>(`/regulations/${regulationId}/obligations`),
    enabled: !!regulationId,
  });
}

export function useDataGraph() {
  return useQuery({
    queryKey: ["graph", "data"],
    queryFn: () => apiFetch<DataGraph>("/graph/data"),
  });
}

export function useAuditEvents(page = 1) {
  return useQuery({
    queryKey: ["audit", page],
    queryFn: () =>
      apiFetch<Page<AuditEvent>>(`/audit-events?page=${page}&page_size=100`),
  });
}

export function useExecutiveReport() {
  return useQuery({
    queryKey: ["reports", "executive"],
    queryFn: () => apiFetch<Record<string, unknown>>("/reports/executive"),
  });
}

export function useAssetFlows(id: string) {
  return useQuery({
    queryKey: ["asset", id, "flows"],
    queryFn: () => apiFetch<Flow[]>(`/assets/${id}/flows`),
    enabled: !!id,
  });
}

export function useAssetControls(id: string) {
  return useQuery({
    queryKey: ["asset", id, "controls"],
    queryFn: () => apiFetch<AssetControl[]>(`/assets/${id}/controls`),
    enabled: !!id,
  });
}

export function useVendor(id: string) {
  return useQuery({
    queryKey: ["vendor", id],
    queryFn: () => apiFetch<Vendor>(`/vendors/${id}`),
    enabled: !!id,
  });
}

export function useRegulation(id: string) {
  return useQuery({
    queryKey: ["regulation", id],
    queryFn: () => apiFetch<Regulation>(`/regulations/${id}`),
    enabled: !!id,
  });
}

export function useEvidence() {
  return useQuery({
    queryKey: ["evidence"],
    queryFn: () => apiFetch<Evidence[]>("/evidence"),
  });
}

export function useTasks() {
  return useQuery({
    queryKey: ["tasks"],
    queryFn: () => apiFetch<Task[]>("/tasks"),
  });
}

export function useTaskMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (args: { id: string; status: string }) =>
      apiFetch<Task>(`/tasks/${args.id}`, {
        method: "PATCH",
        body: { status: args.status },
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["tasks"] }),
  });
}

export function useIncidents() {
  return useQuery({
    queryKey: ["incidents"],
    queryFn: () => apiFetch<Incident[]>("/incidents"),
  });
}

export function useIncident(id: string) {
  return useQuery({
    queryKey: ["incident", id],
    queryFn: () => apiFetch<Incident>(`/incidents/${id}`),
    enabled: !!id,
  });
}

export function useDataRequests() {
  return useQuery({
    queryKey: ["data-requests"],
    queryFn: () => apiFetch<DataRequest[]>("/data-requests"),
  });
}

export function useDataRequest(id: string) {
  return useQuery({
    queryKey: ["data-request", id],
    queryFn: () => apiFetch<DataRequest>(`/data-requests/${id}`),
    enabled: !!id,
  });
}

export function useProcessingActivities() {
  return useQuery({
    queryKey: ["processing-activities"],
    queryFn: () => apiFetch<ProcessingActivity[]>("/processing-activities"),
  });
}

export function useConnectors() {
  return useQuery({
    queryKey: ["connectors"],
    queryFn: () => apiFetch<Connector[]>("/connectors"),
  });
}

export function useScans() {
  return useQuery({
    queryKey: ["scans"],
    queryFn: () => apiFetch<Scan[]>("/scans"),
  });
}

export function useScanMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (connectorId: string) =>
      apiFetch<{ scan_id: string; status: string }>(
        `/connectors/${connectorId}/scan`,
        { method: "POST" },
      ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["scans"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      qc.invalidateQueries({ queryKey: ["findings"] });
      qc.invalidateQueries({ queryKey: ["connectors"] });
    },
  });
}

export function useSearch(q: string) {
  return useQuery({
    queryKey: ["search", q],
    queryFn: () => apiFetch<SearchResults>(`/search?q=${encodeURIComponent(q)}`),
    enabled: q.trim().length >= 2,
  });
}
