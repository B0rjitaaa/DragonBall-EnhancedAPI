import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { api } from "../api";
import ScanResult from "../components/ScanResult";
import type { Scan, ScanStatus } from "../types";

const SOURCE_LABEL: Record<Scan["source"], string> = { camera: "Camera", upload: "Uploaded photo" };
const STATUS_LABEL: Record<ScanStatus, string> = {
  pending: "Queued…",
  processing: "Identifying…",
  done: "Done",
  failed: "Error",
};

export default function History() {
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<Scan | null>(null);
  const scans = useQuery({
    queryKey: ["scans", page],
    queryFn: () => api.listScans(page),
    placeholderData: keepPreviousData,
  });

  if (scans.isError) return <p className="error">{scans.error.message}</p>;
  if (!scans.data) return <p className="muted">Loading…</p>;

  return (
    <div>
      <table className="table">
        <thead>
          <tr>
            <th />
            <th>Date</th>
            <th>Source</th>
            <th>Result</th>
            <th>Confidence</th>
            <th>Time</th>
          </tr>
        </thead>
        <tbody>
          {scans.data.results.map((scan) => (
            <tr key={scan.id} className={scan.needs_review ? "warn-row" : ""} onClick={() => setSelected(scan)}>
              <td>{scan.cropped_image && <img className="thumb" src={scan.cropped_image} alt="" />}</td>
              <td>{new Date(scan.created_at).toLocaleString()}</td>
              <td>{SOURCE_LABEL[scan.source] ?? scan.source}</td>
              <td>
                {scan.status !== "done"
                  ? STATUS_LABEL[scan.status]
                  : scan.matched_card
                    ? `${scan.matched_card.card_number} · ${scan.matched_card.name}`
                    : "—"}
              </td>
              <td>{scan.confidence != null ? `${Math.round(scan.confidence * 100)}%` : "—"}</td>
              <td>{scan.duration_ms != null ? `${scan.duration_ms} ms` : "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="pager">
        <button disabled={!scans.data.previous} onClick={() => setPage((p) => p - 1)}>
          ← Previous
        </button>
        <span>Page {page}</span>
        <button disabled={!scans.data.next} onClick={() => setPage((p) => p + 1)}>
          Next →
        </button>
      </div>

      {selected && (
        <div className="scan-modal" onClick={() => setSelected(null)}>
          <div onClick={(e) => e.stopPropagation()}>
            <ScanResult key={selected.id} scan={selected} />
          </div>
        </div>
      )}
    </div>
  );
}
