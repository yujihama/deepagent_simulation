import {
  AlertTriangle,
  BookOpen,
  CheckCircle2,
  FileText,
  MessageSquare,
  Play,
  RefreshCw,
  Save,
  Settings,
  ShieldCheck,
  Users
} from "lucide-react";
import type { CSSProperties, ReactNode } from "react";
import { useEffect, useState } from "react";
import { api } from "./api";
import type {
  AgentConfig,
  AuditReport,
  BusinessRecord,
  BusinessRecordField,
  KnowledgeDocument,
  ObservationTheme,
  ObservationThemeCatalog,
  RunEvent,
  RuntimeStatus,
  ScenarioCase,
  ScenarioInitialInstruction,
  ScenarioRun
} from "./types";

const agentLabels: Record<string, string> = {
  "sales-a": "営業社員A",
  "sales-b": "営業社員B",
  "sales-manager": "営業課長",
  "sales-director": "営業部長",
  "customer-a": "取引先A",
  "erp-agent": "ERP Agent",
  "audit-agent": "監査Agent",
  system: "システム"
};

const scenarioOptions: { id: ScenarioCase; label: string }[] = [
  { id: "normal", label: "正常申請" },
  { id: "high_correct", label: "高額一括" },
  { id: "split_inducement", label: "分割誘発" },
  { id: "urgent", label: "急ぎ依頼" },
  { id: "all", label: "複数比較" }
];

function shortTime(value: string) {
  const date = new Date(value);
  return date.toLocaleTimeString("ja-JP", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function shortDateTime(value: string) {
  const date = new Date(value);
  return date.toLocaleString("ja-JP", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  });
}

function scenarioLabel(caseType: string) {
  return scenarioOptions.find((item) => item.id === caseType)?.label ?? caseType;
}

function App() {
  const [agents, setAgents] = useState<AgentConfig[]>([]);
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([]);
  const [runtime, setRuntime] = useState<RuntimeStatus | null>(null);
  const [themeCatalog, setThemeCatalog] = useState<ObservationThemeCatalog | null>(null);
  const [selectedAgentId, setSelectedAgentId] = useState("sales-a");
  const [selectedDocumentId, setSelectedDocumentId] = useState("erp-check-spec");
  const [mode, setMode] = useState<"mock" | "live">("mock");
  const [selectedScenarioCase, setSelectedScenarioCase] = useState<ScenarioCase>("split_inducement");
  const [scenarioInstructions, setScenarioInstructions] = useState<Record<string, ScenarioInitialInstruction[]>>({});
  const [currentRun, setCurrentRun] = useState<ScenarioRun | null>(null);
  const [scenarioRuns, setScenarioRuns] = useState<ScenarioRun[]>([]);
  const [events, setEvents] = useState<RunEvent[]>([]);
  const [businessRecords, setBusinessRecords] = useState<BusinessRecord[]>([]);
  const [audit, setAudit] = useState<AuditReport | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const selectedAgent = agents.find((agent) => agent.id === selectedAgentId) ?? agents[0];
  const selectedDocument = documents.find((doc) => doc.id === selectedDocumentId) ?? documents[0];
  const activeAgents = agents.filter((agent) => agent.status === "active");
  const activeDocuments = documents.filter((doc) => doc.enabled);
  const splitEvents = events.filter((event) => event.status === "warning").length;
  const currentScenario = scenarioOptions.find((item) => item.id === selectedScenarioCase) ?? scenarioOptions[0];
  const selectedScenarioInstructions = scenarioInstructions[selectedScenarioCase] ?? [];
  const activeTheme = themeCatalog?.themes.find((theme) => theme.id === themeCatalog.activeThemeId);

  useEffect(() => {
    void refreshAll();
  }, []);

  async function refreshAll() {
    try {
      setError(null);
      const [nextAgents, nextDocs, nextRuntime, nextThemeCatalog, nextScenarioInstructions, nextRuns] = await Promise.all([
        api.agents(),
        api.documents(),
        api.runtime(),
        api.observationThemes(),
        api.scenarioInstructions(),
        api.scenarios()
      ]);
      setAgents(nextAgents);
      setDocuments(nextDocs);
      setRuntime(nextRuntime);
      setThemeCatalog(nextThemeCatalog);
      if (nextRuntime.liveReady) {
        setMode("live");
      }
      setScenarioInstructions(nextScenarioInstructions);
      setScenarioRuns(nextRuns);
      if (currentRun?.id) {
        await loadRunDetails(currentRun.id);
      } else {
        setBusinessRecords([]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "初期データの取得に失敗しました");
    }
  }

  async function runScenario(caseType: ScenarioCase) {
    setBusy(true);
    setEvents([]);
    setBusinessRecords([]);
    setAudit(null);
    setError(null);
    try {
      const run = await api.runScenario(caseType, mode);
      setCurrentRun(run);
      const source = new EventSource(`/api/scenarios/${run.id}/stream`);
      source.addEventListener("run_event", (event) => {
        const parsed = JSON.parse((event as MessageEvent).data) as RunEvent;
        setEvents((prev) => [...prev, parsed]);
      });
      source.addEventListener("done", () => {
        source.close();
        setBusy(false);
        void refreshScenarioRuns();
        void loadRunDetails(run.id);
      });
      source.onerror = () => {
        source.close();
        setBusy(false);
        void refreshScenarioRuns();
        void loadRunDetails(run.id);
      };
    } catch (err) {
      setBusy(false);
      setError(err instanceof Error ? err.message : "シナリオ実行に失敗しました");
    }
  }

  async function loadRunDetails(runId: string) {
    const [nextRun, nextEvents, nextRecords, nextAudit] = await Promise.all([
      api.scenario(runId),
      api.runEvents(runId),
      api.businessRecords(runId),
      api.auditReport(runId).catch(() => null)
    ]);
    setCurrentRun(nextRun);
    setEvents(nextEvents);
    setBusinessRecords(nextRecords);
    setAudit(nextAudit);
  }

  async function refreshScenarioRuns() {
    const nextRuns = await api.scenarios();
    setScenarioRuns(nextRuns);
  }

  async function saveAgent(agent: AgentConfig) {
    const saved = await api.updateAgent(agent);
    setAgents((prev) => prev.map((item) => (item.id === saved.id ? saved : item)));
  }

  async function saveDocument(doc: KnowledgeDocument) {
    const saved = await api.updateDocument(doc);
    setDocuments((prev) => prev.map((item) => (item.id === saved.id ? saved : item)));
  }

  async function resetSeed() {
    setBusy(true);
    try {
      await api.resetSeed();
      setCurrentRun(null);
      setEvents([]);
      setBusinessRecords([]);
      setAudit(null);
      await refreshAll();
    } finally {
      setBusy(false);
    }
  }

  function updateSelectedAgent(patch: Partial<AgentConfig>) {
    if (!selectedAgent) return;
    setAgents((prev) => prev.map((agent) => (agent.id === selectedAgent.id ? { ...agent, ...patch } : agent)));
  }

  function updateSelectedDocument(patch: Partial<KnowledgeDocument>) {
    if (!selectedDocument) return;
    setDocuments((prev) => prev.map((doc) => (doc.id === selectedDocument.id ? { ...doc, ...patch } : doc)));
  }

  function updateScenarioInstruction(instructionId: string, patch: Partial<ScenarioInitialInstruction>) {
    if (selectedScenarioCase === "all") return;
    setScenarioInstructions((prev) => ({
      ...prev,
      [selectedScenarioCase]: (prev[selectedScenarioCase] ?? []).map((instruction) =>
        instruction.id === instructionId ? { ...instruction, ...patch } : instruction
      )
    }));
  }

  async function saveScenarioInstructions() {
    if (selectedScenarioCase === "all") return;
    const saved = await api.updateScenarioInstructions(selectedScenarioCase, scenarioInstructions[selectedScenarioCase] ?? []);
    setScenarioInstructions(saved);
  }

  async function changeTheme(themeId: string) {
    try {
      setError(null);
      const nextCatalog = await api.updateObservationTheme(themeId);
      setThemeCatalog(nextCatalog);
      setCurrentRun(null);
      setScenarioRuns(await api.scenarios());
      setEvents([]);
      setBusinessRecords([]);
      setAudit(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "観察テーマの更新に失敗しました");
    }
  }

  return (
    <div className="app-shell">
      <main className="main">
        <header className="topbar">
          <div>
            <h1>Agent Simulation</h1>
          </div>
          <div className="top-actions">
            {themeCatalog && (
              <select
                className="theme-select"
                value={themeCatalog.activeThemeId}
                aria-label="観察テーマ"
                onChange={(event) => void changeTheme(event.target.value)}
              >
                {themeCatalog.themes.map((theme) => (
                  <option key={theme.id} value={theme.id} disabled={!theme.enabled}>
                    {theme.name}
                  </option>
                ))}
              </select>
            )}
            <div className={runtime?.liveReady ? "runtime-pill ok" : "runtime-pill warn"}>
              <span>{runtime?.model ?? "確認中"}</span>
            </div>
            <div className="segmented">
              <button className={mode === "mock" ? "selected" : ""} onClick={() => setMode("mock")}>
                接続確認モック
              </button>
              <button className={mode === "live" ? "selected" : ""} onClick={() => setMode("live")}>
                Live DeepAgent
              </button>
            </div>
            <button className="icon-button" onClick={() => void refreshAll()} title="再読み込み">
              <RefreshCw size={18} />
            </button>
          </div>
        </header>

        {error && <div className="error-banner">{error}</div>}

        <section className="summary-grid">
          <Metric icon={<Users />} label="独立Agent" value={`${activeAgents.length}体`} />
          <Metric icon={<FileText />} label="規定・仕様書" value={`${activeDocuments.length}件`} />
          <Metric icon={<ShieldCheck />} label="観察テーマ" value={activeTheme?.name ?? "申請承認"} />
          <Metric icon={<AlertTriangle />} label="警告イベント" value={`${splitEvents}件`} />
        </section>

        <section className="panel history-panel">
          <div className="panel-header compact">
            <h2>実行履歴</h2>
            {currentRun ? <span className="pill muted">{currentRun.id}</span> : <span className="pill muted">未選択</span>}
          </div>
          <div className="run-history-list">
            {scenarioRuns.length === 0 && <div className="empty inline">実行履歴はまだありません。</div>}
            {scenarioRuns.map((run) => (
              <button
                className={run.id === currentRun?.id ? "run-history-item selected" : "run-history-item"}
                disabled={busy}
                key={run.id}
                onClick={() => void loadRunDetails(run.id)}
              >
                <strong>{scenarioLabel(run.caseType)}</strong>
                <span>{shortDateTime(run.startedAt)}</span>
                <small>{run.id}</small>
                <span className={run.status === "completed" ? "pill good" : run.status === "running" ? "pill running" : "pill warn"}>
                  {run.status}
                </span>
              </button>
            ))}
          </div>
        </section>

        <div className="workspace">
          <section className="panel primary-panel">
            <div className="panel-header">
              <div>
                <h2>Agent名簿エディタ</h2>
              </div>
              <button disabled={!selectedAgent} onClick={() => selectedAgent && void saveAgent(selectedAgent)}>
                <Save size={16} />
                保存
              </button>
            </div>
            <div className="agent-table">
              <div className="table-row header">
                <span>名前</span>
                <span>役割</span>
                <span>参照Docs</span>
                <span>ツール</span>
                <span>状態</span>
              </div>
              {agents.map((agent) => (
                <button
                  className={agent.id === selectedAgentId ? "table-row selected" : "table-row"}
                  key={agent.id}
                  onClick={() => setSelectedAgentId(agent.id)}
                >
                  <strong>{agent.name}</strong>
                  <span>{agent.role}</span>
                  <span>{agent.documentIds.length}件</span>
                  <span>{agent.allowedTools.join(", ") || "-"}</span>
                  <span className={agent.status === "active" ? "pill good" : "pill muted"}>{agent.status}</span>
                </button>
              ))}
            </div>
          </section>

          <aside className="panel inspector">
            <div className="panel-header compact">
              <h2>エージェント詳細</h2>
              <Settings size={18} />
            </div>
            {selectedAgent && (
              <div className="form-stack">
                <label>
                  名前
                  <input value={selectedAgent.name} onChange={(event) => updateSelectedAgent({ name: event.target.value })} />
                </label>
                <label>
                  役割
                  <input value={selectedAgent.role} onChange={(event) => updateSelectedAgent({ role: event.target.value })} />
                </label>
                <label>
                  ペルソナ
                  <textarea
                    value={selectedAgent.persona}
                    rows={5}
                    onChange={(event) => updateSelectedAgent({ persona: event.target.value })}
                  />
                </label>
                <div className="toggle-list">
                  <strong>参照ドキュメント</strong>
                  {documents.map((doc) => (
                    <label className="checkline" key={doc.id}>
                      <input
                        type="checkbox"
                        checked={selectedAgent.documentIds.includes(doc.id)}
                        onChange={(event) => {
                          const set = new Set(selectedAgent.documentIds);
                          if (event.target.checked) set.add(doc.id);
                          else set.delete(doc.id);
                          updateSelectedAgent({ documentIds: [...set] });
                        }}
                      />
                      <span>{doc.title}</span>
                    </label>
                  ))}
                </div>
              </div>
            )}
          </aside>
        </div>

        <div className="workspace lower">
          <section className="panel erp-panel">
            <div className="panel-header">
              <div>
                <h2>観察シナリオ</h2>
              </div>
              <div className="header-actions">
                <button disabled={busy || (selectedScenarioCase !== "all" && selectedScenarioInstructions.length === 0)} onClick={() => void runScenario(selectedScenarioCase)}>
                  <Play size={16} />
                  選択シナリオを実行
                </button>
                <button
                  className="secondary"
                  disabled={busy || selectedScenarioCase === "all"}
                  onClick={() => void saveScenarioInstructions()}
                >
                  <Save size={16} />
                  初動指示を保存
                </button>
                <button className="secondary" onClick={() => void resetSeed()} disabled={busy}>
                  初期化
                </button>
              </div>
            </div>
            <div className="scenario-grid">
              {scenarioOptions.map((item) => (
                <button
                  className={item.id === selectedScenarioCase ? "scenario-button selected" : "scenario-button"}
                  key={item.id}
                  disabled={busy}
                  onClick={() => setSelectedScenarioCase(item.id)}
                >
                  <Play size={16} />
                  <strong>{item.label}</strong>
                </button>
              ))}
            </div>
            <div className="scenario-config">
              <div className="scenario-config-header">
                <div>
                  <h3>初動指示: {currentScenario.label}</h3>
                </div>
                {selectedScenarioCase !== "all" && <span className="pill muted">{selectedScenarioInstructions.length}件</span>}
              </div>
              {selectedScenarioCase !== "all" && (
                <div className="instruction-list">
                  {selectedScenarioInstructions.map((instruction) => (
                    <div className="instruction-card" key={instruction.id}>
                      <div className="instruction-card-top">
                        <label className="checkline">
                          <input
                            type="checkbox"
                            checked={instruction.enabled}
                            onChange={(event) => updateScenarioInstruction(instruction.id, { enabled: event.target.checked })}
                          />
                          <span>有効</span>
                        </label>
                        <label>
                          初動エージェント
                          <select
                            value={instruction.toAgent}
                            onChange={(event) => updateScenarioInstruction(instruction.id, { toAgent: event.target.value })}
                          >
                            {agents.map((agent) => (
                              <option key={agent.id} value={agent.id}>
                                {agent.name}
                              </option>
                            ))}
                          </select>
                        </label>
                        <label>
                          渡し方
                          <select
                            value={instruction.mode}
                            onChange={(event) =>
                              updateScenarioInstruction(instruction.id, {
                                mode: event.target.value as ScenarioInitialInstruction["mode"]
                              })
                            }
                          >
                            <option value="dispatch">dispatch: 起動して実行</option>
                            <option value="context">context: 背景として保持</option>
                          </select>
                        </label>
                      </div>
                      <label>
                        件名
                        <input
                          value={instruction.subject}
                          onChange={(event) => updateScenarioInstruction(instruction.id, { subject: event.target.value })}
                        />
                      </label>
                      <label>
                        表示・記録される初期指示
                        <textarea
                          rows={4}
                          value={instruction.body}
                          onChange={(event) => updateScenarioInstruction(instruction.id, { body: event.target.value })}
                        />
                      </label>
                      {instruction.mode === "dispatch" && (
                        <label>
                          実行時だけ追加する内部指示
                          <textarea
                            rows={4}
                            value={instruction.deliveryBody}
                            onChange={(event) => updateScenarioInstruction(instruction.id, { deliveryBody: event.target.value })}
                          />
                        </label>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
            <BusinessRecordTable records={businessRecords} theme={activeTheme} />
          </section>

          <section className="panel stream-panel">
            <div className="panel-header">
              <div>
                <h2>実行ストリーム</h2>
              </div>
              {busy ? <span className="pill running">実行中</span> : <span className="pill muted">待機</span>}
            </div>
            <div className="event-list">
              {events.length === 0 && <div className="empty">まだイベントはありません。</div>}
              {events.map((event) => (
                <div className={`event-item ${event.status}`} key={event.id}>
                  <time>{shortTime(event.timestamp)}</time>
                  <strong>{agentLabels[event.sourceAgent] ?? event.sourceAgent}</strong>
                  <span>{event.message}</span>
                </div>
              ))}
            </div>
          </section>
        </div>

        <div className="workspace bottom">
          <section className="panel knowledge-panel">
            <div className="panel-header">
              <div>
                <h2>規定・チェック仕様書</h2>
              </div>
              <button disabled={!selectedDocument} onClick={() => selectedDocument && void saveDocument(selectedDocument)}>
                <Save size={16} />
                保存
              </button>
            </div>
            <div className="knowledge-layout">
              <div className="doc-list">
                {documents.map((doc) => (
                  <button
                    key={doc.id}
                    className={doc.id === selectedDocumentId ? "doc-item selected" : "doc-item"}
                    onClick={() => setSelectedDocumentId(doc.id)}
                  >
                    <BookOpen size={16} />
                    <span>{doc.title}</span>
                    <small>{doc.category}</small>
                  </button>
                ))}
              </div>
              {selectedDocument && (
                <div className="doc-editor">
                  <input value={selectedDocument.title} onChange={(event) => updateSelectedDocument({ title: event.target.value })} />
                  <textarea value={selectedDocument.body} rows={12} onChange={(event) => updateSelectedDocument({ body: event.target.value })} />
                  <label className="checkline">
                    <input
                      type="checkbox"
                      checked={selectedDocument.enabled}
                      onChange={(event) => updateSelectedDocument({ enabled: event.target.checked })}
                    />
                    <span>有効</span>
                  </label>
                </div>
              )}
            </div>
          </section>

          <section className="panel audit-panel">
            <div className="panel-header compact">
              <h2>監査Agent評価</h2>
              <ShieldCheck size={18} />
            </div>
            {audit ? (
              <div className="audit-body">
                <div className={`audit-status ${audit.splitSuspicion ? "warn" : "ok"}`}>
                  {audit.splitSuspicion ? <AlertTriangle size={20} /> : <CheckCircle2 size={20} />}
                  <strong>{audit.approvalCorrectness}</strong>
                </div>
                <p>{audit.finalAssessment}</p>
                <div className="flag-list">
                  {audit.violationFlags.map((flag) => (
                    <span className="pill warn" key={flag}>
                      {flag}
                    </span>
                  ))}
                </div>
                <div className="evidence-list">
                  {audit.evidenceMessages.slice(0, 6).map((item) => (
                    <div key={item}>
                      <MessageSquare size={14} />
                      <span>{item}</span>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="empty">監査結果はシナリオ完了後に表示されます。</div>
            )}
          </section>
        </div>
      </main>
    </div>
  );
}

function Metric({ icon, label, value }: { icon: ReactNode; label: string; value: string }) {
  return (
    <div className="metric">
      <div className="metric-icon">{icon}</div>
      <div>
        <span>{label}</span>
        <strong>{value}</strong>
      </div>
    </div>
  );
}

const fallbackRecordFields: BusinessRecordField[] = [
  { key: "customer", label: "相手先", value: "" },
  { key: "purpose", label: "内容", value: "" },
  { key: "amount", label: "金額", value: "" },
  { key: "approvalRequiredRole", label: "必要承認", value: "" },
  { key: "requestedApprover", label: "指定承認", value: "" },
  { key: "status", label: "状態", value: "" }
];

function BusinessRecordTable({ records, theme }: { records: BusinessRecord[]; theme?: ObservationTheme }) {
  const columns = theme?.tableColumns ?? fallbackRecordFields.map(({ key, label }) => ({ key, label }));
  const columnTemplate =
    columns.length === 6 ? "0.8fr 1.25fr 0.75fr 0.8fr 0.85fr 1fr" : `repeat(${columns.length}, minmax(0, 1fr))`;
  const emptyLabel = theme?.recordPluralLabel ?? "業務レコード";
  const rowStyle = { "--record-columns": columnTemplate } as CSSProperties;

  return (
    <div className="application-table">
      <div className="table-row header" style={rowStyle}>
        {columns.map((column) => (
          <span key={column.key}>{column.label}</span>
        ))}
      </div>
      {records.length === 0 && <div className="empty inline">{emptyLabel}はまだありません。</div>}
      {records.map((record) => {
        const values = new Map(record.displayFields.map((field) => [field.key, field.value]));
        return (
          <div className="table-row" key={record.id} style={rowStyle}>
            {columns.map((column, index) => {
              const rawValue = values.get(column.key) ?? record.fieldValues[column.key] ?? "";
              const text = rawValue === null || rawValue === "" ? "-" : String(rawValue);
              if (column.key === "status") {
                return (
                  <span className={text.includes("疑義") || text.includes("差戻し") ? "pill warn" : "pill good"} key={column.key}>
                    {text}
                  </span>
                );
              }
              return index === 0 ? <strong key={column.key}>{text}</strong> : <span key={column.key}>{text}</span>;
            })}
          </div>
        );
      })}
    </div>
  );
}

export default App;
