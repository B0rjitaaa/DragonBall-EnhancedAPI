import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { api } from "../api";
import type { Scan } from "../types";
import CardDetail from "./CardDetail";
import CardPicker from "./CardPicker";

function percent(value: number | null) {
  return value == null ? "—" : `${Math.round(value * 100)}%`;
}

export default function ScanResult({ scan }: { scan: Scan }) {
  const queryClient = useQueryClient();
  const [correcting, setCorrecting] = useState(false);
  const confirm = useMutation({
    mutationFn: (cardId: number) => api.confirmScan(scan.id, cardId),
    onSuccess: (updated) => {
      queryClient.setQueryData(["scan", scan.id], updated);
      queryClient.invalidateQueries({ queryKey: ["scans"] });
      queryClient.invalidateQueries({ queryKey: ["session"] });
      queryClient.invalidateQueries({ queryKey: ["collection"] });
      setCorrecting(false);
    },
  });

  if (scan.status === "pending" || scan.status === "processing") {
    return <p className="muted">Identifying… ({scan.status})</p>;
  }
  if (scan.status === "failed") {
    return <p className="error">Error: {scan.error}</p>;
  }

  // En modo ráfaga, lo que no se añadió solo se confirma eligiendo la carta.
  const pendingInSession = scan.session != null && !scan.added_to_collection && !scan.dismissed;
  const unsure = (scan.needs_review || pendingInSession) && !scan.confirmed;
  const picking = unsure || correcting;
  const current = confirm.data ?? scan;

  return (
    <section className="scan-result">
      <div className="scan-meta">
        {current.confirmed ? (
          <span className="scan-badge ok">Confirmed ✓</span>
        ) : (
          <span className={unsure ? "scan-badge warn" : "scan-badge ok"}>
            {unsure ? "Not sure" : "Identified"} · {percent(scan.confidence)}
          </span>
        )}
        <span className="muted">
          {scan.method} · {scan.duration_ms} ms
          {!scan.card_detected && " · card edges not detected"}
        </span>
      </div>

      <div className="scan-body">
        {scan.cropped_image && (
          <figure className="crop">
            <img src={scan.cropped_image} alt="Crop" />
            <figcaption>Your photo</figcaption>
          </figure>
        )}
        <div className="scan-main">
          {picking ? (
            <>
              <h3>{unsure ? "Which one is it?" : "Pick the right card"}</h3>
              <CardPicker candidates={scan.candidates} onPick={(id) => confirm.mutate(id)} busy={confirm.isPending} />
              {correcting && (
                <button className="link" onClick={() => setCorrecting(false)}>
                  Cancel
                </button>
              )}
            </>
          ) : current.matched_card ? (
            <>
              {/* En una sesión la colección la gestiona el modo ráfaga: sin botón de añadir. */}
              <CardDetail card={current.matched_card} showAddButton={current.session == null} />
              {!current.confirmed && (
                <button className="link" onClick={() => setCorrecting(true)}>
                  Not this card? Fix it
                </button>
              )}
            </>
          ) : (
            <p className="muted">No matches: have the fingerprints been computed?</p>
          )}
          {confirm.isError && <p className="error">{confirm.error.message}</p>}
        </div>
      </div>
    </section>
  );
}
