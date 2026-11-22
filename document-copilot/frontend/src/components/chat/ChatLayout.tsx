import { useCallback, useEffect, useState } from 'react'
import { Outlet, useMatch, useNavigate } from 'react-router-dom'

import type { ChatLayoutContext } from '@/components/chat/chat-layout-context'
import { ThreadList } from '@/components/chat/ThreadList'
import { ApiError } from '@/lib/api'
import { type DemoInfo, getDemoInfo } from '@/lib/demo'
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

  // Accounts without full access only get the sample questions. If this call fails the screen
  // behaves normally and the backend still enforces the limit.
  const [demo, setDemo] = useState<DemoInfo | null>(null)
  useEffect(() => {
    getDemoInfo()
      .then(setDemo)
      .catch(() => setDemo(null))
  }, [])

  async function startNewChat(question?: string) {
    try {
      const thread = await createThread()
      reloadThreads()
      // The question travels as navigation state; the chat sends it once it has opened.
      navigate(`/chat/${thread.id}`, { state: question ? { question } : null })
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Could not start a new chat.')
    }
  }

  const context: ChatLayoutContext = { reloadThreads, startNewChat, demo }

  return (
    <div className="flex h-screen">
      <ThreadList
        threads={threads}
        activeId={activeId}
        error={error}
        onNewChat={() => void startNewChat()}
      />
      <main className="min-w-0 flex-1">
        <Outlet context={context} />
      </main>
    </div>
  )
}
