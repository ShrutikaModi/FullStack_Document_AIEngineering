import { useChat } from '@ai-sdk/react'
import type { UIMessage } from 'ai'
import { useEffect, useRef, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'

import { ChatInput } from '@/components/chat/ChatInput'
import { useChatLayout } from '@/components/chat/chat-layout-context'
import { ContactDialog } from '@/components/chat/ContactDialog'
import { MessageBubble } from '@/components/chat/MessageBubble'
import { SampleQuestions } from '@/components/chat/SampleQuestions'
import { SourcePanel } from '@/components/chat/SourcePanel'
import { friendlyError } from '@/lib/chat-error'
import { createChatTransport } from '@/lib/chat-transport'
import type { Source } from '@/lib/citations'
import { isSampleQuestion } from '@/lib/demo'

export function ChatView({
  threadId,
  initialMessages,
  initialQuestion,
  onTurnFinished,
}: {
  threadId: string
  initialMessages: UIMessage[]
  initialQuestion?: string
  onTurnFinished: () => void
}) {
  const { demo } = useChatLayout()
  const navigate = useNavigate()
  const location = useLocation()
  const [transport] = useState(createChatTransport)
  // The message for accounts that only have the samples; it opens when they type their own question.
  const [noticeOpen, setNoticeOpen] = useState(false)
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

  function send(text: string) {
    // Accounts with only the sample questions get the message instead of a model call. The
    // backend refuses these too; this just avoids the round trip and shows the message at once.
    if (demo?.demo && !isSampleQuestion(text, demo.questions)) {
      setNoticeOpen(true)
      return
    }
    setProgress(null) // don't show the previous question's last step
    void sendMessage({ text })
  }

  // A sample picked on the start screen is sent once, then removed from the navigation state
  // so reloading the page does not send it again.
  const pickedSent = useRef(false)
  useEffect(() => {
    if (!initialQuestion || pickedSent.current) return
    pickedSent.current = true
    setProgress(null)
    void sendMessage({ text: initialQuestion })
    navigate(location.pathname, { replace: true, state: null })
  }, [initialQuestion, sendMessage, navigate, location.pathname])

  return (
    <div className="flex h-full flex-col">
      <div className="flex-1 overflow-y-auto p-4">
        <div className="mx-auto flex max-w-2xl flex-col gap-3">
          {messages.length === 0 && !initialQuestion && (
            <div className="mt-16 flex flex-col items-center gap-6">
              <p className="text-center text-muted-foreground">
                Ask a question about the filings to get started.
              </p>
              {demo?.demo && <SampleQuestions questions={demo.questions} onPick={send} />}
            </div>
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
          <ChatInput disabled={busy} onSend={send} />
        </div>
      </div>
      <SourcePanel source={openSource} onClose={() => setOpenSource(null)} />
      {demo?.notice && (
        <ContactDialog notice={demo.notice} open={noticeOpen} onOpenChange={setNoticeOpen} />
      )}
    </div>
  )
}
