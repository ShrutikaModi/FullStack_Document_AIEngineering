import type { UIMessage } from 'ai'
import { useEffect, useState } from 'react'
import { useLocation } from 'react-router-dom'

import { ChatView } from '@/components/chat/ChatView'
import { useChatLayout } from '@/components/chat/chat-layout-context'
import { ApiError } from '@/lib/api'
import { supabase } from '@/lib/supabase'
import { getThreadMessages } from '@/lib/threads'

type State =
  | { kind: 'loading' }
  | { kind: 'ready'; messages: UIMessage[] }
  | { kind: 'error'; text: string }

// Loads the saved history first, then starts the chat with it.
export function ChatThread({ threadId }: { threadId: string }) {
  const { reloadThreads } = useChatLayout()
  const [state, setState] = useState<State>({ kind: 'loading' })
  // A sample question picked on the start screen arrives as navigation state.
  const picked = (useLocation().state as { question?: unknown } | null)?.question
  const [initialQuestion] = useState(typeof picked === 'string' ? picked : undefined)

  useEffect(() => {
    let cancelled = false
    getThreadMessages(threadId)
      .then((messages) => !cancelled && setState({ kind: 'ready', messages }))
      .catch((error) => {
        if (cancelled) return
        if (error instanceof ApiError && error.status === 401) {
          void supabase.auth.signOut()
        } else if (error instanceof ApiError && (error.status === 403 || error.status === 404)) {
          setState({ kind: 'error', text: 'This conversation was not found.' })
        } else {
          setState({
            kind: 'error',
            text: error instanceof ApiError ? error.message : 'Could not load this conversation.',
          })
        }
      })
    return () => {
      cancelled = true
    }
  }, [threadId])

  if (state.kind === 'loading') {
    return <p className="p-6 text-muted-foreground">Loading…</p>
  }
  if (state.kind === 'error') {
    return (
      <p role="alert" className="p-6 text-destructive">
        {state.text}
      </p>
    )
  }
  return (
    <ChatView
      threadId={threadId}
      initialMessages={state.messages}
      initialQuestion={initialQuestion}
      onTurnFinished={reloadThreads}
    />
  )
}
