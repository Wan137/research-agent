import { useState } from "react";
import type { FormEvent } from "react";
import { useResearchStream } from "./hooks/useResearchStream";
import { RunCard } from "./components/RunCard";

function App() {
  const { runs, isRunning, ask } = useResearchStream();
  const [question, setQuestion] = useState("");

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const trimmed = question.trim();
    if (!trimmed || isRunning) return;
    ask(trimmed);
    setQuestion("");
  };

  return (
    <div className="h-screen overflow-hidden bg-slate-950 text-slate-100">
      <div className="mx-auto flex h-full max-w-3xl flex-col px-4 py-8">
        <header className="mb-6 shrink-0">
          <h1 className="text-2xl font-bold">Research Agent</h1>
          <p className="mt-1 text-sm text-slate-400">
            Ask a complex question and watch the agent plan, act, and verify its own answer.
          </p>
        </header>

        <main className="flex flex-1 flex-col gap-4 overflow-y-auto pb-4">
          {runs.length === 0 && (
            <p className="text-sm text-slate-500">No questions yet — ask one below to get started.</p>
          )}
          {runs.map((run) => (
            <RunCard key={run.id} run={run} />
          ))}
        </main>

        <form onSubmit={handleSubmit} className="flex shrink-0 gap-2 bg-slate-950 pt-2">
          <input
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Ask a research question…"
            disabled={isRunning}
            className="flex-1 rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500 focus:border-sky-500 focus:outline-none disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={isRunning || !question.trim()}
            className="rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium text-white hover:bg-sky-500 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isRunning ? "Thinking…" : "Ask"}
          </button>
        </form>
      </div>
    </div>
  );
}

export default App;
