/* Everything the page asks the workbench, and the shapes of the answers. */

export type CheckCard = { id: string; label: string; hint: string; expected: boolean; note: string };
export type CheckResult = {
  id: string;
  passed: boolean;
  expected: boolean;
  command: string;
  detail: string;
};

export type TurnItem = {
  text?: string;
  say?: string;
  in?: PaneTab;
  press?: string;
  venue?: string;
  body?: Record<string, unknown>;
  service?: string;
  action?: "start" | "stop" | "kill" | "restart";
  look?: PaneTab;
  run?: string;
  clock?: { in?: number; every?: number };
  answer?: string;
  /** A venue button that only means something once the agent holds a place in line. */
  needs?: "queue";
};

export type PromptTry = {
  label: string;
  text: string;
  started: number;
  runs: number;
  byYou: number;
  tools: string[];
  orders: number | null;
};

export type Task = {
  kind: "prepare" | "files" | "turn" | "app" | "prompts";
  id: string;
  title?: string;
  explain?: string;
  // prepare
  step?: number;
  resetVenue?: boolean;
  // files
  open?: string;
  start?: string;
  stage?: number;
  compare?: number;
  only?: string[];
  /** Where the files come from; with a `stage`, always that step's solution folder. */
  source?: "solution";
  /** Folders to open all the way down when the explorer loads, e.g. [artifacts/]. */
  expand?: string[];
  highlight?: string;
  highlightLabel?: string;
  editable?: boolean;
  // turn
  items?: TurnItem[];
  // app
  tab?: PaneTab;
  // prompts
  file?: string;
  prompts?: { label: string; text: string }[];
  say?: string;
};

export type Exercise = { title?: string; intro?: string; tasks: Task[]; apps?: PaneTab[] };

export type PartFull = {
  id: string;
  venue: boolean;
  label: string;
  headline: string;
  body: string;
  exercises: Record<string, Exercise>;
  checks: CheckCard[];
  checksTitle: string;
  expect: string[];
};

export type StepCard = {
  slug: string;
  order: number;
  title: string;
  kicker: string;
  minutes: number;
  color: string;
  summary: string;
  venue: boolean;
  stage: number | null;
  parts: { id: string; label: string; headline: string; checkCount: number }[];
};

export type StepFull = Omit<StepCard, "parts"> & { parts: PartFull[] };

export type CoursePayload = {
  course: { title: string; subtitle?: string; credit?: string; tagline?: string };
  steps: StepCard[];
  languages: string[];
  lang: string;
};

export type ServiceState = "running" | "starting" | "stopped" | "external" | "remote" | "unreachable";

export type Service = {
  name: string;
  label: string;
  note: string;
  port: number | null;
  state: ServiceState;
  pid: number | null;
  remote: string;
  url: string;
  command: string;
  last: string;
};

export type Stage = { step: number | null; edited: boolean };

export type PaneTab = "monstertix" | "venue" | "agent";

export type FileNode = { name: string; path: string; kind: "file" | "dir"; children?: FileNode[] };
export type StageChange = { path: string; status: "added" | "changed"; lines: number[] };
export type Job = { state: "idle" | "running" | "done"; code: number | null; command?: string; log: string };

async function get<T>(url: string): Promise<T> {
  const response = await fetch(url, { cache: "no-store" });
  if (!response.ok) throw new Error(`${response.status} ${url}`);
  return response.json();
}

async function post<T>(url: string, body?: unknown): Promise<T> {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!response.ok) throw new Error(`${response.status} ${url}`);
  return response.json();
}

const q = encodeURIComponent;

export const api = {
  course: (lang: string) => get<CoursePayload>(`/api/course?lang=${q(lang)}`),
  step: (slug: string, lang: string) => get<StepFull>(`/api/steps/${q(slug)}?lang=${q(lang)}`),
  check: (slug: string, part: string) =>
    post<{ results: CheckResult[] }>(`/api/check/${q(slug)}?part=${q(part)}`),
  services: () => get<{ services: Service[]; stage: Stage }>("/api/services"),
  service: (name: string, action: string, settings?: Record<string, number>) =>
    post<Service & { detail?: string }>(`/api/services/${q(name)}/${q(action)}`, settings ?? {}),
  serviceLog: (name: string) => get<{ log: string }>(`/api/services/${q(name)}/log`),
  stage: () => get<Stage & { steps: number[] }>("/api/stage"),
  stageChanges: (since: number, to: number) =>
    get<{ files: StageChange[]; removed: string[] }>(`/api/stage/changes?since=${since}&to=${to}`),
  stageLoad: (step: number, resetVenue: boolean) =>
    post<Stage & { ok: boolean; output: string }>("/api/stage", { step, resetVenue }),
  venueState: () => get<{ up: boolean; queue: number; orders: number }>("/api/venue/state"),
  venue: (action: string, body?: Record<string, unknown>) =>
    post<{ ok: boolean; error?: string }>(`/api/venue/${q(action)}`, body ?? {}),
  jobStart: (slug: string, task: string, index: number) =>
    post<Job>(`/api/jobs/${q(slug)}/${q(task)}/${index}`),
  job: (slug: string, task: string, index: number) => get<Job>(`/api/jobs/${q(slug)}/${q(task)}/${index}`),
  /** With `stage`, the step's code as its solution folder ships it, not what is on disk. */
  fileTree: (start: string, stage?: number) =>
    get<{ root: string; entries: FileNode[] }>(`/api/files/tree?start=${q(start)}&depth=12${stage != null ? `&stage=${stage}` : ""}`),
  fileRead: (path: string, stage?: number) =>
    get<{ path: string; lines?: string[]; error?: string }>(`/api/files/read?path=${q(path)}${stage != null ? `&stage=${stage}` : ""}`),
  promptLab: (slug: string, task: string) =>
    get<{ text: string; using: boolean; error?: string; tries: PromptTry[] }>(`/api/prompts/${q(slug)}/${q(task)}`),
  promptSwap: (slug: string, task: string, text: string, label: string) =>
    post<{ ok: boolean; error?: string }>(`/api/prompts/${q(slug)}/${q(task)}`, { text, label }),
  promptRestore: (slug: string, task: string) => post<{ ok: boolean }>(`/api/prompts/${q(slug)}/${q(task)}/restore`),
  terminal: (slug: string, command: string) =>
    post<{ code: number; output: string }>(`/api/terminal/${q(slug)}`, { command }),
  env: () => get<{ project: string; model: string; venue: string; remoteVenue: boolean }>("/api/env"),
};
