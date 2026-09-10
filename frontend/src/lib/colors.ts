const COLORS = ['red', 'blue', 'green', 'yellow', 'black', 'white']

export function colorClass(value: unknown): string {
  const v = String(value).toLowerCase()
  return COLORS.includes(v) ? `c-${v}` : ''
}
