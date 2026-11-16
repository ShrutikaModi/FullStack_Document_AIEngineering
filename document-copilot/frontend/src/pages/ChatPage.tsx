import { useParams } from 'react-router-dom'

import { ChatThread } from '@/components/chat/ChatThread'
import { useChatLayout } from '@/components/chat/chat-layout-context'
import { Button } from '@/components/ui/button'

// /chat shows a start screen; /chat/:threadId shows one conversation.
export default function ChatPage() {
  const { threadId } = useParams()
  const { startNewChat } = useChatLayout()

  if (threadId) return <ChatThread key={threadId} threadId={threadId} />

  return (
    <div className="flex h-full flex-col items-center justify-center gap-3">
      <h1 className="text-2xl font-semibold">Document Copilot</h1>
      <p className="text-muted-foreground">Start a new conversation, or pick one from the list.</p>
      <Button onClick={startNewChat}>New chat</Button>
    </div>
  )
}
