import type { UIMessage } from 'ai'

// One source behind an answer. The backend builds it from its own stored copy of the
// filing passage (never from the model), so every field here is trustworthy.
export type Source = {
  label: number // the [n] used in the answer text
  chunkId: string
  company: string
  ticker: string
  formType: string
  fiscalYear: number
  filingDate: string // YYYY-MM-DD
  page: number | null
  section: string | null
  excerpt: string
  sourceUrl: string
}

// The answer text cut into plain text and clickable citations, in reading order.
export type Piece = { kind: 'text'; text: string } | { kind: 'citation'; source: Source }

// Saved messages come back from the API as JSON, so check the shape instead of trusting it.
function isSource(value: unknown): value is Source {
  if (typeof value !== 'object' || value === null) return false
  const v = value as Record<string, unknown>
  return (
    typeof v.label === 'number' &&
    typeof v.chunkId === 'string' &&
    typeof v.company === 'string' &&
    typeof v.formType === 'string' &&
    typeof v.fiscalYear === 'number' &&
    typeof v.filingDate === 'string' &&
    typeof v.excerpt === 'string' &&
    typeof v.sourceUrl === 'string'
  )
}

// The sources of an assistant message: the `data-citations` part the backend sends after
// the answer text (and stores, so a reloaded conversation still has them).
export function sourcesOf(message: UIMessage): Source[] {
  for (const part of message.parts) {
    if (part.type !== 'data-citations') continue
    const { sources } = (part as { data?: { sources?: unknown } }).data ?? {}
    if (Array.isArray(sources)) return sources.filter(isSource)
  }
  return []
}

// Turns "up 20% [1][2]." into text and citation pieces. A [n] becomes a citation only if a
// source with that label exists; otherwise it stays plain text, so the screen never shows a
// button with nothing behind it (this also covers a marker that arrives before the sources).
export function splitAnswer(text: string, sources: Source[]): Piece[] {
  const byLabel = new Map(sources.map((source) => [source.label, source]))
  const pieces: Piece[] = []
  let plain = ''
  let last = 0
  for (const match of text.matchAll(/\[(\d+)\]/g)) {
    const source = byLabel.get(Number(match[1]))
    if (!source) continue
    plain += text.slice(last, match.index)
    if (plain) pieces.push({ kind: 'text', text: plain })
    plain = ''
    pieces.push({ kind: 'citation', source })
    last = match.index + match[0].length
  }
  plain += text.slice(last)
  if (plain) pieces.push({ kind: 'text', text: plain })
  return pieces
}

// "Apple Inc. · 10-K FY2024 · page 23" for chips and the source list.
export function describeSource(source: Source): string {
  const page = source.page === null ? 'page unknown' : `page ${source.page}`
  return `${source.company} · ${source.formType} FY${source.fiscalYear} · ${page}`
}

// Noon avoids the date shifting a day when a date-only string is read as UTC.
export function formatFilingDate(isoDate: string): string {
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(
    new Date(`${isoDate}T12:00:00`),
  )
}
