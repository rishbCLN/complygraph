"use client";

import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { apiFetch } from "./api";
import type {
  AISystem,
  AISystemComponent,
  AISystemFlow,
  AnalysisReport,
  ApprovalRequest,
  Assessment,
  Asset,
  Campaign,
  CampaignResult,
  AssetControl,
  AssetField,
  AuditEvent,
  Connector,
  Control,
  ControlEvidence,
  ControlMapping,
  ControlMappingGraph,
  ControlMappingRef,
  ConsentEvent,
  ConsentNotice,
  ConsentPurpose,
  ConsentRecord,
  ConsentSummary,
  DashboardSummary,
  DataGraph,
  DataPosture,
  DsrDiscoveryItem,
  DsrTask,
  Notification,
  ReassessmentResult,
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
  PortfolioRollup,
  ProcessingActivity,
  Regulation,
  ReusableEvidence,
  Risk,
  RiskSummary,
  Scan,
  SearchResults,
  SelfAudit,
  SeverityCount,
  Task,
  TopFinding,
  Vendor,
  IntegrationStatus,
  WebhookEndpoint,
  WebhookWithSecret,
  WebhookDelivery,
  ExternalTicket,
  MfaStatus,
  MfaEnrollment,
  MfaBackupCodes,
  SSOProviders,
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

export function useControlMappings(id: string) {
  return useQuery({
    queryKey: ["control", id, "mappings"],
    queryFn: () => apiFetch<ControlMappingRef[]>(`/controls/${id}/mappings`),
    enabled: !!id,
  });
}

export function useReusableEvidence(id: string) {
  return useQuery({
    queryKey: ["control", id, "reusable-evidence"],
    queryFn: () =>
      apiFetch<ReusableEvidence[]>(`/controls/${id}/reusable-evidence`),
    enabled: !!id,
  });
}

export function useControlMappingsList() {
  return useQuery({
    queryKey: ["control-mappings"],
    queryFn: () => apiFetch<ControlMapping[]>("/control-mappings"),
  });
}

export function useControlMappingGraph() {
  return useQuery({
    queryKey: ["control-mappings", "graph"],
    queryFn: () => apiFetch<ControlMappingGraph>("/control-mappings/graph"),
  });
}

export function useCreateControlMapping() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: {
      source_control_id: string;
      target_control_id: string;
      relation_type: string;
      rationale?: string;
      confidence?: number;
    }) => apiFetch<ControlMapping>("/control-mappings", { method: "POST", body }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["control-mappings"] });
    },
  });
}

export function useDeleteControlMapping() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      apiFetch(`/control-mappings/${id}`, { method: "DELETE", raw: true }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["control-mappings"] });
    },
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

export function useSelfAudit() {
  return useQuery({
    queryKey: ["self-audit"],
    queryFn: () => apiFetch<SelfAudit>("/self-audit"),
  });
}

export function useCustomPacks() {
  return useQuery({
    queryKey: ["regulations", "packs"],
    queryFn: () => apiFetch<Regulation[]>("/regulations/packs"),
  });
}

export function useImportPackMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (args: { format: "yaml" | "json"; content: string }) =>
      apiFetch<Regulation>("/regulations/packs/import", {
        method: "POST",
        body: args,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["regulations"] });
      qc.invalidateQueries({ queryKey: ["controls"] });
    },
  });
}

export function useDeletePackMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      apiFetch(`/regulations/packs/${id}`, { method: "DELETE", raw: true }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["regulations"] });
      qc.invalidateQueries({ queryKey: ["controls"] });
    },
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

export function useDsrTasks(id: string) {
  return useQuery({
    queryKey: ["data-request", id, "tasks"],
    queryFn: () => apiFetch<DsrTask[]>(`/data-requests/${id}/tasks`),
    enabled: !!id,
  });
}

export function useDsrDiscovery(id: string, enabled: boolean) {
  return useQuery({
    queryKey: ["data-request", id, "discover"],
    queryFn: () => apiFetch<DsrDiscoveryItem[]>(`/data-requests/${id}/discover`),
    enabled: !!id && enabled,
  });
}

export function useVerifyDsr() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      apiFetch<DataRequest>(`/data-requests/${id}/verify`, { method: "POST" }),
    onSuccess: (_data, id) => {
      qc.invalidateQueries({ queryKey: ["data-request", id] });
      qc.invalidateQueries({ queryKey: ["data-requests"] });
    },
  });
}

export function useFulfillDsr() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      apiFetch<DataRequest>(`/data-requests/${id}/fulfill`, { method: "POST" }),
    onSuccess: (_data, id) => {
      qc.invalidateQueries({ queryKey: ["data-request", id] });
      qc.invalidateQueries({ queryKey: ["data-requests"] });
    },
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

// --- Approvals (maker-checker, feature #4) --------------------------------------

export function useApprovals(params: { status?: string; entity_type?: string } = {}) {
  const qs = new URLSearchParams();
  if (params.status) qs.set("status", params.status);
  if (params.entity_type) qs.set("entity_type", params.entity_type);
  const suffix = qs.toString() ? `?${qs.toString()}` : "";
  return useQuery({
    queryKey: ["approvals", params],
    queryFn: () => apiFetch<ApprovalRequest[]>(`/approvals${suffix}`),
  });
}

export function useSubmitApproval() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: {
      entity_type: string;
      entity_id: string;
      action: string;
      payload?: Record<string, unknown>;
      summary?: string;
    }) => apiFetch<ApprovalRequest>("/approvals", { method: "POST", body }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["approvals"] }),
  });
}

export function useReviewApproval() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (args: { id: string; decision: "approve" | "reject" | "cancel"; note?: string }) =>
      apiFetch<ApprovalRequest>(`/approvals/${args.id}/${args.decision}`, {
        method: "POST",
        body: args.decision === "cancel" ? undefined : { note: args.note },
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["approvals"] });
      qc.invalidateQueries({ queryKey: ["findings"] });
      qc.invalidateQueries({ queryKey: ["risks"] });
    },
  });
}

// --- Audit campaigns (feature #5) -----------------------------------------------

export function useCampaigns(status?: string) {
  const suffix = status ? `?status=${status}` : "";
  return useQuery({
    queryKey: ["campaigns", status || "all"],
    queryFn: () => apiFetch<Campaign[]>(`/campaigns${suffix}`),
  });
}

export function useCampaign(id: string) {
  return useQuery({
    queryKey: ["campaign", id],
    queryFn: () => apiFetch<Campaign>(`/campaigns/${id}`),
    enabled: !!id,
  });
}

export function useCampaignResults(id: string, status?: string) {
  const suffix = status ? `?status=${status}` : "";
  return useQuery({
    queryKey: ["campaign", id, "results", status || "all"],
    queryFn: () => apiFetch<CampaignResult[]>(`/campaigns/${id}/results${suffix}`),
    enabled: !!id,
  });
}

export function useCreateCampaign() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { name: string; description?: string; scope_regulation_ids?: string[] }) =>
      apiFetch<Campaign>("/campaigns", { method: "POST", body }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["campaigns"] }),
  });
}

export function useRunCampaign() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => apiFetch<Campaign>(`/campaigns/${id}/run`, { method: "POST" }),
    onSuccess: (_data, id) => {
      qc.invalidateQueries({ queryKey: ["campaigns"] });
      qc.invalidateQueries({ queryKey: ["campaign", id] });
    },
  });
}

export function useDeleteCampaign() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => apiFetch(`/campaigns/${id}`, { method: "DELETE", raw: true }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["campaigns"] }),
  });
}

// --- Risk register (feature #3) -------------------------------------------------

export function useRisks(params: { status?: string; category?: string } = {}) {
  const qs = new URLSearchParams();
  if (params.status) qs.set("status", params.status);
  if (params.category) qs.set("category", params.category);
  const suffix = qs.toString() ? `?${qs.toString()}` : "";
  return useQuery({
    queryKey: ["risks", params],
    queryFn: () => apiFetch<Risk[]>(`/risks${suffix}`),
  });
}

export function useRisk(id: string) {
  return useQuery({
    queryKey: ["risk", id],
    queryFn: () => apiFetch<Risk>(`/risks/${id}`),
    enabled: !!id,
  });
}

export function useRiskSummary() {
  return useQuery({
    queryKey: ["risks", "summary"],
    queryFn: () => apiFetch<RiskSummary>("/risks/summary"),
  });
}

export function useCreateRisk() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: Record<string, unknown>) =>
      apiFetch<Risk>("/risks", { method: "POST", body }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["risks"] }),
  });
}

export function useUpdateRisk() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (args: { id: string; body: Record<string, unknown> }) =>
      apiFetch<Risk>(`/risks/${args.id}`, { method: "PATCH", body: args.body }),
    onSuccess: (_data, args) => {
      qc.invalidateQueries({ queryKey: ["risk", args.id] });
      qc.invalidateQueries({ queryKey: ["risks"] });
    },
  });
}

export function useAcceptRisk() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (args: { id: string; rationale: string; expires_at?: string }) =>
      apiFetch<Risk>(`/risks/${args.id}/accept`, {
        method: "POST",
        body: { rationale: args.rationale, expires_at: args.expires_at },
      }),
    onSuccess: (_data, args) => {
      qc.invalidateQueries({ queryKey: ["risk", args.id] });
      qc.invalidateQueries({ queryKey: ["risks"] });
    },
  });
}

export function useCloseRisk() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      apiFetch<Risk>(`/risks/${id}/close`, { method: "POST" }),
    onSuccess: (_data, id) => {
      qc.invalidateQueries({ queryKey: ["risk", id] });
      qc.invalidateQueries({ queryKey: ["risks"] });
    },
  });
}

export function useDeleteRisk() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      apiFetch(`/risks/${id}`, { method: "DELETE", raw: true }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["risks"] }),
  });
}

// --- AI systems ----------------------------------------------------------------

export function useAiSystems() {
  return useQuery({
    queryKey: ["ai-systems"],
    queryFn: () => apiFetch<AISystem[]>("/systems"),
  });
}

export function useAiSystem(id: string) {
  return useQuery({
    queryKey: ["ai-system", id],
    queryFn: () => apiFetch<AISystem>(`/systems/${id}`),
    enabled: !!id,
  });
}

export function useAiSystemComponents(id: string) {
  return useQuery({
    queryKey: ["ai-system", id, "components"],
    queryFn: () => apiFetch<AISystemComponent[]>(`/systems/${id}/components`),
    enabled: !!id,
  });
}

export function useAiSystemFlows(id: string) {
  return useQuery({
    queryKey: ["ai-system", id, "flows"],
    queryFn: () => apiFetch<AISystemFlow[]>(`/systems/${id}/flows`),
    enabled: !!id,
  });
}

export function useAnalyzeSystemMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      apiFetch<AnalysisReport>(`/systems/${id}/analyze`, { method: "POST" }),
    onSuccess: (_data, id) => {
      qc.invalidateQueries({ queryKey: ["ai-system", id] });
      qc.invalidateQueries({ queryKey: ["ai-systems"] });
    },
  });
}

export function useAnalyzeAllSystemsMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () =>
      apiFetch<PortfolioRollup>("/systems/analyze-all", { method: "POST" }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["ai-systems"] });
    },
  });
}

// --- Consent management (feature #8) ---------------------------------------
export function useConsentPurposes(activeOnly = false) {
  return useQuery({
    queryKey: ["consent-purposes", activeOnly],
    queryFn: () =>
      apiFetch<ConsentPurpose[]>(`/consent/purposes${activeOnly ? "?active_only=true" : ""}`),
  });
}

export function useConsentSummary() {
  return useQuery({
    queryKey: ["consent-summary"],
    queryFn: () => apiFetch<ConsentSummary>("/consent/summary"),
  });
}

export function useConsentNotices() {
  return useQuery({
    queryKey: ["consent-notices"],
    queryFn: () => apiFetch<ConsentNotice[]>("/consent/notices"),
  });
}

export function useConsentRecords(params: { purpose_id?: string; status?: string } = {}) {
  const qs = new URLSearchParams();
  if (params.purpose_id) qs.set("purpose_id", params.purpose_id);
  if (params.status) qs.set("status", params.status);
  const suffix = qs.toString() ? `?${qs.toString()}` : "";
  return useQuery({
    queryKey: ["consent-records", params],
    queryFn: () => apiFetch<ConsentRecord[]>(`/consent/records${suffix}`),
  });
}

export function useConsentEvents(params: { principal?: string; purpose_id?: string } = {}) {
  const qs = new URLSearchParams();
  if (params.principal) qs.set("principal", params.principal);
  if (params.purpose_id) qs.set("purpose_id", params.purpose_id);
  const suffix = qs.toString() ? `?${qs.toString()}` : "";
  return useQuery({
    queryKey: ["consent-events", params],
    queryFn: () => apiFetch<ConsentEvent[]>(`/consent/events${suffix}`),
  });
}

export function useCreatePurpose() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: Record<string, unknown>) =>
      apiFetch<ConsentPurpose>("/consent/purposes", { method: "POST", body }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["consent-purposes"] });
      qc.invalidateQueries({ queryKey: ["consent-summary"] });
    },
  });
}

export function useUpdatePurpose() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: Record<string, unknown> }) =>
      apiFetch<ConsentPurpose>(`/consent/purposes/${id}`, { method: "PATCH", body }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["consent-purposes"] });
    },
  });
}

export function useArchivePurpose() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      apiFetch<ConsentPurpose>(`/consent/purposes/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["consent-purposes"] });
      qc.invalidateQueries({ queryKey: ["consent-summary"] });
    },
  });
}

export function useCreateNotice() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { title: string; body: string; publish: boolean }) =>
      apiFetch<ConsentNotice>("/consent/notices", { method: "POST", body }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["consent-notices"] });
      qc.invalidateQueries({ queryKey: ["consent-summary"] });
    },
  });
}

export function usePublishNotice() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      apiFetch<ConsentNotice>(`/consent/notices/${id}/publish`, { method: "POST" }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["consent-notices"] });
      qc.invalidateQueries({ queryKey: ["consent-summary"] });
    },
  });
}

export function useConsentAction() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      action,
      purpose_id,
      principal_identifier,
    }: {
      action: "grant" | "withdraw";
      purpose_id: string;
      principal_identifier: string;
    }) =>
      apiFetch<ConsentRecord>(`/consent/${action}`, {
        method: "POST",
        body: { purpose_id, principal_identifier },
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["consent-records"] });
      qc.invalidateQueries({ queryKey: ["consent-events"] });
      qc.invalidateQueries({ queryKey: ["consent-summary"] });
    },
  });
}

// --- Notifications / reminders (feature #6) --------------------------------
export function useNotifications(state?: string) {
  return useQuery({
    queryKey: ["notifications", state ?? "active"],
    queryFn: () =>
      apiFetch<Notification[]>(`/notifications${state ? `?state=${state}` : ""}`),
    refetchInterval: 60000,
  });
}

export function useUnreadCount() {
  return useQuery({
    queryKey: ["notifications", "unread-count"],
    queryFn: () => apiFetch<{ unread: number }>("/notifications/unread-count"),
    refetchInterval: 60000,
  });
}

function invalidateNotifications(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: ["notifications"] });
}

export function useMarkNotificationRead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      apiFetch<Notification>(`/notifications/${id}/read`, { method: "POST" }),
    onSuccess: () => invalidateNotifications(qc),
  });
}

export function useDismissNotification() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      apiFetch<Notification>(`/notifications/${id}/dismiss`, { method: "POST" }),
    onSuccess: () => invalidateNotifications(qc),
  });
}

export function useMarkAllNotificationsRead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => apiFetch<{ unread: number }>("/notifications/read-all", { method: "POST" }),
    onSuccess: () => invalidateNotifications(qc),
  });
}

export function useGenerateReminders() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () =>
      apiFetch<{ total: number; by_kind: Record<string, number> }>("/notifications/generate", {
        method: "POST",
      }),
    onSuccess: () => invalidateNotifications(qc),
  });
}

export function useRunReassessment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => apiFetch<ReassessmentResult>("/reassessment/run", { method: "POST" }),
    onSuccess: () => {
      invalidateNotifications(qc);
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      qc.invalidateQueries({ queryKey: ["controls"] });
    },
  });
}

// --- Integrations: status, webhooks, tickets (feature #10) -----------------
export function useIntegrationStatus() {
  return useQuery({
    queryKey: ["integrations", "status"],
    queryFn: () => apiFetch<IntegrationStatus>("/integrations/status"),
  });
}

export function useWebhooks() {
  return useQuery({
    queryKey: ["integrations", "webhooks"],
    queryFn: () => apiFetch<WebhookEndpoint[]>("/integrations/webhooks"),
  });
}

export function useWebhookDeliveries(id: string) {
  return useQuery({
    queryKey: ["integrations", "webhooks", id, "deliveries"],
    queryFn: () =>
      apiFetch<WebhookDelivery[]>(`/integrations/webhooks/${id}/deliveries`),
    enabled: !!id,
  });
}

export function useCreateWebhook() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { name: string; url: string; events: string[] }) =>
      apiFetch<WebhookWithSecret>("/integrations/webhooks", { method: "POST", body }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["integrations", "webhooks"] }),
  });
}

export function useUpdateWebhook() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (args: {
      id: string;
      body: { name?: string; url?: string; events?: string[]; enabled?: boolean };
    }) =>
      apiFetch<WebhookEndpoint>(`/integrations/webhooks/${args.id}`, {
        method: "PATCH",
        body: args.body,
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["integrations", "webhooks"] }),
  });
}

export function useDeleteWebhook() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      apiFetch(`/integrations/webhooks/${id}`, { method: "DELETE", raw: true }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["integrations", "webhooks"] }),
  });
}

export function useRotateWebhookSecret() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      apiFetch<WebhookWithSecret>(`/integrations/webhooks/${id}/rotate-secret`, {
        method: "POST",
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["integrations", "webhooks"] }),
  });
}

export function useTestWebhook() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      apiFetch<WebhookDelivery>(`/integrations/webhooks/${id}/test`, { method: "POST" }),
    onSuccess: (_data, id) => {
      qc.invalidateQueries({ queryKey: ["integrations", "webhooks"] });
      qc.invalidateQueries({ queryKey: ["integrations", "webhooks", id, "deliveries"] });
    },
  });
}

export function useTickets(params: { entity_type: string; entity_id: string }) {
  const qs = new URLSearchParams({
    entity_type: params.entity_type,
    entity_id: params.entity_id,
  });
  return useQuery({
    queryKey: ["tickets", params],
    queryFn: () => apiFetch<ExternalTicket[]>(`/integrations/tickets?${qs.toString()}`),
    enabled: !!params.entity_id,
  });
}

export function useCreateTicket() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: {
      provider: string;
      entity_type: string;
      entity_id: string;
      summary?: string;
      description?: string;
    }) => apiFetch<ExternalTicket>("/integrations/tickets", { method: "POST", body }),
    onSuccess: (_data, vars) =>
      qc.invalidateQueries({
        queryKey: ["tickets", { entity_type: vars.entity_type, entity_id: vars.entity_id }],
      }),
  });
}

// --- MFA (feature #10) -----------------------------------------------------
export function useMfaStatus() {
  return useQuery({
    queryKey: ["mfa", "status"],
    queryFn: () => apiFetch<MfaStatus>("/auth/mfa"),
  });
}

export function useMfaEnroll() {
  return useMutation({
    mutationFn: () => apiFetch<MfaEnrollment>("/auth/mfa/enroll", { method: "POST" }),
  });
}

export function useMfaActivate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (code: string) =>
      apiFetch<MfaBackupCodes>("/auth/mfa/activate", { method: "POST", body: { code } }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["mfa", "status"] });
      qc.invalidateQueries({ queryKey: ["me"] });
    },
  });
}

export function useMfaRegenerateBackupCodes() {
  return useMutation({
    mutationFn: () =>
      apiFetch<MfaBackupCodes>("/auth/mfa/backup-codes", { method: "POST" }),
  });
}

export function useMfaDisable() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (password: string) =>
      apiFetch<{ message: string }>("/auth/mfa/disable", {
        method: "POST",
        body: { password },
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["mfa", "status"] });
      qc.invalidateQueries({ queryKey: ["me"] });
    },
  });
}

// --- SSO discovery (feature #10) -------------------------------------------
export function useSSOProviders() {
  return useQuery({
    queryKey: ["sso", "providers"],
    queryFn: () => apiFetch<SSOProviders>("/sso/providers"),
    retry: false,
    staleTime: 5 * 60_000,
  });
}
