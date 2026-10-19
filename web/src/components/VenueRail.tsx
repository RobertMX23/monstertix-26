import { isUp, useBench } from "../lib/bench";
import { t } from "../i18n";

/* The left column of the story, and of every part that uses the venue: the
   venue panel, live. The venue starts with the workbench and is always on, so
   there is nothing to switch; ‹ folds the panel away and › brings it back.
   Every other process is switched on and off on the card that shows it. */

export function VenueRail() {
  const { service, railOpen, setRailOpen } = useBench();
  const venue = service("venue");

  if (!railOpen) {
    return (
      <div className="flex h-full flex-col items-center gap-3 pt-3">
        <button type="button" className="btn px-1.5" title={t("Show the venue")} onClick={() => setRailOpen(true)}>›</button>
        <span className="dot" title={t("The venue")} style={{ background: isUp(venue) ? "var(--ok)" : "var(--fg-faint)" }} />
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-start gap-2 px-3 pt-4 pb-2">
        <div className="min-w-0 flex-1">
          <div className="kicker" style={{ color: "var(--fg-faint)" }}>{t("The venue")}</div>
          <p className="mt-1 text-[0.72rem] leading-snug" style={{ color: "var(--fg-faint)" }}>
            {t("The ticket seller, live. It is always on.")}
          </p>
        </div>
        <button type="button" className="btn px-1.5" title={t("Hide the venue")} onClick={() => setRailOpen(false)}>‹</button>
      </div>
      {isUp(venue) ? (
        <iframe src="/svc/venue/panel" title={t("Venue panel")} className="block min-h-0 w-full flex-1 border-0"
                style={{ background: "var(--card)" }} />
      ) : (
        <p className="px-3 py-6 text-[0.8rem]" style={{ color: "var(--fg-faint)" }}>
          {venue?.state === "unreachable" ? t("The venue is not answering.") : t("Starting the venue…")}
        </p>
      )}
    </div>
  );
}
