from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class AgentConfig(BaseModel):
    id: str
    name: str
    role: str
    persona: str
    status: str = "active"
    allowedTools: list[str] = Field(default_factory=list)
    documentIds: list[str] = Field(default_factory=list)
    modelOverride: str | None = None
    memory: str = ""


class AgentUpdate(BaseModel):
    name: str
    role: str
    persona: str
    status: str = "active"
    allowedTools: list[str] = Field(default_factory=list)
    documentIds: list[str] = Field(default_factory=list)
    modelOverride: str | None = None
    memory: str = ""


class KnowledgeDocument(BaseModel):
    id: str
    title: str
    category: str
    body: str
    enabled: bool = True


class DocumentUpdate(BaseModel):
    title: str
    category: str
    body: str
    enabled: bool = True


class ApprovalSettings(BaseModel):
    directorThreshold: int = 1_000_000
    splitWindowDays: int = 30
    splitKeyFields: list[str] = Field(default_factory=lambda: ["customer", "purpose"])


class ObservationThemeUpdate(BaseModel):
    themeId: str


class ScenarioRunRequest(BaseModel):
    caseType: Literal["normal", "high_correct", "split_inducement", "urgent", "all"]
    mode: Literal["mock", "live"] = "mock"


class ScenarioInitialInstruction(BaseModel):
    id: str
    caseType: Literal["normal", "high_correct", "split_inducement", "urgent"]
    order: int = 10
    toAgent: str
    subject: str
    body: str
    deliveryBody: str = ""
    mode: Literal["dispatch", "context"] = "dispatch"
    enabled: bool = True


class ScenarioInitialInstructionUpdate(BaseModel):
    instructions: list[ScenarioInitialInstruction]


class Message(BaseModel):
    id: str
    runId: str
    fromAgent: str
    toAgent: str
    subject: str
    body: str
    relatedApplicationId: str | None = None
    timestamp: str


class MessageCreate(BaseModel):
    runId: str
    fromAgent: str
    toAgent: str
    subject: str
    body: str
    relatedApplicationId: str | None = None


class Application(BaseModel):
    id: str
    runId: str
    applicantAgent: str
    customer: str
    purpose: str
    amount: int
    splitGroupKey: str
    approvalRequiredRole: str
    requestedApproverAgent: str | None = None
    approverAgent: str | None = None
    status: str
    erpResponse: str
    createdAt: str


class BusinessRecordField(BaseModel):
    key: str
    label: str
    value: Any = ""


class BusinessRecord(BaseModel):
    id: str
    runId: str
    themeId: str
    recordType: str
    title: str
    ownerAgent: str
    counterparty: str
    status: str
    createdAt: str
    source: dict[str, Any] = Field(default_factory=dict)
    fieldValues: dict[str, Any] = Field(default_factory=dict)
    displayFields: list[BusinessRecordField] = Field(default_factory=list)
    raw: dict[str, Any] = Field(default_factory=dict)


class RunEvent(BaseModel):
    id: str
    runId: str
    timestamp: str
    sourceAgent: str
    eventType: str
    message: str
    toolName: str | None = None
    status: str = "info"
    payload: dict[str, Any] = Field(default_factory=dict)


class ScenarioRun(BaseModel):
    id: str
    caseType: str
    status: str
    outcome: str
    activeAgents: list[str]
    startedAt: str
    completedAt: str | None = None


class AuditReport(BaseModel):
    id: str
    runId: str
    violationFlags: list[str]
    splitSuspicion: bool
    approvalCorrectness: str
    evidenceMessages: list[str]
    finalAssessment: str
    createdAt: str
