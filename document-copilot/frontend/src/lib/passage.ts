// A filing passage arrives as text in which tables are rows written like
//   | Net sales | $ | 167,045 | $ | 162,560 |
// with "$" and "%" in cells of their own, title rows ("| Year Ended December 31, |") and
// sometimes a header row with no label column. This turns the text into paragraphs and
// tidy tables so the screen can show a real table instead of lines of pipes.

export type Row =
  | { kind: 'label'; text: string } // a title or section row, e.g. "Americas:" or "($ in millions)"
  | { kind: 'head' | 'body'; cells: string[] }

export type Block = { kind: 'text'; text: string } | { kind: 'table'; rows: Row[]; columns: number }

const isTableLine = (line: string) => {
  const pipes = (line.match(/\|/g) ?? []).length
  return pipes >= 2 || (line.trim().startsWith('|') && pipes >= 1)
}

// A number as a filing prints it: "201,183", "$7.7", "(31,370)", "145%". Plain years are not
// counted, so a row of years reads as a header.
const NUMBER = /^\$?\(?\d[\d,]*(\.\d+)?\)?%?$/
const YEAR = /^(19|20)\d\d$/
export const isNumeric = (cell: string) => NUMBER.test(cell) && !YEAR.test(cell)

function cellsOf(line: string): string[] {
  const raw = line
    .trim()
    .replace(/^\|/, '')
    .replace(/\|$/, '')
    .split('|')
    .map((cell) => cell.trim().replace(/\s+/g, ' '))
  const cells: string[] = []
  raw.forEach((cell, i) => {
    if (cell === '$' && i + 1 < raw.length) {
      raw[i + 1] = `$${raw[i + 1]}` // "$ | 201,183" is one cell: "$201,183"
    } else if ((cell === '%' || cell === ')') && cells.length > 0) {
      cells[cells.length - 1] += cell // "145 | %" is one cell: "145%"
    } else {
      cells.push(cell)
    }
  })
  return cells
}

function tableOf(lines: string[]): Block {
  const parsed: Row[] = []
  for (const line of lines) {
    const cells = cellsOf(line)
    if (cells.every((cell) => /^:?-{2,}:?$/.test(cell) || cell === '')) continue // "|---|---|"
    const filled = cells.filter(Boolean)
    if (filled.length === 1) parsed.push({ kind: 'label', text: filled[0] })
    else parsed.push({ kind: cells.some(isNumeric) ? 'body' : 'head', cells })
  }

  const data = parsed.filter((row) => row.kind !== 'label')
  const width = Math.max(0, ...data.map((row) => row.cells.length))
  // A header row with one cell fewer than the data has no label column: leave that column blank
  // so the headings sit over their numbers. Other short rows are padded on the right.
  const padded = parsed.map((row) => {
    if (row.kind === 'label') return row
    const blank = Array<string>(width - row.cells.length).fill('')
    return { ...row, cells: row.kind === 'head' ? [...blank, ...row.cells] : [...row.cells, ...blank] }
  })
  // Drop columns that are empty in every row (the filings use blank spacer cells).
  const kept = Array.from({ length: width }, (_, i) => i).filter((i) =>
    padded.some((row) => row.kind !== 'label' && row.cells[i] !== ''),
  )
  const rows = padded.map((row) =>
    row.kind === 'label' ? row : { ...row, cells: kept.map((i) => row.cells[i]) },
  )
  return { kind: 'table', rows, columns: Math.max(1, kept.length) }
}

export function parsePassage(text: string): Block[] {
  const blocks: Block[] = []
  let prose: string[] = []
  let table: string[] = []
  const flush = () => {
    const joined = prose.join('\n').trim()
    if (joined) blocks.push({ kind: 'text', text: joined })
    if (table.length > 0) blocks.push(tableOf(table))
    prose = []
    table = []
  }
  for (const line of text.split('\n')) {
    if (isTableLine(line)) {
      if (prose.length > 0) flush()
      table.push(line)
    } else {
      if (table.length > 0) flush()
      prose.push(line)
    }
  }
  flush()
  return blocks
}
