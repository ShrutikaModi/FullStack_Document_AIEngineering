import { useChat } from '@ai-sdk/react'
import type { UIMessage } from 'ai'
import { useEffect, useRef, useState } from 'react'

import { ChatInput } from '@/components/chat/ChatInput'
import { MessageBubble } from '@/components/chat/MessageBubble'
import { SourcePanel } from '@/components/chat/SourcePanel'
import { friendlyError } from '@/lib/chat-error'
import { createChatTransport } from '@/lib/chat-transport'
import type { Source } from '@/lib/citations'

export function ChatView({
  threadId,
  initialMessages,
  onTurnFinished,
}: {
  threadId: string
  initialMessages: UIMessage[]
  onTurnFinished: () => void
}) {
  const [transport] = useState(createChatTransport)
  // What the assistant is doing right now ("Searching AAPL FY2024 filings: ..."). The backend
  // sends these as transient parts, which the chat library delivers only through onData.
  const [progress, setProgress] = useState<string | null>(null)
  const { messages, sendMessage, status, error } = useChat({
    id: threadId,
    messages: initialMessages,
    transport,
    onFinish: onTurnFinished,
    onData: (part) => {
      if (part.type !== 'data-status') return
      const { text } = (part.data ?? {}) as { text?: unknown }
      if (typeof text === 'string') setProgress(text)
    },
  })
  // The source the analyst clicked; the panel beside the chat shows its passage.
  const [openSource, setOpenSource] = useState<Source | null>(null)
  const bottom = useRef<HTMLDivElement>(null)
  const busy = status === 'submitted' || status === 'streaming'
  // Until the verified answer starts arriving there is no text to show, only progress.
  const last = messages[messages.length - 1]
  const answerStarted =
    last?.role === 'assistant' && last.parts.some((part) => part.type === 'text' && part.text)

  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, status])

  return (
    <div className="flex h-full flex-col">
      <div className="flex-1 overflow-y-auto p-4">
        <div className="mx-auto flex max-w-2xl flex-col gap-3">
          {messages.length === 0 && (
            <p className="mt-16 text-center text-muted-foreground">
              Ask a question about the filings to get started.
            </p>
          )}
          {messages.map((message) => (
            <MessageBubble key={message.id} message={message} onOpenSource={setOpenSource} />
          ))}
          {busy && !answerStarted && (
            <p className="text-sm text-muted-foreground">{progress ?? 'Thinking…'}</p>
          )}
          {error && (
            <p role="alert" className="text-sm text-destructive">
              {friendlyError(error)}
            </p>
          )}
          <div ref={bottom} />
        </div>
      </div>
      <div className="border-t p-4">
        <div className="mx-auto max-w-2xl">
          <ChatInput
            disabled={busy}
            onSend={(text) => {
              setProgress(null) // don't show the previous question's last step
              void sendMessage({ text })
            }}
          />
        </div>
      </div>
      <SourcePanel source={openSource} onClose={() => setOpenSource(null)} />
    </div>
  )
}
