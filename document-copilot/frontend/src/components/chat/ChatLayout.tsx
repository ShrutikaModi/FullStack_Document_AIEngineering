import { useCallback, useEffect, useState } from 'react'
import { Outlet, useMatch, useNavigate } from 'react-router-dom'

import type { ChatLayoutContext } from '@/components/chat/chat-layout-context'
import { ThreadList } from '@/components/chat/ThreadList'
import { ApiError } from '@/lib/api'
import { createThread, listThreads, type Thread } from '@/lib/threads'

// Sidebar plus the open conversation. Owns the thread list so the sidebar can
// refresh after a reply (the title is set when the first reply finishes).
export function ChatLayout() {
  const navigate = useNavigate()
  const activeId = useMatch('/chat/:threadId')?.params.threadId
  const [threads, setThreads] = useState<Thread[]>([])
  const [error, setError] = useState<string | null>(null)

  const reloadThreads = useCallback(() => {
    listThreads()
      .then((list) => {
        setThreads(list)
        setError(null)
      })
      .catch((e) => setError(e instanceof ApiError ? e.message : 'Could not load conversations.'))
  }, [])

  useEffect(reloadThreads, [reloadThreads])

  async function startNewChat() {
    try {
      const thread = await createThread()
      reloadThreads()
      navigate(`/chat/${thread.id}`)
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Could not start a new chat.')
    }
  }

  const context: ChatLayoutContext = { reloadThreads, startNewChat }

  return (
    <div className="flex h-screen">
      <ThreadList threads={threads} activeId={activeId} error={error} onNewChat={startNewChat} />
      <main className="min-w-0 flex-1">
        <Outlet context={context} />
      </main>
    </div>
  )
}
