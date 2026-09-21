// Types mirror the FastAPI response schemas. Kept manually in sync with the
// backend routers under apps/api/app/api/routers.

export type Page<T> = {
  items: T[];
  total: number;
  page: number;
  page_size: number;
};

export type Me = {
  id: string;
  email: string;
  full_name: string;
  role: string;
  capabilities: string[];
  organization: { id: string; name: string; slug: string; role: string };
};

// Audit campaigns (feature #5).
export type CampaignSummary = {
  total: number;
  applicable: number;
  passing: number;
  by_status: Record<string, number>;
  coverage: number;
};

export type Campaign = {
  id: string;
  name: string;
  description: string | null;
  scope_regulation_ids: string[] | null;
  status: string;
  assessment_date: string | null;
  started_at: string | null;
  completed_at: string | null;
  summary: CampaignSummary | null;
  created_at: string | null;
};

export type CampaignResult = {
  id: string;
  control_id: string | null;
  control_code: string;
  control_title: string | null;
  regulation_name: string | null;
  category: string | null;
  status: string;
  score: number;
  reason: string | null;
};

export type CampaignCompare = {
  campaign_id: string;
  baseline_id: string;
  regressed: { code: string; from: string; to: string }[];
  improved: { code: string; from: string; to: string }[];
  added: { code: string; status: string }[];
  removed: { code: string; status: string }[];
};

// Maker-checker approval workflow (feature #4).
export type ApprovalRequest = {
  id: string;
  entity_type: string;
  entity_id: string;
  action: string;
  payload: Record<string, unknown> | null;
  summary: string | null;
  status: string;
  submitted_by: string | null;
  submitted_at: string;
  reviewed_by: string | null;
  reviewed_at: string | null;
  review_note: string | null;
};

export type DashboardSummary = {
  organization: string;
  assessment_date: string;
  data_assets: number;
  personal_data_assets: number;
  open_findings: number;
  critical_findings: number;
  control_coverage: number;
  evidence_stale_pct: number;
  unmapped_data_flows: number;
  vendors_processing_personal_data: number;
  upcoming_obligations: number;
  control_status_breakdown: Record<string, number>;
  evidence_freshness: Record<string, number>;
};

export type SeverityCount = { severity: string; count: number };
export type TopFinding = {
  id: string;
  title: string;
  severity: string;
  risk_score: number;
  status: string;
};
export type DataPosture = {
  categories: { category: string; count: number }[];
  sensitivity: { level: number; count: number }[];
};

export type Finding = {
  id: string;
  title: string;
  description: string | null;
  severity: string;
  risk_score: number;
  risk_breakdown: Record<string, number> | null;
  status: string;
  source: string | null;
  data_categories: string | null;
  recommended_actions: string[] | null;
  evidence_refs: unknown[] | null;
  control_id: string | null;
  control_code: string | null;
  asset_id: string | null;
  asset_name: string | null;
  vendor_id: string | null;
  owner: string | null;
  resolution_note: string | null;
  detected_at: string | null;
  due_at: string | null;
  resolved_at: string | null;
};

export type Control = {
  id: string;
  code: string;
  title: string;
  description: string | null;
  category: string;
  legal_reference: string | null;
  source_section: string | null;
  regulation_name: string | null;
  effective_from: string | null;
  temporal_status: string;
  severity_default: string;
  latest_status: string | null;
  latest_score: number | null;
};

export type MappedControl = {
  id: string;
  code: string;
  title: string;
  category: string;
  regulation_id: string | null;
  regulation_name: string | null;
};

export type ControlMapping = {
  id: string;
  source: MappedControl;
  target: MappedControl;
  relation_type: string;
  rationale: string | null;
  confidence: number;
  system: boolean;
};

export type ControlMappingGraph = {
  nodes: MappedControl[];
  edges: {
    id: string;
    source: string;
    target: string;
    relation_type: string;
    confidence: number;
    system: boolean;
  }[];
};

// Per-control mapping (normalised to an outward view via `direction`).
export type ControlMappingRef = {
  id: string;
  relation_type: string;
  rationale: string | null;
  confidence: number;
  system: boolean;
  direction: "outgoing" | "incoming";
  other: MappedControl;
};

export type ReusableEvidence = {
  evidence_id: string;
  evidence_name: string;
  evidence_type: string;
  status: string;
  relation_type_on_source: string;
  via_mapping_id: string;
  mapping_relation: string;
  mapping_confidence: number;
  source_control: MappedControl;
  requires_review: boolean;
};

export type QualityItem = {
  type: string;
  id: string;
  label: string;
  detail: string;
};

export type QualityCheck = {
  key: string;
  title: string;
  category: string;
  severity: string;
  recommendation: string;
  total: number;
  complete: number;
  incomplete: number;
  score: number;
  items: QualityItem[];
  items_truncated: boolean;
};

export type SelfAudit = {
  organization: string;
  assessment_date: string;
  overall_score: number;
  total_gaps: number;
  check_count: number;
  checks: QualityCheck[];
};

export type Assessment = {
  id: string;
  control_id: string;
  status: string;
  score: number;
  assessment_date: string;
  reason: string | null;
  evidence_count: number;
  automated: boolean;
};

export type ControlEvidence = {
  id: string;
  name: string;
  type: string;
  status: string;
  relation_type: string;
  collected_at: string | null;
  expires_at: string | null;
  hash: string | null;
};

export type Asset = {
  id: string;
  name: string;
  display_name: string | null;
  asset_type: string;
  system_name: string | null;
  environment: string | null;
  classification: string;
  sensitivity_level: number;
  owner: string | null;
  row_count: number | null;
  field_count: number;
  personal_data: boolean;
  last_seen_at: string | null;
};

export type AssetField = {
  id: string;
  name: string;
  data_type: string | null;
  classification: string;
  category: string;
  confidence: number;
  confidence_band: string;
  detection_method: string | null;
  needs_review: boolean;
  masked_examples: string | null;
};

export type Vendor = {
  id: string;
  name: string;
  description: string | null;
  service_type: string | null;
  country: string | null;
  data_processing: string | null;
  contract_status: string;
  risk_level: string;
  owner: string | null;
  personal_data_flows: number;
  open_findings: number;
};

export type Regulation = {
  id: string;
  name: string;
  jurisdiction: string;
  version: string | null;
  source_document: string | null;
  source_url?: string | null;
  pack?: string | null;
  pack_version?: string | null;
  legal_status?: string;
  effective_from: string | null;
  status: string;
  enabled: boolean;
  obligation_count: number;
  is_custom: boolean;
};

export type Obligation = {
  id: string;
  code: string;
  title: string;
  description: string | null;
  legal_reference: string | null;
  source_section: string | null;
  effective_from: string | null;
  control_count: number;
};

export type AuditEvent = {
  id: string;
  action: string;
  entity_type: string | null;
  entity_id: string | null;
  user_id: string | null;
  metadata: Record<string, unknown> | null;
  ip_address: string | null;
  created_at: string | null;
};

export type GraphNode = {
  id: string;
  kind: string;
  type: string;
  label: string;
  asset_type?: string;
  classification?: string;
  sensitivity_level?: number;
  personal_data?: boolean;
  system?: string | null;
  environment?: string | null;
  country?: string | null;
  contract_status?: string | null;
  risk_level?: string | null;
  center?: boolean;
};

export type GraphEdge = {
  id: string;
  source: string;
  target: string;
  relation: string;
  flow_type: string;
  personal_data: boolean;
  sensitive: boolean;
  cross_border: boolean;
  purpose: string | null;
  discovered: boolean;
  confidence: number;
};

export type DataGraph = {
  nodes: GraphNode[];
  edges: GraphEdge[];
  stats?: {
    assets: number;
    vendors: number;
    flows: number;
    cross_border_flows: number;
  };
};

export type RootCause = {
  title: string;
  likelihood: number;
  evidence: string[];
  reasoning: string;
};

export type RecommendedAction = {
  action: string;
  priority: string;
  owner_type: string;
  requires_human_review: boolean;
};

export type Investigation = {
  id: string;
  finding_id: string | null;
  mode: string;
  model: string | null;
  status: string;
  summary: string | null;
  root_causes: RootCause[] | null;
  recommendations: RecommendedAction[] | null;
  missing_evidence: string[] | null;
  legal_review_required: boolean;
  uncertainty: string | null;
  evidence_considered: string[] | null;
  input_sanitized: boolean;
  input_sanitized_notice?: string;
  raw_pii_excluded_notice?: string;
};

export type Flow = {
  id: string;
  source_asset_id: string | null;
  destination_asset_id: string | null;
  flow_type: string;
  purpose: string | null;
  contains_personal_data: boolean;
  cross_border: boolean;
  vendor_id: string | null;
  categories: string | null;
};

export type AssetControl = {
  control_id: string;
  code: string;
  title: string;
  reason: string | null;
  applicable: boolean;
};

export type Evidence = {
  id: string;
  type: string;
  name: string;
  description: string | null;
  source: string | null;
  hash: string | null;
  status: string;
  owner: string | null;
  collected_at: string | null;
  expires_at: string | null;
  linked_controls: number;
};

export type Task = {
  id: string;
  title: string;
  description: string | null;
  finding_id: string | null;
  assignee_id: string | null;
  priority: string;
  status: string;
  due_at: string | null;
  completed_at: string | null;
};

export type Incident = {
  id: string;
  title: string;
  description: string | null;
  severity: string;
  status: string;
  detected_at: string | null;
  contained_at: string | null;
  affected_records_estimate: number | null;
  board_notification_status: string;
  principal_notification_status: string;
  root_cause: string | null;
  remediation: string | null;
  timeline: { events?: { at: string; event: string }[] } | null;
};

export type DataRequest = {
  id: string;
  requester_identifier: string;
  request_type: string;
  status: string;
  verification_status: string;
  received_at: string | null;
  due_at: string | null;
  completed_at: string | null;
  notes: string | null;
};

export type ProcessingActivity = {
  id: string;
  name: string;
  purpose: string | null;
  description: string | null;
  lawful_basis: string | null;
  owner: string | null;
  status: string;
  retention_period_days: number | null;
  has_notice: boolean;
  has_consent: boolean;
};

export type Organization = {
  id: string;
  name: string;
  slug: string;
  industry: string | null;
  country: string;
  plan: string;
  assessment_date: string | null;
};

export type Connector = {
  id: string;
  name: string;
  type: string;
  status: string;
  last_scan_at: string | null;
  created_at: string;
};

export type Scan = {
  id: string;
  connector_id: string | null;
  status: string;
  stage: string | null;
  progress: number;
  items_scanned: number;
  findings_created: number;
  changes: Record<string, unknown> | null;
  error_message: string | null;
  created_at: string;
  completed_at: string | null;
};

export type SearchResults = {
  query: string;
  assets: { id: string; label: string; type: string }[];
  findings: { id: string; label: string; severity: string }[];
  controls: { id: string; label: string; code: string }[];
  vendors: { id: string; label: string }[];
};

// --- AI systems (AI Compliance Compiler) ---------------------------------------

export type AISystem = {
  id: string;
  name: string;
  description: string | null;
  business_purpose: string | null;
  owner: string | null;
  system_type: string;
  risk_domain: string | null;
  lifecycle_stage: string;
  review_status: string;
  sector: string;
  regions: string[] | null;
  deployment_environment: string | null;
  processes_personal_data: boolean;
  makes_automated_decisions: boolean;
  high_risk: boolean;
  last_reviewed_at: string | null;
  last_changed_at: string | null;
  component_count: number;
  flow_count: number;
};

export type AISystemComponent = {
  id: string;
  name: string;
  component_type: string;
  description: string | null;
  provider: string | null;
  region: string | null;
  external: boolean;
  vendor_id: string | null;
  data_asset_id: string | null;
  data_categories: string[] | null;
  config: Record<string, unknown> | null;
};

export type AISystemFlow = {
  id: string;
  source_component_id: string | null;
  target_component_id: string | null;
  relation: string;
  purpose: string | null;
  data_categories: string[] | null;
  contains_personal_data: boolean;
  cross_border: boolean;
};

// Risk register (feature #3).
export type Risk = {
  id: string;
  title: string;
  description: string | null;
  category: string;
  status: string;
  owner: string | null;
  inherent_likelihood: number;
  inherent_impact: number;
  residual_likelihood: number;
  residual_impact: number;
  inherent_score: number;
  inherent_severity: string;
  residual_score: number;
  residual_severity: string;
  treatment_strategy: string;
  treatment_plan: string | null;
  single_loss_expectancy: number | null;
  annual_rate_of_occurrence: number | null;
  ale: number | null;
  rto_hours: number | null;
  rpo_hours: number | null;
  max_tolerable_downtime_hours: number | null;
  business_impact: string | null;
  accepted_by: string | null;
  accepted_at: string | null;
  acceptance_rationale: string | null;
  acceptance_expires_at: string | null;
  review_due_at: string | null;
  control_id: string | null;
  finding_id: string | null;
  vendor_id: string | null;
  ai_system_id: string | null;
  processing_activity_id: string | null;
  created_at: string | null;
};

export type RiskSummary = {
  total: number;
  open: number;
  by_status: Record<string, number>;
  by_severity: Record<string, number>;
  heatmap: number[][];
  total_ale: number;
};

// How a derived fact was determined (Feature #4).
export type FactProvenance = {
  confidence: "DECLARED" | "OBSERVED" | "INFERRED" | "UNKNOWN";
  band: "HIGH" | "MEDIUM" | "LOW";
  basis: string;
};

export type AnalyzedControl = {
  code: string;
  title: string;
  category: string;
  severity: string;
  evaluator_key: string | null;
  scope: "system" | "org_wide";
  applicable: boolean;
  status: string;
  reason: string;
  recommended_actions: string[] | null;
};

export type ChangeTransition = { code: string; from: string; to: string };

export type ChangeImpact = {
  is_baseline: boolean;
  previous_at: string | null;
  regressed: ChangeTransition[];
  improved: ChangeTransition[];
  added: { code: string; status: string }[];
  removed: { code: string; status: string }[];
  unchanged: number;
};

export type AnalysisReport = {
  system_id: string;
  system_name: string;
  assessment_date: string;
  facts: Record<string, unknown>;
  fact_provenance: Record<string, FactProvenance>;
  summary: {
    total: number;
    applicable: number;
    by_status: Record<string, number>;
  };
  controls: AnalyzedControl[];
  changes: ChangeImpact;
};

export type PortfolioSystem = {
  system_id: string;
  system_name: string;
  sector: string;
  summary: {
    total: number;
    applicable: number;
    by_status: Record<string, number>;
  };
  regressed: ChangeTransition[];
  improved: ChangeTransition[];
  is_baseline: boolean;
};

export type PortfolioRollup = {
  organization: string;
  assessment_date: string;
  generated_at: string;
  system_count: number;
  systems_with_failures: number;
  total_regressions: number;
  systems: PortfolioSystem[];
};
