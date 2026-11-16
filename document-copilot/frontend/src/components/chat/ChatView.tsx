import { useChat } from '@ai-sdk/react'
import type { UIMessage } from 'ai'
import { useEffect, useRef, useState } from 'react'

import { ChatInput } from '@/components/chat/ChatInput'
import { MessageBubble } from '@/components/chat/MessageBubble'
import { createChatTransport } from '@/lib/chat-transport'

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
  const { messages, sendMessage, status, error } = useChat({
    id: threadId,
    messages: initialMessages,
    transport,
    onFinish: onTurnFinished,
  })
  const bottom = useRef<HTMLDivElement>(null)
  const busy = status === 'submitted' || status === 'streaming'

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
            <MessageBubble key={message.id} message={message} />
          ))}
          {status === 'submitted' && <p className="text-sm text-muted-foreground">Thinking…</p>}
          {error && (
            <p role="alert" className="text-sm text-destructive">
              Something went wrong sending your message. Please try again.
            </p>
          )}
          <div ref={bottom} />
        </div>
      </div>
      <div className="border-t p-4">
        <div className="mx-auto max-w-2xl">
          <ChatInput disabled={busy} onSend={(text) => sendMessage({ text })} />
        </div>
      </div>
    </div>
  )
}
