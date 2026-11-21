import { Button } from '@/components/ui/button'
import { describeSource, type Source } from '@/lib/citations'

// The clickable [n] inside an answer. Clicking opens the source panel.
export function CitationChip({
  source,
  onOpen,
}: {
  source: Source
  onOpen: (source: Source) => void
}) {
  return (
    <Button
      variant="ghost"
      size="xs"
      onClick={() => onOpen(source)}
      title={describeSource(source)}
      aria-label={`Source ${source.label}: ${describeSource(source)}`}
      className="mx-0.5 h-5 min-w-5 bg-primary/10 px-1 align-baseline text-primary hover:bg-primary/20"
    >
      {source.label}
    </Button>
  )
}
