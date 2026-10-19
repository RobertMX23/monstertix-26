import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { api, type FileNode, type StageChange, type Task } from "../lib/api";
import { useBench } from "../lib/bench";
import { combined, useCodePage, type CodeRef } from "../lib/code";
import { shown } from "../lib/numbers";
import { t } from "../i18n";
import { Inline } from "./Inline";
import { StageBar } from "./StageBar";

/* The code as it is on disk right now, read-only.

   Two layers of marking, kept apart on purpose:

     what changed    files this step adds (NEW) or edits (CHANGED), compared
                     with the step before; changed lines get a bar in the margin
     what to look at a pattern from the step (`highlight`) tints the lines that
                     carry the idea, with one sentence (`highlightLabel`) on why

   The first says where to look; the second says what to look for. */

function Chevron({ open }: { open: boolean }) {
  return (
    <span className="inline-block w-3 text-[9px] transition-transform"
          style={{ color: "var(--fg-faint)", transform: open ? "rotate(90deg)" : "none" }}>
      ▶
    </span>
  );
}

function Row({ node, depth, openDirs, toggle, selected, select, marks, hits }: {
  node: FileNode;
  depth: number;
  openDirs: Set<string>;
  toggle: (path: string) => void;
  selected: string;
  select: (path: string) => void;
  marks: Record<string, StageChange>;
  hits: Set<string>;
}) {
  const isOpen = openDirs.has(node.path);
  const mark = marks[node.path];
  const holds = node.kind === "dir" && Object.keys(marks).some((p) => p.startsWith(node.path + "/"));
  return (
    <>
      <button
        type="button"
        onClick={() => (node.kind === "dir" ? toggle(node.path) : select(node.path))}
        className="flex w-full items-center gap-1.5 rounded-md px-2 py-[3px] text-left font-mono text-[0.74rem]"
        style={{
          paddingLeft: 8 + depth * 13,
          background: node.path === selected ? "var(--overlay)" : "transparent",
          color: mark ? "var(--accent)" : node.path === selected ? "var(--fg)" : "var(--fg-muted)",
        }}
      >
        {node.kind === "dir" ? <Chevron open={isOpen} /> : <span className="w-3" />}
        <span className="truncate" style={{ fontWeight: mark ? 600 : 400 }}>
          {node.name}
          {node.kind === "dir" ? "/" : ""}
        </span>
        {hits.has(node.path) && (
          <span className="h-1.5 w-1.5 shrink-0 rounded-sm" title={t("has highlighted lines")}
                style={{ background: "var(--lime)" }} />
        )}
        {mark && (
          <span className="ml-auto shrink-0 rounded px-1 font-sans text-[0.58rem] font-semibold uppercase tracking-wide"
                style={{ color: "var(--accent)", background: "color-mix(in srgb, var(--accent) 14%, transparent)" }}>
            {mark.status === "added" ? t("new") : t("changed")}
          </span>
        )}
        {holds && !isOpen && (
          <span className="ml-auto h-1.5 w-1.5 shrink-0 rounded-full" style={{ background: "var(--accent)" }} />
        )}
      </button>
      {node.kind === "dir" && isOpen &&
        (node.children ?? []).map((child) => (
          <Row key={child.path} node={child} depth={depth + 1} openDirs={openDirs} toggle={toggle}
               selected={selected} select={select} marks={marks} hits={hits} />
        ))}
    </>
  );
}

function prune(nodes: FileNode[], only: string[]): FileNode[] {
  const kept: FileNode[] = [];
  for (const node of nodes) {
    if (node.kind === "file") {
      if (only.some((e) => (e.endsWith("/") ? node.path.startsWith(e) : node.path === e))) kept.push(node);
    } else {
      const children = prune(node.children ?? [], only);
      if (children.length) kept.push({ ...node, children });
    }
  }
  return kept;
}

function ancestors(path: string): string[] {
  const parts = path.split("/").slice(0, -1);
  return parts.map((_, i) => parts.slice(0, i + 1).join("/"));
}

export function FileExplorer({ task, color, stageBar = true }: { task: Task; color: string; stageBar?: boolean }) {
  const { epoch, stage } = useBench();
  const [entries, setEntries] = useState<FileNode[]>([]);
  const [openDirs, setOpenDirs] = useState<Set<string>>(new Set());
  const [selected, setSelected] = useState("");
  const [lines, setLines] = useState<string[] | null>(null);
  const [problem, setProblem] = useState("");
  const [marks, setMarks] = useState<Record<string, StageChange>>({});
  const [hits, setHits] = useState<Set<string>>(new Set());
  const [reloads, setReloads] = useState(0);   // ↻: files appear while you work (artifacts/)
  const code = useRef<HTMLDivElement>(null);
  const box = useRef<HTMLDivElement>(null);
  const only = task.only?.length ? task.only : ["agent/", "monstertix/"];
  const loaded = stage?.step ?? null;
  // A step's explorer shows that step's code from its solution folder, whatever is
  // loaded in agent/ right now. Without a stage (memory/, artifacts/) it reads the disk.
  const from = task.stage;

  // The page's code blocks, all shown in this one explorer (lib/code.tsx).
  const page = useCodePage();
  const [active, setActive] = useState<CodeRef | null>(null);
  const pageRefs = page?.refs ?? [];

  // Every highlight on the page tints its lines; the one just asked for is where it scrolls.
  const pattern = useMemo(() => combined([task.highlight, ...pageRefs.map((r) => r.highlight)]),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [task.highlight, pageRefs.length]);
  const focus = useMemo(() => (active ? combined([active.highlight]) : pattern), [active, pattern]);
  const legend = active?.label || task.highlightLabel;

  useEffect(() => {
    if (task.compare === undefined || task.stage === undefined) return;
    api.stageChanges(task.compare, task.stage).then((payload) => {
      const relevant = payload.files.filter((f) => only.some((e) => (e.endsWith("/") ? f.path.startsWith(e) : f.path === e)));
      setMarks(Object.fromEntries(relevant.map((c) => [c.path, c])));
      setOpenDirs((prev) => {
        const next = new Set(prev);
        relevant.forEach((c) => ancestors(c.path).forEach((a) => next.add(a)));
        return next;
      });
    }).catch(() => setMarks({}));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [task.compare, task.stage]);

  useEffect(() => {
    api.fileTree(task.start ?? "", from).then((payload) => {
      const kept = prune(payload.entries, only);
      setEntries(kept);
      if (task.open) setOpenDirs((prev) => new Set([...prev, ...ancestors(task.open!)]));
      if (task.expand?.length) {
        // Open every folder under these, so a file saved deep inside shows at once.
        const dirs: string[] = [];
        const walkDirs = (nodes: FileNode[]) => nodes.forEach((n) => {
          if (n.kind === "dir") {
            if (task.expand!.some((e) => (n.path + "/").startsWith(e))) dirs.push(n.path);
            walkDirs(n.children ?? []);
          }
        });
        walkDirs(kept);
        setOpenDirs((prev) => new Set([...prev, ...dirs]));
      }
      // Which files hold highlighted lines: read the marked ones and the one shown first.
      if (pattern) {
        const files: string[] = [];
        const walk = (nodes: FileNode[]) => nodes.forEach((n) => (n.kind === "file" ? files.push(n.path) : walk(n.children ?? [])));
        walk(kept);
        Promise.all(files.filter((f) => f.endsWith(".py") || f.endsWith(".html")).map((f) =>
          api.fileRead(f, from).then((r) => ((r.lines ?? []).some((l) => pattern.test(l)) ? f : "")).catch(() => ""),
        )).then((found) => setHits(new Set(found.filter(Boolean))));
      }
    }).catch(() => setProblem(t("could not read the project")));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [task.start, task.open, epoch, loaded, reloads]);

  const show = useCallback(async (path: string) => {
    setSelected(path);
    setProblem("");
    try {
      const file = await api.fileRead(path, from);
      if (file.error) {
        setLines(null);
        setProblem(file.error);
        return;
      }
      setLines(file.lines ?? []);
    } catch {
      setProblem(t("could not read that file"));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [from]);

  // Host the page's code: a button elsewhere on the page opens its file here.
  useEffect(() => {
    // Only an explorer of a step's code hosts the page's code (not memory/ or artifacts/).
    if (!page || task.stage == null) return;
    return page.register({
      show: (ref) => {
        setActive(ref);
        setOpenDirs((prev) => new Set([...prev, ...ancestors(ref.path)]));
        show(ref.path);
        // Up to the explorer, clear of the sticky header.
        const el = box.current;
        if (el) {
          const nav = parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--nav-height")) || 112;
          window.scrollTo({ top: el.getBoundingClientRect().top + window.scrollY - nav - 16 });
        }
      },
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, show]);

  useEffect(() => {
    const target = selected || task.open;
    if (target) show(target);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [task.open, epoch, loaded, reloads]);

  // Bring the first highlighted line into view, inside the pane only.
  useEffect(() => {
    if (!lines || !code.current) return;
    const first = lines.findIndex((l) => focus?.test(l));
    const changed = marks[selected]?.lines[0];
    const target = first >= 0 ? first : changed !== undefined ? changed - 1 : -1;
    if (target < 0) {
      code.current.scrollTop = 0;
      return;
    }
    const row = code.current.querySelector<HTMLElement>(`[data-line="${target}"]`);
    if (row) code.current.scrollTop = Math.max(0, row.offsetTop - 60);
  }, [lines, selected, focus, marks]);

  const changedLines = new Set(marks[selected]?.lines ?? []);
  const anyMarks = Object.keys(marks).length > 0;

  return (
    <div ref={box} className="mt-3">
      {task.explain && (
        <p className="mb-3 text-sm" style={{ color: "var(--fg-muted)" }}>
          <Inline text={task.explain} />
        </p>
      )}

      {stageBar && task.stage !== undefined && <StageBar step={task.stage} color={color} />}

      <div className="overflow-hidden rounded-2xl border" style={{ borderColor: "var(--hairline)", background: "var(--card)" }}>
        <div className="flex items-center gap-3 border-b px-4 py-2" style={{ borderColor: "var(--hairline)" }}>
          <span className="kicker" style={{ color: "var(--fg-faint)" }}>{t("Files")}</span>
          <span className="truncate font-mono text-[0.72rem]" style={{ color: "var(--fg)" }}>
            {selected || t("select a file")}
          </span>
          <span className="ml-auto shrink-0 text-[0.66rem]" style={{ color: "var(--fg-faint)" }}>{t("read only")}</span>
          <button type="button" className="btn px-1.5 py-0" title={t("Read the files again")}
                  onClick={() => setReloads((n) => n + 1)}>↻</button>
        </div>

        {(anyMarks || legend) && (
          <div className="flex flex-col gap-1 border-b px-4 py-2 text-[0.74rem]" style={{ borderColor: "var(--hairline)", color: "var(--fg-muted)" }}>
            {anyMarks && (
              <span>
                <span className="mr-1.5 inline-block h-2.5 w-[3px] align-middle" style={{ background: "var(--accent)" }} />
                {t("Compared with step {n}: NEW files, and changed lines marked in the margin.", { n: shown(task.compare) })}
              </span>
            )}
            {legend && (
              <span>
                <span className="mr-1.5 inline-block h-2.5 w-2.5 rounded-sm align-middle"
                      style={{ background: "color-mix(in srgb, var(--lime) 28%, transparent)" }} />
                <Inline text={legend} />
              </span>
            )}
          </div>
        )}

        <div className="grid" style={{ gridTemplateColumns: "minmax(9rem, 12.5rem) minmax(0, 1fr)" }}>
          <div className="quiet-scroll overflow-auto border-r py-2" style={{ borderColor: "var(--hairline)", maxHeight: 620 }}>
            {entries.map((node) => (
              <Row key={node.path} node={node} depth={0} openDirs={openDirs}
                   toggle={(p) => setOpenDirs((prev) => {
                     const next = new Set(prev);
                     if (next.has(p)) next.delete(p); else next.add(p);
                     return next;
                   })}
                   selected={selected} select={show} marks={marks} hits={hits} />
            ))}
          </div>

          <div ref={code} className="quiet-scroll relative overflow-auto" style={{ maxHeight: 620, background: "var(--viewer-bg)" }}>
            {problem ? (
              <p className="p-4 text-sm" style={{ color: "var(--fg-muted)" }}>
                {marks[selected]?.status === "added"
                  ? t("This file arrives with step {n}. Load it above to read it here.", { n: shown(task.stage) })
                  : problem}
              </p>
            ) : lines ? (
              <pre className="m-0 py-2 font-mono text-[0.72rem] leading-[1.6]">
                {marks[selected]?.status === "added" && (
                  <div className="mx-3 mb-2 rounded-md px-2 py-1 font-sans text-[0.72rem]"
                       style={{ color: "var(--accent)", background: "color-mix(in srgb, var(--accent) 12%, transparent)" }}>
                    {t("New in this step.")}
                  </div>
                )}
                {lines.map((line, index) => {
                  const changed = changedLines.has(index + 1);
                  const picked = pattern?.test(line) ?? false;
                  return (
                    <div
                      key={index}
                      data-line={index}
                      className="flex pr-3"
                      style={{
                        background: picked ? "color-mix(in srgb, var(--lime) 18%, transparent)" : undefined,
                        boxShadow: changed ? "inset 3px 0 0 var(--accent)" : undefined,
                      }}
                    >
                      <span className="w-10 shrink-0 pr-3 text-right select-none"
                            style={{ color: changed ? "var(--accent)" : "var(--fg-faint)", opacity: changed ? 0.95 : 0.55 }}>
                        {index + 1}
                      </span>
                      <span style={{ color: "var(--viewer-fg)", whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
                        {line || " "}
                      </span>
                    </div>
                  );
                })}
              </pre>
            ) : (
              <p className="p-4 font-mono text-[0.75rem]" style={{ color: "var(--fg-faint)" }}>
                {t("Pick a file on the left.")}
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
