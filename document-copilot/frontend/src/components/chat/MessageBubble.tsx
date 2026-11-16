import type { UIMessage } from 'ai'

import { cn } from '@/lib/utils'

// Only text parts are shown for now; sources and citations come with the real assistant.
export function MessageBubble({ message }: { message: UIMessage }) {
  const text = message.parts.map((part) => (part.type === 'text' ? part.text : '')).join('')
  const isUser = message.role === 'user'

  return (
    <div className={cn('flex', isUser ? 'justify-end' : 'justify-start')}>
      <p
        className={cn(
          'max-w-[80%] rounded-xl px-3 py-2 text-sm whitespace-pre-wrap',
          isUser ? 'bg-primary text-primary-foreground' : 'bg-muted',
        )}
      >
        {text}
      </p>
    </div>
  )
}
