import { useCallback, useState } from "react";
import { parseSSEStream } from "../lib/sse";
import type { DoneEvent, ResearchRun, TraceEvent } from "../types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

type RunPatch = Partial<ResearchRun> | ((run: ResearchRun) => Partial<ResearchRun>);

// Drives one or more research runs against the backend's SSE endpoint.
// Each call to `ask` streams into its own run entry so a user could in
// principle fire multiple questions and watch them progress independently
// (the UI currently disables the input while one is in flight, but the
// hook itself doesn't assume that).
export function useResearchStream() {
  const [runs, setRuns] = useState<ResearchRun[]>([]);
  const [isRunning, setIsRunning] = useState(false);

  const updateRun = useCallback((id: string, patch: RunPatch) => {
    setRuns((prev) =>
      prev.map((run) => {
        if (run.id !== id) return run;
        const delta = typeof patch === "function" ? patch(run) : patch;
        return { ...run, ...delta };
      }),
    );
  }, []);

  const ask = useCallback(
    async (question: string) => {
      const id = crypto.randomUUID();
      const newRun: ResearchRun = {
        id,
        question,
        trace: [],
        finalAnswer: null,
        sources: [],
        status: "running",
      };
      setRuns((prev) => [...prev, newRun]);
      setIsRunning(true);

      try {
        const response = await fetch(`${API_BASE_URL}/api/research`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ question }),
        });

        if (!response.ok) {
          throw new Error(`Request failed: ${response.status} ${response.statusText}`);
        }

        for await (const message of parseSSEStream(response)) {
          if (message.event === "trace") {
            const traceEvent: TraceEvent = JSON.parse(message.data);
            updateRun(id, (run) => ({ trace: [...run.trace, traceEvent] }));
          } else if (message.event === "done") {
            const done: DoneEvent = JSON.parse(message.data);
            updateRun(id, {
              finalAnswer: done.final_answer,
              sources: done.sources,
              status: "done",
            });
          } else if (message.event === "error") {
            const payload = JSON.parse(message.data) as { message?: string };
            updateRun(id, { status: "error", error: payload.message ?? "Unknown error" });
          }
        }
      } catch (err) {
        updateRun(id, {
          status: "error",
          error: err instanceof Error ? err.message : String(err),
        });
      } finally {
        setIsRunning(false);
      }
    },
    [updateRun],
  );

  return { runs, isRunning, ask };
}
