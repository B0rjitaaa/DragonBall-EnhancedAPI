import { Fragment } from 'react'

const TOKEN = /(\[[^\]]+\])/g

/** Texto de Bandai (con <br>) con las habilidades [Entre Corchetes] resaltadas y clicables. */
export default function CardText({ text, onKeyword }: { text: string; onKeyword?: (raw: string) => void }) {
  if (!text) return null
  const lines = text.replace(/<br\s*\/?>/gi, '\n').replace(/<[^>]+>/g, '').split('\n')
  return (
    <div className="card-text">
      {lines.map((line, i) => (
        <p key={i}>
          {line.split(TOKEN).map((part, j) =>
            part.startsWith('[') && part.endsWith(']') ? (
              <button key={j} className="kw" onClick={() => onKeyword?.(part.slice(1, -1))} title="Buscar esta habilidad">
                {part}
              </button>
            ) : (
              <Fragment key={j}>{part}</Fragment>
            ),
          )}
        </p>
      ))}
    </div>
  )
}
