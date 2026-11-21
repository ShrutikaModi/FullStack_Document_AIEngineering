import type { UIMessage } from 'ai'
import { Fragment } from 'react'

import { CitationChip } from '@/components/chat/CitationChip'
import { SourceList } from '@/components/chat/SourceList'
import { type Source, sourcesOf, splitAnswer } from '@/lib/citations'
import { cn } from '@/lib/utils'

export function MessageBubble({
  message,
  onOpenSource,
}: {
  message: UIMessage
  onOpenSource: (source: Source) => void
}) {
  const text = message.parts.map((part) => (part.type === 'text' ? part.text : '')).join('')
  const isUser = message.role === 'user'
  const sources = isUser ? [] : sourcesOf(message)
  // The reply exists before its text does (the agent is still searching). Showing nothing
  // here avoids an empty bubble; the progress line in the chat view covers that time.
  if (!isUser && text === '') return null

  return (
    <div className={cn('flex', isUser ? 'justify-end' : 'justify-start')}>
      <div
        className={cn(
          'max-w-[80%] rounded-xl px-3 py-2 text-sm whitespace-pre-wrap',
          isUser ? 'bg-primary text-primary-foreground' : 'bg-muted',
        )}
      >
        {/* Each [n] that has a source becomes a clickable chip; everything else stays text. */}
        {splitAnswer(text, sources).map((piece, index) => (
          <Fragment key={index}>
            {piece.kind === 'text' ? (
              piece.text
            ) : (
              <CitationChip source={piece.source} onOpen={onOpenSource} />
            )}
          </Fragment>
        ))}
        <SourceList sources={sources} onOpen={onOpenSource} />
      </div>
    </div>
  )
}
