import { useOutletContext } from 'react-router-dom'

import type { DemoInfo } from '@/lib/demo'

export type ChatLayoutContext = {
  // Re-read the sidebar list (a thread's title appears after its first reply).
  reloadThreads: () => void
  // Open a new conversation; with a question, that question is sent as soon as it opens.
  startNewChat: (question?: string) => void
  // Whether this account only has the sample questions; null until the backend has answered.
  demo: DemoInfo | null
}

export function useChatLayout() {
  return useOutletContext<ChatLayoutContext>()
}
