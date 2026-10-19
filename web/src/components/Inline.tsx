import { Fragment, type ReactNode } from "react";

/* Task text from step.yaml, with the little markdown it uses: `code`,
   **bold** and *italic*. Everything else stays plain text (never HTML), and
   line breaks are kept, so numbered steps written one per line still read as
   a list. */

const TOKEN = /(`[^`]+`|\*\*[^*]+\*\*|\*[^*\s][^*]*\*)/g;

export function Inline({ text }: { text?: string | null }): ReactNode {
  if (!text) return null;
  return text.split(TOKEN).map((part, i) => {
    if (part.startsWith("`") && part.endsWith("`") && part.length > 2) {
      return <code key={i} className="inline-code">{part.slice(1, -1)}</code>;
    }
    if (part.startsWith("**") && part.endsWith("**") && part.length > 4) {
      return <strong key={i}>{part.slice(2, -2)}</strong>;
    }
    if (part.startsWith("*") && part.endsWith("*") && part.length > 2) {
      return <em key={i}>{part.slice(1, -1)}</em>;
    }
    return <Fragment key={i}>{part}</Fragment>;
  });
}
