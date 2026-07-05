// Mirrors backend/app/agent/state.py — keep in sync manually for now (small
// enough surface that a shared schema package would be overkill).

export type TraceStep =
  | "planning"
  | "routing"
  | "tool_call"
  | "tool_result"
  | "critique"
  | "final"
  | "error";

export interface TraceEvent {
  step: TraceStep;
  node: string;
  content: string;
  timestamp: string;
}

export interface SourceRecord {
  title: string;
  url: string;
}

export interface DoneEvent {
  final_answer: string | null;
  sources: SourceRecord[];
}

export type RunStatus = "running" | "done" | "error";

export interface ResearchRun {
  id: string;
  question: string;
  trace: TraceEvent[];
  finalAnswer: string | null;
  sources: SourceRecord[];
  status: RunStatus;
  error?: string;
}
