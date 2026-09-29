export type Json =
  null | boolean | number | string | Json[] | { [key: string]: Json };
export type Step = {
  start_year: number;
  value: number;
  unit: "relative_exposure" | "percent_energy";
  reference_period: string | null;
};
export type AccessStep = {
  start_year: number;
  access_fraction: number;
  coverage_fraction: number;
  monthly_price_usd: number;
  monthly_copay_usd: number;
  supply_fraction: number;
};
export type Scenario = {
  name: string;
  description: string;
  years: number;
  baseline_year: number;
  sex: string;
  health_structure: string;
  mode: string;
  allow_extrapolation: boolean;
  exposures: Record<string, number>;
  diet: Record<
    string,
    { target: number; unit: string; reference_period: string; role: string }
  >;
  upf_schedule: Step[];
  diet_response: { kind: string; shape: string };
  glp1: { access_schedule: AccessStep[] } | null;
};
export type Edit = { value: number; low?: number | null; high?: number | null };
export type Experiment = {
  catalog_id: string;
  scenario: Scenario;
  overrides: Record<string, Edit>;
  profile: string;
  seed: number;
  reference_id: string | null;
  prediction: string;
  notes: string;
};
export type Entry = {
  id: string;
  label: string;
  classification: string;
  scenario: Scenario;
  package: string;
};
export type Guide = {
  question: string;
  read: string;
  mechanism: string;
  try: string;
  limit: string;
};
export type Parameter = {
  key: string;
  value: number;
  unit: string;
  status: string;
  evidence_grade: string;
  source: string;
  source_url: string | null;
  citation: string | null;
  notes: string | null;
  uncertainty: {
    kind: string;
    low: number | null;
    high: number | null;
    rationale: string;
  };
  lower_bound: number | null;
  upper_bound: number | null;
};
export type Trace = {
  name?: string;
  x?: Json[];
  y?: Json[];
  z?: Json[][];
  text?: Json[];
  type?: string;
  [key: string]: Json | undefined;
};
export type Figure = { data: Trace[]; layout: Record<string, Json> };
export type Chart = { id: string; figure: Figure; guide: Guide };
export type Receipt = {
  id: string;
  name: string;
  status: string;
  stage: string;
  created_at: string;
  profile: string;
  error?: string;
  commentary_sha256: string;
  resolved_evidence_sha256: string;
  code: string;
};
export type Comparison = {
  reference_label: string;
  experiment_label: string;
  year: number;
  outcomes: {
    metric: string;
    unit: string;
    reference: number;
    experiment: number;
    absolute_delta: number;
    relative_delta: number | null;
  }[];
  assumptions: { field: string; reference: Json; experiment: Json }[];
  interval_note: string;
};
export type Result = {
  receipt: Receipt;
  request: Experiment;
  charts?: Chart[];
  summary?: string[];
  reference?: { charts: Chart[]; summary: string[] };
  comparison?: Comparison;
  sources?: Record<string, Parameter>;
  notes?: string;
};
