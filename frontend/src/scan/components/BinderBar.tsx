import { useQuery } from "@tanstack/react-query";

import { api, sessionPollInterval } from "../api";
import type { SessionScan } from "../types";

const SLOTS = [1, 2, 3, 4, 5, 6, 7, 8, 9];

function slotState(s: SessionScan | undefined): { label: string; tone: string } {
  if (!s) return { label: "", tone: "" };
  if (s.status === "pending" || s.status === "processing") return { label: "…", tone: "busy" };
  if (s.status === "failed") return { label: "Error", tone: "error" };
  if (!s.card_detected && !s.card_number) return { label: "Empty", tone: "muted" };
  if (s.dismissed) return { label: "Empty", tone: "muted" };
  const pct = s.confidence == null ? "" : ` ${Math.round(s.confidence * 100)}%`;
  return { label: `${s.card_number ?? "?"}${pct}`, tone: s.added_to_collection ? "ok" : "warn" };
}

interface Props {
  sessionId: number;
  page: number;
  /** Casilla a capturar (null: página terminada). */
  slot: number | null;
  /** Casillas marcadas como hueco vacío en esta página. */
  skipped: Set<number>;
  sending: boolean;
  onSelect: (slot: number) => void;
  onCapture: () => void;
  onSkip: () => void;
  onPage: (page: number) => void;
  onStop: () => void;
}

/** Sesión de archivador: la página en 3×3, la casilla actual y los controles. */
export default function BinderBar({ sessionId, page, slot, skipped, sending, onSelect, onCapture, onSkip, onPage, onStop }: Props) {
  const session = useQuery({
    queryKey: ["session", sessionId],
    queryFn: () => api.getSession(sessionId),
    refetchInterval: (query) => sessionPollInterval(query.state.data),
  });
  // Última captura de cada casilla de esta página (las repetidas quedan descartadas).
  const bySlot = new Map<number, SessionScan>();
  for (const s of [...(session.data?.scans ?? [])].reverse()) {
    if (s.binder_page === page && s.binder_slot != null && !(s.dismissed && s.card_detected)) bySlot.set(s.binder_slot, s);
  }
  const row = slot == null ? null : Math.ceil(slot / 3);
  const col = slot == null ? null : ((slot - 1) % 3) + 1;

  return (
    <div className="binder-bar">
      <div className="binder-head">
        <span className="binder-page">
          <button className="secondary" onClick={() => onPage(page - 1)} disabled={page <= 1} aria-label="Previous page">
            ‹
          </button>
          <strong>Page {page}</strong>
          <button className="secondary" onClick={() => onPage(page + 1)} aria-label="Next page">
            ›
          </button>
        </span>
        <span className="muted small">
          Destination: <strong>{session.data?.location_name ?? "…"}</strong>
        </span>
      </div>

      <div className="binder-grid" role="grid" aria-label={`Page ${page}`}>
        {SLOTS.map((n) => {
          const st = skipped.has(n) && !bySlot.has(n) ? { label: "Gap", tone: "muted" } : slotState(bySlot.get(n));
          return (
            <button
              key={n}
              className={`binder-slot ${st.tone} ${n === slot ? "current" : ""}`}
              onClick={() => onSelect(n)}
              title={n === slot ? "Current slot" : "Capture (or redo) this slot"}
            >
              <small>{n}</small>
              <span>{st.label}</span>
            </button>
          );
        })}
      </div>

      {slot != null ? (
        <p className="binder-hint">
          Move the camera close to the card in <strong>row {row}, column {col}</strong> until it fills the frame. If there's
          glare, tilt the phone a little.
        </p>
      ) : (
        <p className="binder-hint">
          Page {page} done. Check the cards on the right and move on to the next one.
        </p>
      )}

      <div className="actions">
        {slot != null ? (
          <>
            <button onClick={onCapture} disabled={sending}>
              {sending ? "Sending…" : `Capture slot ${slot}`}
            </button>
            <button className="secondary" onClick={onSkip} disabled={sending}>
              Empty slot
            </button>
          </>
        ) : (
          <button onClick={() => onPage(page + 1)}>Next page →</button>
        )}
        <button className="stop" onClick={onStop}>
          ■ Finish
        </button>
      </div>
    </div>
  );
}
