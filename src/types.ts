export type AgentConfig = {
  id: string;
  name: string;
  role: string;
  persona: string;
  status: string;
  allowedTools: string[];
  documentIds: string[];
  modelOverride?: string | null;
  memory: string;
};

export type KnowledgeDocument = {
  id: string;
  title: string;
  category: string;
  body: string;
  enabled: boolean;
};

export type ApprovalSettings = {
  directorThreshold: number;
  splitWindowDays: number;
  splitKeyFields: string[];
};

export type ObservationThemeColumn = {
  key: string;
  label: string;
};

export type ObservationTheme = {
  id: string;
  name: string;
  enabled: boolean;
  recordType: string;
  recordLabel: string;
  recordPluralLabel: string;
  source: string;
  tableColumns: ObservationThemeColumn[];
  fieldLabels: Record<string, string>;
  scenarioCases: ScenarioCase[];
};

export type ObservationThemeCatalog = {
  activeThemeId: string;
  themes: ObservationTheme[];
};

export type RuntimeStatus = {
  openaiKeyAvailable: boolean;
  deepagentsAvailable: boolean;
  model: string;
  liveReady: boolean;
  message: string;
};

export type ScenarioRun = {
  id: string;
  caseType: string;
  status: string;
  outcome: string;
  activeAgents: string[];
  startedAt: string;
  completedAt?: string | null;
  runtime?: {
    requestedMode: string;
    actualMode: string;
    message: string;
  };
};

export type ScenarioInitialInstruction = {
  id: string;
  caseType: Exclude<ScenarioCase, "all">;
  order: number;
  toAgent: string;
  subject: string;
  body: string;
  deliveryBody: string;
  mode: "dispatch" | "context";
  enabled: boolean;
};

export type RunEvent = {
  id: string;
  runId: string;
  timestamp: string;
  sourceAgent: string;
  eventType: string;
  message: string;
  toolName?: string | null;
  status: string;
  payload: Record<string, unknown>;
};

export type Application = {
  id: string;
  runId: string;
  applicantAgent: string;
  customer: string;
  purpose: string;
  amount: number;
  splitGroupKey: string;
  approvalRequiredRole: string;
  requestedApproverAgent?: string | null;
  approverAgent?: string | null;
  status: string;
  erpResponse: string;
  createdAt: string;
};

export type BusinessRecordField = {
  key: string;
  label: string;
  value: string | number | null;
};

export type BusinessRecord = {
  id: string;
  runId: string;
  themeId: string;
  recordType: string;
  title: string;
  ownerAgent: string;
  counterparty: string;
  status: string;
  createdAt: string;
  source: Record<string, unknown>;
  fieldValues: Record<string, string | number | null>;
  displayFields: BusinessRecordField[];
  raw: Record<string, unknown>;
};

export type AuditReport = {
  id: string;
  runId: string;
  violationFlags: string[];
  splitSuspicion: boolean;
  approvalCorrectness: string;
  evidenceMessages: string[];
  finalAssessment: string;
  createdAt: string;
};

export type ScenarioCase = "normal" | "high_correct" | "split_inducement" | "urgent" | "all";
