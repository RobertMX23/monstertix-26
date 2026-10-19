import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from "react";

import type { PaneTab } from "../lib/api";
import { ServiceControls, ServiceLog } from "./ServiceControls";
import { isUp, useBench } from "../lib/bench";
import { t } from "../i18n";

/* The real apps, framed in the reading where a step needs them: under the
   "Your turn" card whose actions use them. Each app is a separate process
   reached through the workbench at /svc/<name>/, so the frame is same-origin
   and only one port has to be open.

   A frame is kept once opened, so switching tabs does not lose a
   conversation, and it reloads when its process comes back. The ADK web UI
   reopens the session that was going, the way a student would pick it from
   the session list after a restart. The box can be dragged taller at its
   bottom-right corner.

   The process behind each app is switched on and off at the card's top right,
   next to its log. */

export const APPS: Record<PaneTab, { label: string; path: string; service: string }> = {
  agent: { label: "ADK web UI", path: "/svc/agent/dev-ui/?app=concert", service: "agent" },
  venue: { label: "Venue panel", path: "/svc/venue/panel", service: "venue" },
  monstertix: { label: "MonsterTix", path: "/svc/monstertix/", service: "monstertix" },
};

/* Lets a "Your turn" item bring its app forward: the copy button on a message
   for the agent opens the ADK web UI tab under the card and scrolls to it. */
type Listener = (tab: PaneTab) => void;
type Dock = { focus: Listener; subscribe: (fn: Listener) => () => void };
const DockContext = createContext<Dock | null>(null);
export const useDock = () => useContext(DockContext);

export function DockProvider({ children }: { children: ReactNode }) {
  const listeners = useRef(new Set<Listener>());
  const [dock] = useState<Dock>(() => ({
    focus: (tab) => {
      // A card with no app of its own (apps: []) uses the one an earlier card on the page frames.
      if (listeners.current.size) listeners.current.forEach((fn) => fn(tab));
      else document.querySelector(".app-dock")?.scrollIntoView({ block: "start" });
    },
    subscribe: (fn) => {
      listeners.current.add(fn);
      return () => {
        listeners.current.delete(fn);
      };
    },
  }));
  return <DockContext.Provider value={dock}>{children}</DockContext.Provider>;
}

export function AppDock({ tabs }: { tabs: PaneTab[] }) {
  const { service, services } = useBench();
  const [tab, setTab] = useState<PaneTab>(tabs[0]);
  const [opened, setOpened] = useState<Set<PaneTab>>(new Set([tabs[0]]));
  const [versions, setVersions] = useState<Record<string, number>>({});
  const [logOpen, setLogOpen] = useState(false);
  const box = useRef<HTMLDivElement>(null);
  const frames = useRef<Record<string, HTMLIFrameElement | null>>({});
  const where = useRef<Record<string, string>>({});
  const wasUp = useRef<Record<string, boolean>>({});

  const show = useCallback((next: PaneTab) => {
    if (!tabs.includes(next)) return;
    setTab(next);
    setOpened((prev) => (prev.has(next) ? prev : new Set(prev).add(next)));
    box.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [tabs]);
  const dock = useDock();
  useEffect(() => dock?.subscribe(show), [dock, show]);

  // Remember where each frame had got to (the dev UI keeps its session in the URL).
  useEffect(() => {
    const timer = setInterval(() => {
      for (const [id, frame] of Object.entries(frames.current)) {
        try {
          const url = frame?.contentWindow?.location;
          if (url && url.pathname.startsWith("/svc/")) where.current[id] = url.pathname + url.search + url.hash;
        } catch {
          /* not loaded yet */
        }
      }
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  // A process that comes back (restarted, or started after a kill) gets a fresh frame.
  useEffect(() => {
    for (const id of tabs) {
      const name = APPS[id].service;
      const up = isUp(services.find((s) => s.name === name));
      if (wasUp.current[name] === false && up) {
        const reload = () => setVersions((v) => ({ ...v, [id]: (v[id] ?? 0) + 1 }));
        if (id === "agent") {
          fetch("/svc/agent/apps/concert/users/user/sessions")
            .then((r) => r.json())
            .then((sessions: { id: string; lastUpdateTime?: number }[]) => {
              const latest = [...sessions].sort((a, b) => (b.lastUpdateTime ?? 0) - (a.lastUpdateTime ?? 0))[0];
              if (latest) where.current.agent = `${APPS.agent.path}&session=${encodeURIComponent(latest.id)}`;
            })
            .catch(() => {})
            .finally(reload);
        } else {
          reload();
        }
      }
      wasUp.current[name] = up;
    }
  }, [services, tabs]);

  const app = APPS[tab];
  const svc = service(app.service);
  const up = isUp(svc);

  return (
    <div ref={box} className="app-dock my-6 overflow-hidden rounded-2xl border"
         style={{ borderColor: "var(--hairline-strong)", background: "var(--card)" }}>
      <div className="flex items-center gap-1 border-b px-2 py-1.5" style={{ borderColor: "var(--hairline)" }}>
        {tabs.map((id) => {
          const active = id === tab;
          return (
            <button key={id} type="button" onClick={() => show(id)}
                    className="flex items-center gap-1.5 rounded-md px-2.5 py-1 text-[0.78rem]"
                    style={{ background: active ? "var(--overlay)" : "transparent",
                             color: active ? "var(--fg)" : "var(--fg-muted)", fontWeight: active ? 600 : 400 }}>
              <span className="dot" style={{ width: 6, height: 6,
                    background: isUp(service(APPS[id].service)) ? "var(--ok)" : "var(--fg-faint)" }} />
              {t(APPS[id].label)}
            </button>
          );
        })}
        <div className="ml-auto flex flex-wrap items-center justify-end gap-1.5">
          {up && (
            <>
              <button type="button" className="btn" title={t("Reload")}
                      onClick={() => setVersions((v) => ({ ...v, [tab]: (v[tab] ?? 0) + 1 }))}>↻</button>
              <a className="btn" href={where.current[tab] ?? app.path} target="_blank" rel="noreferrer"
                 title={t("Open in a new tab")}>↗</a>
            </>
          )}
          <ServiceControls name={app.service} log={logOpen} onLog={setLogOpen} />
        </div>
      </div>

      {logOpen && (
        <div className="border-b px-3 py-2" style={{ borderColor: "var(--hairline)" }}>
          <ServiceLog name={app.service} command={svc?.command} />
        </div>
      )}

      <div className="app-dock__body relative">
        {tabs.map((id) =>
          opened.has(id) && isUp(service(APPS[id].service)) ? (
            <iframe
              key={`${id}-${versions[id] ?? 0}`}
              ref={(el) => {
                frames.current[id] = el;
              }}
              src={where.current[id] ?? APPS[id].path}
              title={APPS[id].label}
              hidden={id !== tab}
              allow="autoplay; clipboard-write"
              className="block h-full w-full border-0"
              style={{ background: "var(--card)" }}
            />
          ) : null,
        )}
        {!up && (
          <div className="grid h-full place-content-center gap-3 px-8 text-center" style={{ color: "var(--fg-faint)" }}>
            <p className="text-sm">
              {svc?.state === "unreachable"
                ? t("{name} is not answering.", { name: t(app.label) })
                : svc?.last === "killed with SIGKILL"
                  ? t("{name} was killed. Nothing is answering on its port.", { name: svc.label })
                  : t("{name} is not running.", { name: svc?.label ?? t(app.label) })}
            </p>
            {svc?.state === "stopped" && (
              <p className="text-[0.8rem]">{t("Turn it on with the switch at the top right.")}</p>
            )}
            {svc && <p className="font-mono text-[0.68rem]">$ {svc.command}</p>}
          </div>
        )}
      </div>
    </div>
  );
}
