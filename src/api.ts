import type {
  AgentConfig,
  Application,
  ApprovalSettings,
  AuditReport,
  BusinessRecord,
  KnowledgeDocument,
  ObservationThemeCatalog,
  RuntimeStatus,
  ScenarioCase,
  ScenarioInitialInstruction,
  ScenarioRun
} from "./types";

const jsonHeaders = { "Content-Type": "application/json" };

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, init);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `${res.status} ${res.statusText}`);
  }
  return (await res.json()) as T;
}

export const api = {
  runtime: () => request<RuntimeStatus>("/api/runtime"),
  agents: () => request<AgentConfig[]>("/api/agents"),
  updateAgent: (agent: AgentConfig) =>
    request<AgentConfig>(`/api/agents/${agent.id}`, {
      method: "PUT",
      headers: jsonHeaders,
      body: JSON.stringify(agent)
    }),
  documents: () => request<KnowledgeDocument[]>("/api/documents"),
  updateDocument: (doc: KnowledgeDocument) =>
    request<KnowledgeDocument>(`/api/documents/${doc.id}`, {
      method: "PUT",
      headers: jsonHeaders,
      body: JSON.stringify(doc)
    }),
  settings: () => request<{ approval: ApprovalSettings }>("/api/settings"),
  updateSettings: (settings: ApprovalSettings) =>
    request<{ approval: ApprovalSettings }>("/api/settings", {
      method: "PUT",
      headers: jsonHeaders,
      body: JSON.stringify(settings)
    }),
  observationThemes: () => request<ObservationThemeCatalog>("/api/observation-themes"),
  updateObservationTheme: (themeId: string) =>
    request<ObservationThemeCatalog>("/api/observation-theme", {
      method: "PUT",
      headers: jsonHeaders,
      body: JSON.stringify({ themeId })
    }),
  scenarioInstructions: () => request<Record<string, ScenarioInitialInstruction[]>>("/api/scenario-instructions"),
  updateScenarioInstructions: (caseType: Exclude<ScenarioCase, "all">, instructions: ScenarioInitialInstruction[]) =>
    request<Record<string, ScenarioInitialInstruction[]>>(`/api/scenario-instructions/${caseType}`, {
      method: "PUT",
      headers: jsonHeaders,
      body: JSON.stringify({ instructions })
    }),
  runScenario: (caseType: ScenarioCase, mode: "mock" | "live") =>
    request<ScenarioRun>("/api/scenarios/run", {
      method: "POST",
      headers: jsonHeaders,
      body: JSON.stringify({ caseType, mode })
    }),
  scenario: (runId: string) => request<ScenarioRun>(`/api/scenarios/${runId}`),
  applications: (runId?: string) =>
    request<Application[]>(runId ? `/api/applications?runId=${encodeURIComponent(runId)}` : "/api/applications"),
  businessRecords: (runId?: string) =>
    request<BusinessRecord[]>(runId ? `/api/business-records?runId=${encodeURIComponent(runId)}` : "/api/business-records"),
  auditReport: (runId: string) => request<AuditReport>(`/api/audit-reports/${runId}`),
  resetSeed: () => request<{ status: string }>("/api/dev/reset-seed", { method: "POST" })
};
