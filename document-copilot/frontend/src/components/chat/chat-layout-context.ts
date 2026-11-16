import { useOutletContext } from 'react-router-dom'

export type ChatLayoutContext = {
  // Re-read the sidebar list (a thread's title appears after its first reply).
  reloadThreads: () => void
  startNewChat: () => void
}

export function useChatLayout() {
  return useOutletContext<ChatLayoutContext>()
}
