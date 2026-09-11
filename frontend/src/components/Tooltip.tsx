import { useCallback, useLayoutEffect, useRef, useState, type ReactNode } from 'react'
import { createPortal } from 'react-dom'

interface Props {
  title?: string
  text?: string | null
  footer?: string
  children: ReactNode
  className?: string
}

/** Tooltip flotante (se pinta en <body>, así no lo recorta el scroll del panel lateral). */
export default function Tooltip({ title, text, footer, children, className }: Props) {
  const anchor = useRef<HTMLSpanElement>(null)
  const bubble = useRef<HTMLDivElement>(null)
  const [open, setOpen] = useState(false)
  const [pos, setPos] = useState<{ top: number; left: number } | null>(null)

  const show = useCallback(() => setOpen(true), [])
  const hide = useCallback(() => {
    setOpen(false)
    setPos(null)
  }, [])

  useLayoutEffect(() => {
    if (!open || !anchor.current || !bubble.current) return
    const a = anchor.current.getBoundingClientRect()
    const b = bubble.current.getBoundingClientRect()
    const margin = 8
    let top = a.bottom + margin
    if (top + b.height > window.innerHeight - margin) top = a.top - b.height - margin // arriba si no cabe
    const left = Math.min(Math.max(margin, a.left + a.width / 2 - b.width / 2), window.innerWidth - b.width - margin)
    setPos({ top: Math.max(margin, top), left })
  }, [open])

  if (!text) return <>{children}</>
  return (
    <span
      ref={anchor}
      className={`tip-anchor ${className ?? ''}`}
      onMouseEnter={show}
      onMouseLeave={hide}
      onFocus={show}
      onBlur={hide}
    >
      {children}
      {open &&
        createPortal(
          <div
            ref={bubble}
            role="tooltip"
            className="tooltip"
            style={pos ? { top: pos.top, left: pos.left } : { top: -9999, left: -9999 }}
          >
            {title && <strong>{title}</strong>}
            <p>{text}</p>
            {footer && <small>{footer}</small>}
          </div>,
          document.body,
        )}
    </span>
  )
}
