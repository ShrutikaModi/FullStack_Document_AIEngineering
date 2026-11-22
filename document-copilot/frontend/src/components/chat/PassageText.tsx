import { Table, TableBody, TableCell, TableHead, TableRow } from '@/components/ui/table'
import { parsePassage, type Row } from '@/lib/passage'
import { cn } from '@/lib/utils'

// A filing passage as the reader should see it: paragraphs as text, tables as real tables
// (see lib/passage.ts for how the stored pipe-separated rows are tidied).
export function PassageText({ text }: { text: string }) {
  return (
    <div className="flex flex-col gap-3 text-sm">
      {parsePassage(text).map((block, i) =>
        block.kind === 'text' ? (
          <p key={i} className="whitespace-pre-wrap">
            {block.text}
          </p>
        ) : (
          <div key={i} className="overflow-hidden rounded-md border bg-background">
            <Table>
              <TableBody>
                {block.rows.map((row, r) => (
                  <PassageRow key={r} row={row} columns={block.columns} />
                ))}
              </TableBody>
            </Table>
          </div>
        ),
      )}
    </div>
  )
}

function PassageRow({ row, columns }: { row: Row; columns: number }) {
  if (row.kind === 'label') {
    // A title or section name spans the whole table.
    return (
      <TableRow className="bg-muted/60">
        <TableCell colSpan={columns} className="font-medium whitespace-normal">
          {row.text}
        </TableCell>
      </TableRow>
    )
  }
  const Cell = row.kind === 'head' ? TableHead : TableCell
  return (
    <TableRow className={cn(row.kind === 'head' && 'bg-muted/60 hover:bg-muted/60')}>
      {row.cells.map((cell, c) => (
        <Cell
          key={c}
          className={cn(
            // The first column holds the row's name; every other column holds figures.
            c === 0 ? 'whitespace-normal' : 'text-right tabular-nums',
            row.kind === 'head' && 'font-medium',
          )}
        >
          {cell}
        </Cell>
      ))}
    </TableRow>
  )
}
