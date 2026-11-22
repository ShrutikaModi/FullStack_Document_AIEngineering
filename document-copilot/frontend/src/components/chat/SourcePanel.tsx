import { ExternalLink } from 'lucide-react'

import { PassageText } from '@/components/chat/PassageText'
import { Button } from '@/components/ui/button'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import { formatFilingDate, type Source } from '@/lib/citations'

// The proof behind a citation: the exact passage from the filing, shown beside the chat.
// Esc, the close button and clicking outside all close it (handled by the Sheet).
export function SourcePanel({ source, onClose }: { source: Source | null; onClose: () => void }) {
  return (
    <Sheet open={source !== null} onOpenChange={(open) => !open && onClose()}>
      <SheetContent side="right" className="sm:max-w-2xl">
        {source && (
          <>
            <SheetHeader>
              <SheetTitle>
                Source [{source.label}] · {source.company}
              </SheetTitle>
              <SheetDescription>
                {source.formType} for fiscal year {source.fiscalYear}, filed{' '}
                {formatFilingDate(source.filingDate)}
                <br />
                {source.page === null ? 'Page unknown' : `Page ${source.page}`}
                {source.section ? ` · ${source.section}` : ''}
              </SheetDescription>
            </SheetHeader>
            <div className="min-h-0 flex-1 overflow-y-auto px-4">
              <p className="mb-1 text-xs font-medium text-muted-foreground">
                Passage from the filing
              </p>
              {/* The stored text, with its tables shown as tables. Nothing is added or reworded. */}
              <div className="rounded-md border bg-muted p-3">
                <PassageText text={source.excerpt} />
              </div>
            </div>
            <div className="border-t p-4">
              <Button
                variant="outline"
                className="w-full"
                render={<a href={source.sourceUrl} target="_blank" rel="noopener noreferrer" />}
              >
                Open the filing on SEC.gov
                <ExternalLink data-icon="inline-end" />
              </Button>
            </div>
          </>
        )}
      </SheetContent>
    </Sheet>
  )
}
