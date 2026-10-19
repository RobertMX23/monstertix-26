/* One file explorer per page.

   A page shows code with :::code blocks. The first explorer on the page hosts
   all of them: the exercise's own explorer if the page has one, otherwise the
   first :::code block. Every other :::code block is a button that opens its
   file in that explorer, highlights its lines and scrolls to it. */

import { createContext, useCallback, useContext, useRef, useState, type ReactNode } from "react";

export type CodeRef = { path: string; highlight: string; label: string };

type Controller = { show: (ref: CodeRef) => void };

type CodePage = {
  refs: CodeRef[];
  /** The step whose solution folder the code comes from. */
  stage: number | null;
  /** Whether an exercise on this page already has an explorer to host the code. */
  hostedByExercise: boolean;
  register: (controller: Controller) => () => void;
  show: (ref: CodeRef) => void;
  hasHost: boolean;
};

const Ctx = createContext<CodePage | null>(null);

export function CodePageProvider({ refs, stage, hostedByExercise, children }: {
  refs: CodeRef[];
  stage: number | null;
  hostedByExercise: boolean;
  children: ReactNode;
}) {
  const controller = useRef<Controller | null>(null);
  const [hasHost, setHasHost] = useState(false);
  const register = useCallback((next: Controller) => {
    if (controller.current) return () => {};
    controller.current = next;
    setHasHost(true);
    return () => {
      if (controller.current === next) {
        controller.current = null;
        setHasHost(false);
      }
    };
  }, []);
  const show = useCallback((ref: CodeRef) => controller.current?.show(ref), []);
  return (
    <Ctx.Provider value={{ refs, stage, hostedByExercise, register, show, hasHost }}>{children}</Ctx.Provider>
  );
}

export function useCodePage() {
  return useContext(Ctx);
}

/** Every pattern on the page, so the explorer can mark all the files the page talks about. */
export function combined(patterns: (string | undefined)[]): RegExp | null {
  const parts = patterns.filter((p): p is string => !!p);
  if (!parts.length) return null;
  try {
    return new RegExp(parts.map((p) => `(?:${p})`).join("|"));
  } catch {
    return null;
  }
}
