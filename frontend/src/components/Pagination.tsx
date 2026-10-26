import { useEffect, useState } from 'react'
import { pageItems } from '../lib/pagination'

const NARROW = '(max-width: 600px)'

function useNarrow(): boolean {
  const [narrow, setNarrow] = useState(() => window.matchMedia(NARROW).matches)
  useEffect(() => {
    const media = window.matchMedia(NARROW)
    const onChange = () => setNarrow(media.matches)
    media.addEventListener('change', onChange)
    return () => media.removeEventListener('change', onChange)
  }, [])
  return narrow
}

/** Paginación con números: ← 1 … 4 [5] 6 … 20 → (menos números en el móvil). */
export default function Pagination({ page, pages, onPage }: { page: number; pages: number; onPage: (page: number) => void }) {
  const narrow = useNarrow()
  const items = pageItems(page, pages, narrow ? 1 : 2)
  return (
    <nav className="pagination" aria-label={`Página ${page} de ${pages}`}>
      <button className="btn ghost page-step" disabled={page <= 1} onClick={() => onPage(page - 1)} aria-label="Página anterior">
        {narrow ? '‹' : '← Anterior'}
      </button>
      <ol className="page-list">
        {items.map((item, i) =>
          item === 'gap' ? (
            <li key={`gap-${i}`} className="page-gap" aria-hidden>
              …
            </li>
          ) : (
            <li key={item}>
              <button
                className={`page-num ${item === page ? 'current' : ''}`}
                aria-current={item === page ? 'page' : undefined}
                aria-label={`Página ${item}`}
                onClick={() => item !== page && onPage(item)}
              >
                {item}
              </button>
            </li>
          ),
        )}
      </ol>
      <button className="btn ghost page-step" disabled={page >= pages} onClick={() => onPage(page + 1)} aria-label="Página siguiente">
        {narrow ? '›' : 'Siguiente →'}
      </button>
    </nav>
  )
}
