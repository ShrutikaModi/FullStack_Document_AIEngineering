import { Button } from '@/components/ui/button'
import { describeSource, type Source } from '@/lib/citations'

// "Sources" under an answer: one row per source. It stays useful even when the answer
// bunches several markers together, because every source is listed once, by itself.
export function SourceList({
  sources,
  onOpen,
}: {
  sources: Source[]
  onOpen: (source: Source) => void
}) {
  if (sources.length === 0) return null
  return (
    <div className="mt-2 border-t border-border pt-2">
      <p className="mb-1 text-xs font-medium text-muted-foreground">Sources</p>
      <ul className="flex flex-col">
        {sources.map((source) => (
          <li key={source.label}>
            <Button
              variant="ghost"
              size="xs"
              onClick={() => onOpen(source)}
              className="h-auto w-full justify-start gap-2 py-1 whitespace-normal"
            >
              <span className="font-medium text-primary">[{source.label}]</span>
              <span className="min-w-0 truncate text-left font-normal">
                {describeSource(source)}
                {source.section ? ` · ${source.section}` : ''}
              </span>
            </Button>
          </li>
        ))}
      </ul>
    </div>
  )
}
