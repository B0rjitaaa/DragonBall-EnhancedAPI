import { csrfToken, reportApiFailure } from "../lib/errorReporter";
import type { BinderSpot, CardOption, FrameRegion, Location, Page, Scan, ScanSession, SessionMode } from "./types";

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  // El token CSRF hace falta si hay sesión iniciada (p. ej. tras entrar en /admin).
  const response = await fetch(url, { ...init, headers: { "X-CSRFToken": csrfToken(), ...(init?.headers ?? {}) } });
  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try {
      const body = await response.json();
      detail = body.detail ?? JSON.stringify(body);
    } catch {
      /* respuesta sin JSON */
    }
    if (response.status >= 500 || response.status === 403) {
      reportApiFailure(init?.method ?? "GET", url.replace(/^\/api/, ""), response.status, detail);
    }
    throw new Error(detail);
  }
  return response.json() as Promise<T>;
}

function json(method: string, body: unknown): RequestInit {
  return { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) };
}

/**
 * Cada cuánto se refresca una sesión: rápido mientras alguna carta se está
 * identificando (el resultado aparece en cuanto está), y despacio si no.
 */
export function sessionPollInterval(session: ScanSession | undefined): number {
  const busy = session?.scans.some((s) => s.status === "pending" || s.status === "processing");
  return busy ? 250 : 2000;
}

export const api = {
  /** `binder`: página y casilla (1…filas×columnas) en una sesión de archivador. */
  /** `region`: zona del marco (fracciones 0-1) que el servidor recorta de la webcam. */
  createScan(image?: File, session?: number, afterEmpty = true, binder?: BinderSpot, region?: FrameRegion | null): Promise<Scan> {
    const spot = {
      ...(binder ? { binder_page: binder.page, binder_slot: binder.slot } : {}),
      ...(region && !image ? { region } : {}),
    };
    if (!image) {
      return request("/api/scanner/scans/", json("POST", session ? { session, after_empty: afterEmpty, ...spot } : {}));
    }
    const form = new FormData();
    form.append("image", image);
    if (session) {
      form.append("session", String(session));
      form.append("after_empty", afterEmpty ? "true" : "false");
      for (const [k, v] of Object.entries(spot)) form.append(k, String(v)); // region solo va sin imagen
    }
    return request("/api/scanner/scans/", { method: "POST", body: form });
  },
  undoScan: (id: number) => request<Scan>(`/api/scanner/scans/${id}/undo/`, json("POST", {})),

  /** `size`: bolsillos por página en modo archivador (si el destino es un archivador, cuenta el suyo). */
  createSession: (location?: number | null, mode: SessionMode = "burst", size?: { rows: number; cols: number }) =>
    request<ScanSession>(
      "/api/scanner/sessions/",
      json("POST", {
        mode,
        ...(location ? { location } : {}),
        ...(size ? { binder_rows: size.rows, binder_cols: size.cols } : {}),
      }),
    ),
  listLocations: () => request<Location[]>("/api/my-collection/locations/"),
  getSession: (id: number) => request<ScanSession>(`/api/scanner/sessions/${id}/`),
  endSession: (id: number) => request<ScanSession>(`/api/scanner/sessions/${id}/end/`, json("POST", {})),
  getScan: (id: number) => request<Scan>(`/api/scanner/scans/${id}/`),
  confirmScan: (id: number, cardId: number, copies?: number) =>
    request<Scan>(`/api/scanner/scans/${id}/confirm/`, json("POST", copies ? { card_id: cardId, copies } : { card_id: cardId })),
  setScanCopies: (id: number, copies: number) =>
    request<Scan>(`/api/scanner/scans/${id}/copies/`, json("POST", { copies })),
  listScans: (page = 1) => request<Page<Scan>>(`/api/scanner/scans/?page=${page}`),

  /** Buscar en todo el catálogo (para corregir la carta de un escaneo). */
  searchCards: (q: string) =>
    request<{ count: number; results: CardOption[] }>("/api/cards/search/", json("POST", { q, page_size: 30 })),
  /** Sumar una copia a Mi colección («Sin ubicar»). */
  addToCollection: (cardId: number) =>
    request<{ quantity: number }>("/api/my-collection/adjust/", json("POST", { card_id: cardId, delta: 1 })),

  previewUrl: () => `/api/scanner/camera/preview/?t=${Date.now()}`,
};
