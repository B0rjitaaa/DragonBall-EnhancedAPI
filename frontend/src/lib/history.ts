/** «hace 5 min», «today 14:03», «3 Nov 14:03»: cuándo fue un cambio del histórico. */
export const historyWhen = (iso: string) => {
  const d = new Date(iso)
  const s = (Date.now() - d.getTime()) / 1000
  if (s < 60) return 'just now'
  if (s < 3600) return `${Math.round(s / 60)} min ago`
  const time = d.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })
  if (s < 86400 && d.getDate() === new Date().getDate()) return `today ${time}`
  return `${d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: d.getFullYear() === new Date().getFullYear() ? undefined : 'numeric' })} ${time}`
}
