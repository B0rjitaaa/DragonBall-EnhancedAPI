import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { api } from "../api";
import type { Candidate } from "../types";

interface Option {
  id: number;
  card_number: string;
  name: string;
  image_url: string;
  card_set?: string;
  hint?: string;
}

function fromCandidate(c: Candidate): Option {
  return {
    id: c.card_id,
    card_number: c.card_number,
    name: c.name,
    image_url: c.image_url,
    card_set: c.card_set,
    hint: `${Math.round(c.score * 100)}%`,
  };
}

function Tile({ o, busy, onPick, showSet }: { o: Option; busy: boolean; onPick: (id: number) => void; showSet?: boolean }) {
  return (
    <button className="scan-tile" disabled={busy} onClick={() => onPick(o.id)} title="This one">
      {o.image_url && <img src={o.image_url} alt={o.name} loading="lazy" />}
      <span>
        {o.card_number} · {o.name}
        {o.hint && <span className="muted"> · {o.hint}</span>}
      </span>
      {showSet && o.card_set && <span className="tile-set">{o.card_set}</span>}
    </button>
  );
}

/** Elige la carta correcta: entre los candidatos del escaneo o buscándola. Si duda entre
 *  impresiones hermanas (mismo número: promos, Judge…), enseña juntas todas sus ediciones. */
export default function CardPicker({
  candidates,
  onPick,
  busy,
}: {
  candidates: Candidate[];
  onPick: (cardId: number) => void;
  busy: boolean;
}) {
  const [search, setSearch] = useState("");
  const term = search.trim();
  const results = useQuery({
    queryKey: ["cards", "picker", term],
    queryFn: () => api.searchCards(term),
    enabled: term.length >= 2,
  });

  // Los dos mejores son la misma carta en distinta impresión: la duda es la edición.
  const siblingNumber =
    candidates.length > 1 && candidates[0].card_number === candidates[1].card_number ? candidates[0].card_number : null;
  const printings = useQuery({
    queryKey: ["cards", "printings", siblingNumber],
    queryFn: () => api.searchCards(siblingNumber!),
    enabled: siblingNumber != null && term.length < 2,
  });

  const searching = term.length >= 2;
  const scores = new Map(candidates.map((c) => [c.card_id, `${Math.round(c.score * 100)}%`]));
  const siblings: Option[] = siblingNumber
    ? (printings.data?.results ?? candidates.filter((c) => c.card_number === siblingNumber).map(fromCandidate))
        .filter((o) => o.card_number === siblingNumber)
        .map((o) => ({ ...o, hint: scores.get(o.id) }))
        // primero las que el escáner propuso (por puntuación), luego el resto de ediciones
        .sort((a, b) => (b.hint ? parseInt(b.hint) : -1) - (a.hint ? parseInt(a.hint) : -1))
    : [];
  const others: Option[] = searching
    ? (results.data?.results ?? [])
    : candidates.filter((c) => c.card_number !== siblingNumber).map(fromCandidate);

  return (
    <div className="picker">
      <input
        type="search"
        placeholder="Search by name or number (e.g. BT25-120)…"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
      />
      {searching && results.data && (
        <p className="muted">{results.data.count} results{results.data.count > 30 && " (showing 30)"}</p>
      )}
      {!searching && siblings.length > 0 && (
        <div className="picker-siblings">
          <p className="picker-note">
            It's <strong>{siblings[0].card_number} · {siblings[0].name}</strong>, but there are several printings: pick the
            edition of your card.
          </p>
          <div className="picker-grid">
            {siblings.map((o) => (
              <Tile key={o.id} o={o} busy={busy} onPick={onPick} showSet />
            ))}
          </div>
          {others.length > 0 && <p className="muted small">Other candidates</p>}
        </div>
      )}
      <div className="picker-grid">
        {others.map((o) => (
          <Tile key={o.id} o={o} busy={busy} onPick={onPick} showSet={searching} />
        ))}
      </div>
      <p className="muted small">
        If your printing isn't listed (promos, prizes…), pick the same card in another printing: your photo is saved and
        it will be recognised next time.
      </p>
    </div>
  );
}
