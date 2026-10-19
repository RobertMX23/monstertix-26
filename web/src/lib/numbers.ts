/* Page numbers versus solution numbers.

   The Load buttons load the codelab's solution folders (`use-solution.sh 8`
   for the workflow), but the workbench numbers its pages without the step it
   leaves out, so the workflow is step 7 here. Everything the page shows says
   the page's number; only the request to the server uses the folder's. */

let pageFor: Record<number, number> = {};

export function setStages(steps: { order: number; stage: number | null }[]) {
  // If two pages share one solution, the first page names it.
  pageFor = {};
  for (const s of steps) if (s.stage != null && !(s.stage in pageFor)) pageFor[s.stage] = s.order;
}

/** The page number a solution step is shown as. */
export function shown(solution: number | null | undefined): number | string {
  if (solution == null) return "";
  return pageFor[solution] ?? solution;
}
