// La vista de un mazo tal como quedaría (sin crear nada), en una ventana casi a pantalla completa: «Preview deck» al
// importar y el detalle de un mazo futuro. Las cartas se pueden abrir para ver su ficha.
import { useEffect, useRef, useState, type ReactNode } from 'react'
import CardModal from './CardModal'
import { DeckPreview } from './DeckView'
import { api } from '../lib/api'
import { SkillIndex } from '../lib/skills'
import type { CardSummary } from '../lib/types'

/** Ventana a pantalla casi completa con la vista del mazo tal como quedaría (sin crear nada). Las cartas se pueden
 *  abrir para ver su ficha. */
export default function DeckPreviewDialog({
  name,
  pool,
  side,
  note,
  onClose,
  title = '👁 Deck preview',
  back = <>← Back<span className="long"> to the import</span></>,
  actions,
  eyebrow,
}: {
  name: string
  pool: CardSummary[]
  side: CardSummary[]
  note?: string
  onClose: () => void
  title?: ReactNode
  back?: ReactNode
  /** Botones o datos extra en la cabecera (p. ej. «Build this deck» en un mazo futuro). */
  actions?: ReactNode
  eyebrow?: string
}) {
  const ref = useRef<HTMLDialogElement>(null)
  const [openId, setOpenId] = useState<number | null>(null)
  // La ficha de la carta se cierra con su propio Escape (y React la quita al momento): este aviso evita que ese mismo
  // Escape cierre también la vista previa.
  const cardJustClosed = useRef(false)
  const closeCard = () => {
    setOpenId(null)
    cardJustClosed.current = true
    window.setTimeout(() => (cardJustClosed.current = false), 0)
  }
  const [skills, setSkills] = useState<SkillIndex>(SkillIndex.empty)
  useEffect(() => {
    ref.current?.showModal()
    api.keywordSkills().then((d) => setSkills(new SkillIndex(d))).catch(() => {})
  }, [])
  return (
    <dialog
      ref={ref}
      className="deck-preview-dialog"
      // React pasa «close» y «cancel» a los componentes de fuera: sin esto, cerrar la vista previa cerraría la importación.
      onClose={(e) => {
        e.stopPropagation()
        onClose()
      }}
      onCancel={(e) => {
        e.stopPropagation()
        // Con la ficha de una carta abierta, Escape cierra solo la ficha.
        if (openId != null || cardJustClosed.current) {
          e.preventDefault()
          if (openId != null) closeCard()
        }
      }}
    >
      <header className="deck-preview-head">
        <span>{title}</span>
        <span className="deck-preview-actions">
          {actions}
          <button type="button" className="btn" onClick={() => ref.current?.close()}>
            {back}
          </button>
        </span>
      </header>
      <DeckPreview name={name} pool={pool} side={side} onOpen={setOpenId} note={note} eyebrow={eyebrow} />
      {openId != null && (
        <CardModal key={openId} id={openId} skills={skills} onClose={closeCard} onFilter={() => {}} onOpenPrint={setOpenId} />
      )}
    </dialog>
  )
}

