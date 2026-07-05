import type { ResearchRun } from "../types";
import { ReasoningTrace } from "./ReasoningTrace";

const STATUS_META: Record<ResearchRun["status"], { label: string; color: string }> = {
  running: { label: "Thinking…", color: "text-sky-400" },
  done: { label: "Done", color: "text-emerald-400" },
  error: { label: "Error", color: "text-red-400" },
};

export function RunCard({ run }: { run: ResearchRun }) {
  const status = STATUS_META[run.status];

  return (
    <div className="rounded-xl border border-slate-700/60 bg-slate-900/60 p-4 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <h3 className="text-base font-semibold text-slate-100">{run.question}</h3>
        <span className={`shrink-0 text-xs font-medium ${status.color}`}>
          {run.status === "running" && (
            <span className="mr-1 inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-current align-middle" />
          )}
          {status.label}
        </span>
      </div>

      <div className="mt-3">
        <ReasoningTrace trace={run.trace} />
      </div>

      {run.status === "done" && run.finalAnswer && (
        <div className="mt-3 rounded-lg border border-emerald-500/30 bg-emerald-500/5 p-3">
          <p className="text-xs font-medium uppercase tracking-wide text-emerald-400/80">
            Final answer
          </p>
          <p className="mt-1 whitespace-pre-wrap text-sm text-slate-100">{run.finalAnswer}</p>

          {run.sources.length > 0 && (
            <div className="mt-3 border-t border-emerald-500/20 pt-2">
              <p className="text-xs font-medium uppercase tracking-wide text-emerald-400/80">
                Sources
              </p>
              <ul className="mt-1 list-inside list-disc text-sm text-slate-300">
                {run.sources.map((source, i) => (
                  <li key={i}>
                    <a
                      href={source.url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-sky-400 hover:underline"
                    >
                      {source.title}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {run.status === "error" && (
        <div className="mt-3 rounded-lg border border-red-500/30 bg-red-500/5 p-3 text-sm text-red-300">
          {run.error}
        </div>
      )}
    </div>
  );
}
