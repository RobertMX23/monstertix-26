import { useRef, useState } from "react";

import { api } from "../lib/api";
import { t } from "../i18n";

/* Commands from the reading, typed in and ready, one after another: Enter (or
   Run) executes the one on the prompt on this machine, from the workshop
   folder, shows its real output, and puts the next one on the prompt. Only
   commands written in the step's own :::terminal blocks run. */

type Run = { command: string; output: string; code: number };

export function Terminal({ slug, commands }: { slug: string; commands: string[] }) {
  const [runs, setRuns] = useState<Run[]>([]);
  const [busy, setBusy] = useState(false);
  const input = useRef<HTMLButtonElement>(null);
  // The next command not yet run; after the last, the last again.
  const command = commands[Math.min(runs.length, commands.length - 1)] ?? "";

  async function run() {
    if (busy) return;
    setBusy(true);
    try {
      const result = await api.terminal(slug, command);
      setRuns((previous) => [...previous, { command, ...result }]);
    } catch {
      setRuns((previous) => [...previous, { command, output: t("The workbench did not answer."), code: 1 }]);
    } finally {
      setBusy(false);
      input.current?.focus();
    }
  }

  const prompt = (
    <span style={{ color: "#7ee787" }}>~/monstertix</span>
  );

  return (
    <div className="my-5 overflow-hidden rounded-2xl border" style={{ borderColor: "var(--hairline-strong)", background: "#0d1117" }}>
      <div className="flex items-center gap-2 border-b px-3 py-1.5" style={{ borderColor: "rgba(255,255,255,0.08)" }}>
        <span className="h-2.5 w-2.5 rounded-full" style={{ background: "#ff5f57" }} />
        <span className="h-2.5 w-2.5 rounded-full" style={{ background: "#febc2e" }} />
        <span className="h-2.5 w-2.5 rounded-full" style={{ background: "#28c840" }} />
        <span className="ml-2 font-mono text-[0.68rem]" style={{ color: "#8b949e" }}>{t("terminal")}</span>
        <button type="button" className="btn ml-auto px-2 py-0.5" disabled={busy} onClick={run}
                style={{ color: "#e6edf3", borderColor: "rgba(255,255,255,0.18)" }}>
          {busy ? t("Running…") : t("Run")} ⏎
        </button>
      </div>
      <div className="quiet-scroll max-h-96 overflow-auto px-4 py-3 font-mono text-[0.78rem] leading-relaxed" style={{ color: "#e6edf3" }}>
        {runs.map((done, index) => (
          <div key={index} className="mb-2">
            <div className="whitespace-pre-wrap">{prompt} <span style={{ color: "#8b949e" }}>$</span> {done.command}</div>
            {done.output ? (
              <pre className="m-0 whitespace-pre-wrap" style={{ color: done.code === 0 ? "#e6edf3" : "#ffa198" }}>{done.output}</pre>
            ) : (
              // A command that matched nothing prints nothing; say so, or it looks like Enter did nothing.
              <div style={{ color: "#8b949e" }}>{done.code === 0 ? t("(no output)") : t("(exited with code {code}, no output)", { code: done.code })}</div>
            )}
          </div>
        ))}
        {/* The command line, ready: focus it and press Enter. */}
        <button
          ref={input}
          type="button"
          onClick={run}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              event.preventDefault();
              run();
            }
          }}
          className="block w-full cursor-text whitespace-pre-wrap text-left outline-none"
          title={t("Press Enter to run")}
        >
          {prompt} <span style={{ color: "#8b949e" }}>$</span> {command}
          <span className={busy ? "" : "terminal-caret"} aria-hidden>▍</span>
        </button>
      </div>
    </div>
  );
}
