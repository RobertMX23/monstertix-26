/* What every part of the bench shares: the services and which step is loaded
   (polled from the server, never stored here), and whether the services
   column is open. */

import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from "react";

import { api, type Service, type Stage } from "./api";

type Bench = {
  services: Service[];
  stage: Stage | null;
  refresh: () => Promise<void>;
  service: (name: string) => Service | undefined;
  railOpen: boolean;
  setRailOpen: (open: boolean) => void;
  /** The page shows the venue panel in a left column, so it is not repeated under a card. */
  venueOnLeft: boolean;
  setVenueOnLeft: (on: boolean) => void;
  /** Bumped when something reloads code or restarts a process, so frames and files re-read. */
  epoch: number;
  bump: () => void;
};

const BenchContext = createContext<Bench | null>(null);

function stored<T extends string>(key: string, fallback: T): T {
  try {
    return (localStorage.getItem(key) as T) || fallback;
  } catch {
    return fallback;
  }
}

function store(key: string, value: string) {
  try {
    localStorage.setItem(key, value);
  } catch {
    /* the page works without it */
  }
}

export function BenchProvider({ children }: { children: ReactNode }) {
  const [services, setServices] = useState<Service[]>([]);
  const [stage, setStage] = useState<Stage | null>(null);
  const [railOpen, setRailOpenState] = useState(() => stored("monstertix.rail", "open") === "open");
  const [epoch, setEpoch] = useState(0);
  const [venueOnLeft, setVenueOnLeft] = useState(false);
  const inFlight = useRef(false);

  const refresh = useCallback(async () => {
    if (inFlight.current) return;
    inFlight.current = true;
    try {
      const payload = await api.services();
      setServices(payload.services);
      setStage(payload.stage);
    } catch {
      /* the workbench restarting: keep the last picture */
    } finally {
      inFlight.current = false;
    }
  }, []);

  useEffect(() => {
    refresh();
    const timer = setInterval(() => {
      if (document.visibilityState === "visible") refresh();
    }, 2500);
    return () => clearInterval(timer);
  }, [refresh]);

  const setRailOpen = useCallback((open: boolean) => {
    setRailOpenState(open);
    store("monstertix.rail", open ? "open" : "closed");
  }, []);

  const value: Bench = {
    services,
    stage,
    refresh,
    service: (name) => services.find((s) => s.name === name),
    railOpen,
    setRailOpen,
    venueOnLeft,
    setVenueOnLeft,
    epoch,
    bump: () => setEpoch((n) => n + 1),
  };
  return <BenchContext.Provider value={value}>{children}</BenchContext.Provider>;
}

export function useBench(): Bench {
  const bench = useContext(BenchContext);
  if (!bench) throw new Error("useBench outside BenchProvider");
  return bench;
}

export function isUp(service?: Service) {
  return !!service && ["running", "external", "remote"].includes(service.state);
}
