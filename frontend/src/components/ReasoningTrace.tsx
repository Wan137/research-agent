import type { TraceEvent, TraceStep } from "../types";

const STEP_META: Record<TraceStep, { label: string; icon: string; color: string }> = {
  planning: { label: "Planning", icon: "\u{1F9ED}", color: "border-sky-500/40 bg-sky-500/10 text-sky-300" },
  routing: { label: "Routing", icon: "\u{1F500}", color: "border-violet-500/40 bg-violet-500/10 text-violet-300" },
  tool_call: { label: "Tool call", icon: "\u{1F527}", color: "border-amber-500/40 bg-amber-500/10 text-amber-300" },
  tool_result: { label: "Tool result", icon: "\u{1F4C4}", color: "border-amber-500/40 bg-amber-500/10 text-amber-200" },
  critique: { label: "Self-critique", icon: "\u{1F9D0}", color: "border-fuchsia-500/40 bg-fuchsia-500/10 text-fuchsia-300" },
  final: { label: "Final answer", icon: "✅", color: "border-emerald-500/40 bg-emerald-500/10 text-emerald-300" },
  error: { label: "Error", icon: "⚠️", color: "border-red-500/40 bg-red-500/10 text-red-300" },
};

function formatTime(iso: string): string {
  try {
    return new Date(iso).toLocaleTimeString([], { hour12: false });
  } catch {
    return "";
  }
}

export function ReasoningTrace({ trace }: { trace: TraceEvent[] }) {
  if (trace.length === 0) return null;

  return (
    <ol className="flex flex-col gap-2">
      {trace.map((event, i) => {
        const meta = STEP_META[event.step] ?? STEP_META.planning;
        return (
          <li
            key={i}
            className={`rounded-lg border px-3 py-2 text-sm ${meta.color}`}
          >
            <div className="flex items-center justify-between gap-2">
              <span className="font-medium">
                <span className="mr-1.5">{meta.icon}</span>
                Step {i + 1}: {meta.label}
                <span className="ml-2 text-xs opacity-60">({event.node})</span>
              </span>
              <span className="shrink-0 text-xs opacity-50">{formatTime(event.timestamp)}</span>
            </div>
            <p className="mt-1 whitespace-pre-wrap text-slate-200/90">{event.content}</p>
          </li>
        );
      })}
    </ol>
  );
}
